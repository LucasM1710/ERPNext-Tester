"""API das telas da página /consulta: visão operacional, rastreabilidade, relatórios e logs.

Tudo passa pelo escopo do usuário (clientes, perfil e distritos) e pelo AdapterER.
"""

import json
from collections import Counter

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, today

from solucoes.portal import auditoria, historico
from solucoes.portal.adapters.er import AdapterER
from solucoes.portal.sessao import get_escopo, is_usuario_interno, resolver_clientes

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
STATUS = ["Calibrado", "Alerta 60", "Crítico", "Vencido", "Agendado", "Sem calibração"]


def _json(valor):
	if isinstance(valor, str):
		return json.loads(valor) if valor else {}
	return valor or {}


def _adapter():
	frappe.form_dict.portal = "consulta"
	return AdapterER()


# ===================================================================== visão operacional
@frappe.whitelist()
def painel(cliente=None):
	escopo = resolver_clientes(cliente)
	adapter = _adapter()
	equipamentos = [e for e in adapter.listar_equipamentos(escopo) if e.get("status") not in ("Inativo", "Sucateado")]
	contagem = Counter(e["status_calibracao"] for e in equipamentos)

	ano = getdate(today()).year
	previsto, executado = [0] * 12, [0] * 12
	for e in equipamentos:
		if e.get("proxima_calibracao"):
			d = getdate(e["proxima_calibracao"])
			if d.year == ano:
				previsto[d.month - 1] += 1
	for c in adapter.listar_certificados(escopo, {"de": f"{ano}-01-01"}):
		d = getdate(c["data_calibracao"]) if c.get("data_calibracao") else None
		if d and d.year == ano:
			executado[d.month - 1] += 1

	distritos = {}
	for e in equipamentos:
		chave = e.get("distrito") or ""
		g = distritos.setdefault(
			chave,
			{
				"distrito": e.get("distrito_nome") or "Sem distrito",
				"owner": e.get("owner"),
				"uf": e.get("uf"),
				"cidade": e.get("cidade"),
				"cliente": e.get("cliente_nome"),
				"total": 0,
				**{s: 0 for s in STATUS},
			},
		)
		g["total"] += 1
		g[e["status_calibracao"]] += 1
	for g in distritos.values():
		base = g["total"] - g["Sem calibração"]
		g["em_dia_pct"] = round(100 * (g["Calibrado"] + g["Alerta 60"] + g["Agendado"]) / base, 1) if base else None

	urgentes = [e for e in equipamentos if e["dias_para_vencer"] is not None and e["dias_para_vencer"] <= 45]
	urgentes.sort(key=lambda e: e["dias_para_vencer"])
	return {
		"ano": ano,
		"kpis": {
			"cadastrados": len(equipamentos),
			"calibrados": contagem["Calibrado"] + contagem["Alerta 60"],
			"criticos": contagem["Crítico"],
			"vencidos": contagem["Vencido"],
			"agendados": contagem["Agendado"],
			"sem_calibracao": contagem["Sem calibração"],
			"laboratorio": sum(1 for e in equipamentos if e["origem"] == "laboratorio"),
			"terceiros": sum(1 for e in equipamentos if e["origem"] == "cliente"),
		},
		"por_mes": [{"mes": MESES[i], "previsto": previsto[i], "executado": executado[i]} for i in range(12)],
		"status": [{"nome": s, "valor": contagem[s]} for s in STATUS],
		"distritos": sorted(distritos.values(), key=lambda g: (g["distrito"] == "Sem distrito", g["distrito"])),
		"urgentes": urgentes[:50],
	}


# ===================================================================== rastreabilidade
@frappe.whitelist()
def rastreabilidade(id, cliente=None):
	"""Histórico de certificados do equipamento + padrões usados na última calibração da ER."""
	escopo = resolver_clientes(cliente)
	adapter = _adapter()
	eqp = adapter.obter_equipamento(escopo, id)
	if not eqp:
		raise frappe.DoesNotExistError(_("Equipamento não encontrado."))
	certificados = adapter.listar_certificados(escopo, {"equipamento": id})
	padroes, os_padroes = [], None
	if eqp["origem"] == "laboratorio":
		for c in certificados:
			d = adapter._os_do_escopo(escopo, c["id"])
			if d and (lista := adapter.padroes_da_os(d)):
				padroes, os_padroes = lista, d.name
				break
	return {
		"equipamento": eqp,
		"certificados": certificados,
		"ordens": adapter.listar_ordens(escopo, {"equipamento": id}) if eqp["origem"] == "laboratorio" else [],
		"padroes": padroes,
		"os_padroes": os_padroes,
	}


@frappe.whitelist()
def baixar_certificado_padrao(os, linha, cliente=None):
	file_url = _adapter().arquivo_do_padrao(resolver_clientes(cliente), os, linha)
	if not file_url:
		raise frappe.DoesNotExistError(_("O certificado deste padrão ainda não está disponível."))
	_entregar(file_url)


def _entregar(file_url):
	arquivo = frappe.get_doc("File", {"file_url": file_url})
	frappe.local.response.filename = arquivo.file_name
	frappe.local.response.filecontent = arquivo.get_content()
	frappe.local.response.type = "download"


# ===================================================================== relatórios
COLUNAS = [
	("Status", lambda e: e["status_calibracao"]),
	("Calibrado por", lambda e: e["vendor"]),
	("Nº de série", lambda e: e.get("numero_serie") or ""),
	("TAG", lambda e: e.get("tag") or ""),
	("Equipamento", lambda e: e.get("descricao") or ""),
	("Marca", lambda e: e.get("fabricante") or ""),
	("Modelo", lambda e: e.get("modelo") or ""),
	("Últ. calibração", lambda e: _br(e.get("ultima_calibracao"))),
	("Próx. calibração", lambda e: _br(e.get("proxima_calibracao"))),
	("Dias p/ vencer", lambda e: "" if e["dias_para_vencer"] is None else e["dias_para_vencer"]),
	("Certificado", lambda e: e.get("certificado") or ""),
	("Responsável", lambda e: e.get("owner") or ""),
	("Distrito", lambda e: e.get("distrito_nome") or ""),
	("UF", lambda e: e.get("uf") or ""),
	("Cidade", lambda e: e.get("cidade") or ""),
	("Cliente", lambda e: e.get("cliente_nome") or ""),
	("Obs.", lambda e: e.get("observacao") or ""),
]


def _br(valor):
	return getdate(valor).strftime("%d/%m/%Y") if valor else ""


def _relatorio(escopo, filtros):
	adapter = _adapter()
	lista = adapter.listar_equipamentos(
		escopo, {k: filtros.get(k) for k in ("distrito", "owner", "status_calibracao", "origem") if filtros.get(k)}
	)
	if filtros.get("de") or filtros.get("ate"):
		de, ate = filtros.get("de") or "0000-01-01", filtros.get("ate") or "9999-12-31"
		lista = [e for e in lista if e.get("ultima_calibracao") and de <= e["ultima_calibracao"] <= ate]
	por_owner = {}
	for e in lista:
		chave = (e.get("owner") or "Sem responsável", e.get("distrito_nome") or "Sem distrito")
		g = por_owner.setdefault(chave, {"owner": chave[0], "distrito": chave[1], "total": 0, **{s: 0 for s in STATUS}})
		g["total"] += 1
		g[e["status_calibracao"]] += 1
	vencimentos = [e for e in lista if e["dias_para_vencer"] is not None and e["dias_para_vencer"] <= 90]
	for e in vencimentos:
		d = e["dias_para_vencer"]
		e["faixa"] = "Vencido" if d < 0 else "Até 30 dias" if d <= 30 else "31 a 60 dias" if d <= 60 else "61 a 90 dias"
	return {
		"equipamentos": lista,
		"por_owner": sorted(por_owner.values(), key=lambda g: (g["distrito"], g["owner"])),
		"vencimentos": sorted(vencimentos, key=lambda e: e["dias_para_vencer"]),
	}


@frappe.whitelist()
def relatorio(filtros=None, cliente=None):
	return _relatorio(resolver_clientes(cliente), _json(filtros))


@frappe.whitelist()
def exportar(formato="xlsx", filtros=None, cliente=None):
	"""Relatório de equipamentos em Excel ou PDF (mesmas colunas da tela)."""
	escopo = resolver_clientes(cliente)
	filtros = _json(filtros)
	lista = _relatorio(escopo, filtros)["equipamentos"]
	cabecalho = [c[0] for c in COLUNAS]
	linhas = [[c[1](e) for c in COLUNAS] for e in lista]
	nome = f"relatorio-equipamentos-{today()}"
	auditoria.registrar("Exportação de relatório", escopo[0] if len(escopo) == 1 else None, depois={"formato": formato, **filtros})

	if formato == "pdf":
		from frappe.utils.pdf import get_pdf

		html = frappe.render_template(
			"solucoes/templates/relatorio_equipamentos.html",
			{"cabecalho": cabecalho, "linhas": linhas, "filtros": filtros, "gerado_em": frappe.utils.now_datetime(),
			 "empresa": frappe.defaults.get_global_default("company"), "usuario": frappe.utils.get_fullname()},
		)
		frappe.local.response.filename = nome + ".pdf"
		frappe.local.response.filecontent = get_pdf(html, {"orientation": "Landscape"})
		frappe.local.response.type = "download"
		return

	from frappe.utils.xlsxutils import make_xlsx

	arquivo = make_xlsx([cabecalho, *linhas], "Equipamentos")
	frappe.local.response.filename = nome + ".xlsx"
	frappe.local.response.filecontent = arquivo.getvalue()
	frappe.local.response.type = "download"


# ===================================================================== logs
@frappe.whitelist()
def logs(filtros=None, cliente=None):
	"""Auditoria: usuário interno vê tudo; gestor vê os logs dos clientes que administra."""
	filtros = _json(filtros)
	f = {}
	interno = is_usuario_interno()
	geridos = None
	if not interno:
		escopo = get_escopo()
		geridos = [c for c in escopo if escopo.eh_gestor(c)]
		if not geridos:
			raise frappe.PermissionError(_("Apenas gestores podem ver a auditoria."))
		f["cliente"] = ["in", geridos]
	if cliente:
		if geridos is not None and cliente not in geridos:
			raise frappe.PermissionError(_("Você não administra este cliente."))
		f["cliente"] = cliente
	if filtros.get("usuario"):
		f["usuario"] = filtros["usuario"]
	if filtros.get("acao"):
		f["acao"] = filtros["acao"]
	de, ate = filtros.get("de"), filtros.get("ate")
	if de or ate:
		f["creation"] = ["between", [de or "2000-01-01", add_days(ate, 1) if ate else "2999-12-31"]]
	linhas = frappe.get_all(
		"Log Portal",
		filters=f,
		fields=["name", "creation", "usuario", "cliente", "acao", "referencia_doctype", "referencia", "valor_anterior", "valor_novo"],
		order_by="creation desc",
		limit=cint(filtros.get("limite")) or 500,
	)
	nomes = dict(frappe.get_all("User", filters={"name": ["in", list({l.usuario for l in linhas}) or [""]]}, fields=["name", "full_name"], as_list=True))
	clientes = dict(frappe.get_all("Customer", filters={"name": ["in", list({l.cliente for l in linhas if l.cliente}) or [""]]}, fields=["name", "customer_name"], as_list=True))
	for l in linhas:
		l.usuario_nome = nomes.get(l.usuario) or l.usuario
		l.cliente_nome = clientes.get(l.cliente) or l.cliente
	return {"logs": linhas, "acoes": sorted(set(frappe.get_all("Log Portal", filters={k: v for k, v in f.items() if k == "cliente"}, pluck="acao", distinct=True)))}


# ===================================================================== histórico de atendimento
@frappe.whitelist()
def historico_atendimento(cliente=None):
	"""Notas das oportunidades que a ER liberou para o usuário (Gestor/Líder com o histórico habilitado)."""
	return historico.historico(resolver_clientes(cliente))
