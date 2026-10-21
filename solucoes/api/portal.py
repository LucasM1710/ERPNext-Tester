"""API do Portal do Cliente — usada pelo frontend em /portal.

Todas as rotas resolvem os clientes do usuário logado e delegam ao adapter
configurado; nenhuma consulta direta a DocTypes acontece aqui.
"""

import json

import frappe
from frappe import _

from solucoes.metrologia.periodicidade import sugerir_periodicidade
from solucoes.portal import auditoria, historico
from solucoes.portal.adapters import get_adapter, modo_portal
from solucoes.portal.sessao import (
	GESTOR,
	USUARIO,
	clientes_com_distritos,
	get_contato_do_usuario,
	get_escopo,
	is_usuario_interno,
	resolver_clientes,
	resolver_escopo_unico,
)


def _json(valor):
	if isinstance(valor, str):
		return json.loads(valor) if valor else {}
	return valor or {}


def _config():
	return frappe.get_cached_doc("Configuracao Portal Metrologia")


def _nao_encontrado(item):
	if item is None:
		raise frappe.DoesNotExistError(_("Registro não encontrado."))
	return item


# ===================================================================== contexto
@frappe.whitelist()
def contexto():
	resolver_clientes()
	cfg = _config()
	user = frappe.get_cached_doc("User", frappe.session.user)
	escopo = get_escopo()
	interno = is_usuario_interno()
	com_distritos = clientes_com_distritos(escopo[:200])
	consulta = modo_portal() == "consulta"
	com_historico = set(historico.liberadas(escopo[:200])) if consulta else set()
	if not interno:
		auditoria.registrar_acesso(list(escopo))
	return {
		"usuario": {"email": user.name, "nome": user.full_name, "imagem": user.user_image, "interno": interno},
		"clientes": [_contexto_cliente(escopo, c, c in com_distritos, consulta, c in com_historico) for c in escopo[:200]],
		"empresa": frappe.defaults.get_global_default("company"),
		# Logs: usuários internos e gestores dos clientes.
		"pode_ver_logs": interno or any(escopo.eh_gestor(c) for c in escopo[:200]),
		"config": {
			"titulo": cfg.titulo_portal or "Portal do Cliente",
			"dias_alerta": cfg.dias_alerta or 30,
			# /consulta: só leitura (as ações de escrita somem das telas e o adapter recusa).
			"modo": "consulta" if consulta else "completo",
			"permitir_cadastro_cliente": bool(cfg.permitir_cadastro_cliente),
			"permitir_certificado_externo": bool(cfg.permitir_certificado_externo),
		},
	}


def _contexto_cliente(escopo, cliente, usa_distritos, consulta=False, ver_historico=False):
	perfil = escopo.perfil(cliente)
	distritos = []
	# Usuário não navega por distrito: vê os equipamentos dos quais é dono.
	if usa_distritos and perfil != USUARIO:
		permitidos = escopo.distritos_de(cliente)
		filtros = {"cliente": cliente, "ativo": 1}
		if permitidos is not None:
			filtros["name"] = ["in", list(permitidos) or [""]]
		distritos = frappe.get_all(
			"Distrito Cliente", filters=filtros, fields=["name as id", "nome_distrito as nome"], order_by="nome_distrito"
		)
	return {
		"id": cliente,
		"nome": frappe.db.get_value("Customer", cliente, "customer_name"),
		"usa_distritos": usa_distritos,
		"perfil": perfil,
		"distritos": distritos,
		# Na /consulta a escrita fica restrita (pelo adapter) aos equipamentos de terceiros.
		"pode_editar": perfil != USUARIO,
		"pode_gerenciar": usa_distritos and perfil == GESTOR,
		# Histórico de atendimento (notas das oportunidades liberadas pela ER)
		"ver_historico": ver_historico,
	}


@frappe.whitelist()
def dashboard(cliente=None):
	return get_adapter().resumo_dashboard(resolver_clientes(cliente))


# ===================================================================== equipamentos
@frappe.whitelist()
def equipamentos(cliente=None, filtros=None):
	return get_adapter().listar_equipamentos(resolver_clientes(cliente), _json(filtros))


@frappe.whitelist()
def equipamento(id, cliente=None):
	clientes = resolver_clientes(cliente)
	adapter = get_adapter()
	eqp = _nao_encontrado(adapter.obter_equipamento(clientes, id))
	eqp["certificados"] = adapter.listar_certificados(clientes, {"equipamento": id})
	eqp["ordens"] = adapter.listar_ordens(clientes, {"equipamento": id})
	eqp["tendencia"] = _tendencia(adapter, clientes, eqp["certificados"])
	eqp["periodicidade_sugerida"] = sugerir_periodicidade(
		[{"data": t["data"], "uso": t["uso"]} for t in eqp["tendencia"] if t["uso"] is not None],
		eqp.get("periodicidade_meses"),
	)
	eqp["verificacoes"] = adapter.listar_verificacoes(clientes, id)
	return eqp


def _tendencia(adapter, clientes, certificados, limite=10):
	"""Pior ponto de cada calibração (mais antiga -> mais recente).

	Usa o valor ENCONTRADO (as found) quando o equipamento foi ajustado: é ele que mostra
	como o instrumento se comportou durante o intervalo — base da periodicidade inteligente.
	"""
	serie = []
	for resumo in reversed(certificados[:limite]):
		cert = adapter.obter_certificado(clientes, resumo["id"]) or {}
		pontos = cert.get("pontos") or []
		if not pontos:
			continue

		def erro_encontrado(p):
			if cert.get("ajustado") and p.get("valor_encontrado"):
				return (p["valor_encontrado"] or 0) - (p.get("valor_nominal") or 0)
			return p.get("erro") or 0

		pior = max(pontos, key=lambda p: abs(erro_encontrado(p)) + abs(p.get("incerteza") or 0))
		erro, incerteza, tolerancia = abs(erro_encontrado(pior)), abs(pior.get("incerteza") or 0), pior.get("tolerancia")
		serie.append(
			{
				"certificado_id": resumo["id"],
				"data": resumo["data_calibracao"],
				"erro_max": erro,
				"incerteza": incerteza,
				"tolerancia": tolerancia,
				"uso": round((erro + incerteza) / tolerancia, 4) if tolerancia else None,
				"resultado": resumo["resultado"],
			}
		)
	return serie


@frappe.whitelist()
def qrcode(id, cliente=None):
	"""SVG com QR Code apontando para a ficha do equipamento no portal (para etiqueta)."""
	from io import BytesIO

	from pyqrcode import create

	_nao_encontrado(get_adapter().obter_equipamento(resolver_clientes(cliente), id))
	buffer = BytesIO()
	pagina = "consulta" if modo_portal() == "consulta" else "cliente"
	create(frappe.utils.get_url(f"/{pagina}/equipamentos/{id}"), error="M").svg(buffer, scale=8, quiet_zone=2)
	frappe.local.response.update(
		{
			"filename": f"{id}.svg",
			"filecontent": buffer.getvalue(),
			"type": "download",
			"content_type": "image/svg+xml",
			"display_content_as": "inline",
		}
	)


@frappe.whitelist(methods=["POST"])
def criar_equipamento(dados, cliente=None):
	if not _config().permitir_cadastro_cliente and not is_usuario_interno():
		raise frappe.PermissionError(_("Cadastro de equipamentos pelo portal está desabilitado."))
	return get_adapter().criar_equipamento(resolver_escopo_unico(cliente), _json(dados))


@frappe.whitelist(methods=["POST"])
def atualizar_equipamento(id, dados, cliente=None):
	return get_adapter().atualizar_equipamento(resolver_clientes(cliente), id, _json(dados))


# ===================================================================== certificados
@frappe.whitelist()
def certificados(cliente=None, filtros=None):
	return get_adapter().listar_certificados(resolver_clientes(cliente), _json(filtros))


@frappe.whitelist()
def certificado(id, cliente=None):
	return _nao_encontrado(get_adapter().obter_certificado(resolver_clientes(cliente), id))


@frappe.whitelist()
def baixar_certificado(id, cliente=None):
	file_url = get_adapter().obter_arquivo_certificado(resolver_clientes(cliente), id)
	if not file_url:
		raise frappe.DoesNotExistError(_("Este certificado não possui arquivo."))
	arquivo = frappe.get_doc("File", {"file_url": file_url})
	frappe.local.response.filename = arquivo.file_name
	frappe.local.response.filecontent = arquivo.get_content()
	frappe.local.response.type = "download"


@frappe.whitelist(methods=["POST"])
def analisar_certificado(id, status, observacao=None, cliente=None):
	if status not in ("Aprovado", "Reprovado"):
		frappe.throw(_("Status de análise inválido."))
	return get_adapter().registrar_analise_critica(
		resolver_clientes(cliente), id, status, observacao, frappe.session.user
	)


@frappe.whitelist(methods=["POST"])
def anexar_certificado_externo(dados=None, cliente=None):
	if not _config().permitir_certificado_externo and not is_usuario_interno():
		raise frappe.PermissionError(_("Envio de certificados externos está desabilitado."))
	escopo = resolver_escopo_unico(cliente)
	dados = _json(dados or frappe.form_dict.get("dados"))

	file_url = None
	if upload := frappe.request.files.get("file"):
		if not upload.filename.lower().endswith(".pdf"):
			frappe.throw(_("Envie o certificado em PDF."))
		arquivo = frappe.get_doc(
			{"doctype": "File", "file_name": upload.filename, "content": upload.stream.read(), "is_private": 1}
		).insert(ignore_permissions=True)
		file_url = arquivo.file_url

	cert = get_adapter().criar_certificado_externo(escopo, dados, file_url)
	if file_url:
		frappe.db.set_value(
			"File", arquivo.name, {"attached_to_doctype": "Certificado Calibracao", "attached_to_name": cert["id"]}
		)
	return cert


# ===================================================================== ordens de serviço
@frappe.whitelist()
def ordens(cliente=None, filtros=None):
	return get_adapter().listar_ordens(resolver_clientes(cliente), _json(filtros))


@frappe.whitelist()
def ordem(id, cliente=None):
	return _nao_encontrado(get_adapter().obter_ordem(resolver_clientes(cliente), id))


@frappe.whitelist(methods=["POST"])
def solicitar_servico(dados, cliente=None):
	return get_adapter().solicitar_servico(resolver_escopo_unico(cliente), get_contato_do_usuario(), _json(dados))


@frappe.whitelist(methods=["POST"])
def responder_orcamento(id, aprovado, cliente=None):
	return get_adapter().responder_orcamento(resolver_clientes(cliente), id, frappe.utils.cint(aprovado))


# ===================================================================== verificação intermediária
@frappe.whitelist(methods=["POST"])
def registrar_verificacao(id, dados, cliente=None):
	return get_adapter().registrar_verificacao(resolver_clientes(cliente), id, _json(dados))
