"""API da Central de TI (página /ti).

Colaborador: vê só os próprios chamados. Técnico (papel "Tecnico TI", System Manager ou
listado na configuração): fila, atribuição, status, notas internas e painel.
Os colaboradores não precisam de permissão nos DocTypes: todo acesso passa por aqui.
"""

import json
from collections import Counter
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, getdate, now_datetime, strip_html_tags, today

from solucoes.central_ti.doctype.chamado_ti.chamado_ti import ABERTOS, ENCERRADOS, tecnicos_ativos
from solucoes.central_ti.servico import registrar_resposta
from solucoes.central_ti.sla import config, prazos_da_prioridade

PAPEIS_TECNICO = ("Tecnico TI", "System Manager")
QUANDO = {
	"Crítica": "Afeta várias pessoas ou a empresa",
	"Alta": "Não consigo trabalhar",
	"Média": "Atrapalha, mas consigo trabalhar",
	"Baixa": "Consigo trabalhar normalmente",
}
CAMPOS_LISTA = [
	"name", "assunto", "categoria", "prioridade", "status", "responsavel", "solicitante", "email_solicitante",
	"nome_solicitante", "departamento", "canal", "aberto_em", "prazo_resposta", "prazo_resolucao",
	"primeira_resposta_em", "resolvido_em", "sla_resposta", "sla_resolucao", "avaliacao", "modified", "equipamento",
]  # fmt: skip


# ===================================================================== sessão
def _usuario():
	if frappe.session.user == "Guest":
		raise frappe.PermissionError(_("Faça login para acessar a Central de TI."))
	return frappe.session.user


def eh_tecnico(usuario=None):
	usuario = usuario or frappe.session.user
	return bool(set(frappe.get_roles(usuario)) & set(PAPEIS_TECNICO)) or usuario in tecnicos_ativos()


def _exigir_tecnico():
	_usuario()
	if not eh_tecnico():
		raise frappe.PermissionError(_("Área exclusiva da equipe de TI."))


def _meus_filtros(usuario):
	email = frappe.db.get_value("User", usuario, "email") or usuario
	return [["solicitante", "=", usuario]], [["email_solicitante", "=", email]]


def _do_usuario(doc, usuario):
	email = frappe.db.get_value("User", usuario, "email") or usuario
	return doc.solicitante == usuario or (doc.email_solicitante or "").lower() == email.lower()


def _chamado_acessivel(id):
	usuario = _usuario()
	if not frappe.db.exists("Chamado TI", id):
		raise frappe.DoesNotExistError(_("Chamado não encontrado."))
	doc = frappe.get_doc("Chamado TI", id)
	tecnico = eh_tecnico(usuario)
	if not tecnico and not _do_usuario(doc, usuario):
		raise frappe.DoesNotExistError(_("Chamado não encontrado."))
	return doc, tecnico


def _json(valor, padrao=None):
	if isinstance(valor, str):
		return json.loads(valor) if valor else padrao
	return valor if valor is not None else padrao


# ===================================================================== formatação
_nomes_cache = {}


def _nome(usuario):
	if not usuario:
		return None
	if usuario not in _nomes_cache:
		_nomes_cache[usuario] = frappe.utils.get_fullname(usuario) or usuario
	return _nomes_cache[usuario]


def _icones():
	return dict(frappe.get_all("Categoria Chamado TI", fields=["name", "icone"], as_list=True))


def _resumo(d, icones=None):
	icones = icones if icones is not None else _icones()
	return {
		"id": d.name,
		"assunto": d.assunto,
		"categoria": d.categoria,
		"icone": icones.get(d.categoria) or "life-buoy",
		"prioridade": d.prioridade,
		"status": d.status,
		"aberto": d.status in ABERTOS,
		"responsavel": d.responsavel,
		"responsavel_nome": _nome(d.responsavel),
		"solicitante_nome": d.nome_solicitante or d.email_solicitante,
		"departamento": d.departamento,
		"canal": d.canal,
		"aberto_em": str(d.aberto_em) if d.aberto_em else None,
		"atualizado_em": str(d.modified),
		"prazo_resposta": str(d.prazo_resposta) if d.prazo_resposta else None,
		"prazo_resolucao": str(d.prazo_resolucao) if d.prazo_resolucao else None,
		"respondido": bool(d.primeira_resposta_em),
		"resolvido_em": str(d.resolvido_em) if d.resolvido_em else None,
		"sla_resposta": d.sla_resposta,
		"sla_resolucao": d.sla_resolucao,
		"avaliacao": d.avaliacao,
		"equipamento": d.get("equipamento"),
	}


def _salvar_anexos(chamado):
	urls = []
	for arquivo in frappe.request.files.getlist("arquivos") if frappe.request and frappe.request.files else []:
		f = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": arquivo.filename,
				"content": arquivo.stream.read(),
				"is_private": 1,
				"attached_to_doctype": "Chamado TI",
				"attached_to_name": chamado,
			}
		).insert(ignore_permissions=True)
		urls.append(f.file_url)
	return urls


def _equipamento_permitido(equipamento, tecnico, solicitante):
	"""Colaborador só vincula equipamento que está com ele; técnico, qualquer um."""
	if not frappe.db.exists("Equipamento TI", equipamento):
		frappe.throw(_("Equipamento não encontrado."))
	if not tecnico and frappe.db.get_value("Equipamento TI", equipamento, "responsavel") != solicitante:
		raise frappe.PermissionError(_("Este equipamento não está com você."))
	return equipamento


# ===================================================================== contexto
@frappe.whitelist()
def contexto():
	usuario = _usuario()
	cfg = config()
	tecnico = eh_tecnico(usuario)
	ou_meus = _meus_filtros(usuario)
	meus = frappe.get_all("Chamado TI", or_filters=ou_meus[0] + ou_meus[1], filters={"status": ["in", ABERTOS]}, fields=["status"])
	dados = {
		"usuario": {
			"email": usuario,
			"nome": _nome(usuario),
			"imagem": frappe.db.get_value("User", usuario, "user_image"),
			"tecnico": tecnico,
		},
		"titulo": cfg.titulo or "Central de TI",
		"empresa": frappe.defaults.get_global_default("company"),
		"email_ti": cfg.email_ti,
		# para o manual: prazos reais configurados, com o impacto que leva a cada prioridade
		"prazos": [
			{"prioridade": p, "quando": QUANDO.get(p, ""), "resposta": r, "resolucao": s}
			for p, (r, s) in ((p, prazos_da_prioridade(p)) for p in ("Crítica", "Alta", "Média", "Baixa"))
		],
		"categorias": frappe.get_all(
			"Categoria Chamado TI", filters={"ativo": 1}, fields=["name as nome", "icone", "descricao"], order_by="ordem asc, name asc"
		),
		"contadores": {
			"meus_abertos": len(meus),
			"aguardando_voce": sum(1 for m in meus if m.status == "Aguardando Usuário"),
		},
	}
	if tecnico:
		abertos = frappe.get_all("Chamado TI", filters={"status": ["in", ABERTOS]}, fields=["responsavel", "sla_resposta", "sla_resolucao"])
		dados["tecnicos"] = [{"id": t, "nome": _nome(t)} for t in tecnicos_ativos()]
		dados["contadores"].update(
			{
				"fila_minha": sum(1 for a in abertos if a.responsavel == usuario),
				"fila_sem_responsavel": sum(1 for a in abertos if not a.responsavel),
				"fila_risco": sum(1 for a in abertos if "Violado" in (a.sla_resposta, a.sla_resolucao) or "Em Risco" in (a.sla_resposta, a.sla_resolucao)),
				"fila_abertos": len(abertos),
			}
		)
	return dados


# ===================================================================== colaborador
@frappe.whitelist()
def meus_chamados(filtro="abertos"):
	usuario = _usuario()
	ou = _meus_filtros(usuario)
	f = {}
	if filtro == "abertos":
		f["status"] = ["in", ABERTOS]
	elif filtro == "encerrados":
		f["status"] = ["in", ENCERRADOS]
	linhas = frappe.get_all("Chamado TI", filters=f, or_filters=ou[0] + ou[1], fields=CAMPOS_LISTA, order_by="modified desc", limit=200)
	icones = _icones()
	return [_resumo(d, icones) for d in linhas]


@frappe.whitelist(methods=["POST"])
def abrir_chamado(assunto, descricao=None, categoria=None, impacto=None, solicitante=None, canal=None, prioridade=None, equipamento=None):
	usuario = _usuario()
	if not (assunto or "").strip():
		frappe.throw(_("Informe um título para o chamado."))
	tecnico = eh_tecnico(usuario)
	doc = frappe.get_doc(
		{
			"doctype": "Chamado TI",
			"assunto": assunto.strip()[:140],
			"descricao": descricao,
			"categoria": categoria if categoria and frappe.db.exists("Categoria Chamado TI", categoria) else None,
			"impacto": impacto,
			# técnico pode abrir em nome de outra pessoa (telefone, presencial)
			"solicitante": solicitante if (tecnico and solicitante) else usuario,
			"canal": canal if (tecnico and canal) else "Portal",
		}
	)
	if tecnico and prioridade:
		doc.prioridade = prioridade
		doc.flags.prioridade_manual = True
	if equipamento:
		doc.equipamento = _equipamento_permitido(equipamento, tecnico, doc.solicitante)
	doc.insert(ignore_permissions=True)
	_salvar_anexos(doc.name)
	return _resumo(frappe.get_doc("Chamado TI", doc.name))


@frappe.whitelist()
def chamado(id):
	doc, tecnico = _chamado_acessivel(id)
	filtros = {"chamado": doc.name}
	if not tecnico:
		filtros["tipo"] = ["!=", "Nota Interna"]
	interacoes = frappe.get_all(
		"Interacao Chamado TI",
		filters=filtros,
		fields=["name", "tipo", "via", "autor", "autor_nome", "de_tecnico", "mensagem", "anexos", "creation"],
		order_by="creation asc",
	)
	anexos = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Chamado TI", "attached_to_name": doc.name},
		fields=["name", "file_name", "file_size", "file_url", "creation"],
		order_by="creation asc",
	)
	dados = _resumo(doc)
	dados.update(
		{
			"descricao": doc.descricao,
			"solucao": doc.solucao,
			"impacto": doc.impacto,
			"email_solicitante": doc.email_solicitante if tecnico else None,
			"comentario_avaliacao": doc.comentario_avaliacao,
			"horas_primeira_resposta": doc.horas_primeira_resposta,
			"horas_resolucao": doc.horas_resolucao,
			"horas_pausadas": doc.horas_pausadas,
			"reaberturas": doc.reaberturas,
			"equipamento_info": _equipamento_resumo(doc.equipamento),
			"interacoes": [
				{
					"id": i.name,
					"tipo": i.tipo,
					"via": i.via,
					"autor_nome": i.autor_nome,
					"eu": i.autor == frappe.session.user,
					"de_tecnico": bool(i.de_tecnico),
					"mensagem": i.mensagem,
					"anexos": [a for a in (i.anexos or "").split("\n") if a],
					"em": str(i.creation),
				}
				for i in interacoes
			],
			"anexos": [{"id": a.name, "nome": a.file_name, "tamanho": a.file_size, "url": a.file_url, "em": str(a.creation)} for a in anexos],
			"pode": {
				"gerenciar": tecnico,
				"responder": doc.status not in ("Fechado", "Cancelado"),
				"avaliar": (not tecnico or _do_usuario(doc, frappe.session.user))
				and doc.status in ("Resolvido", "Fechado")
				and not doc.avaliacao,
				"reabrir": doc.status in ("Resolvido", "Fechado") and (tecnico or _do_usuario(doc, frappe.session.user)),
				"cancelar": doc.status in ABERTOS and (tecnico or (_do_usuario(doc, frappe.session.user) and doc.status == "Aberto")),
			},
		}
	)
	return dados


def _equipamento_resumo(nome):
	if not nome or not frappe.db.exists("Equipamento TI", nome):
		return None
	e = frappe.db.get_value(
		"Equipamento TI", nome, ["name", "tipo", "modelo", "processador", "memoria_ram", "armazenamento", "garantia_ate", "qtd_chamados"], as_dict=True
	)
	return {
		"id": e.name,
		"tipo": e.tipo,
		"icone": frappe.db.get_value("Tipo Equipamento TI", e.tipo, "icone") or "package",
		"modelo": e.modelo,
		"resumo": " · ".join(x for x in (e.processador, e.memoria_ram, e.armazenamento) if x),
		"garantia_ate": str(e.garantia_ate) if e.garantia_ate else None,
		"qtd_chamados": e.qtd_chamados,
	}


@frappe.whitelist(methods=["POST"])
def responder(id, mensagem, interna=0):
	doc, tecnico = _chamado_acessivel(id)
	if doc.status in ("Fechado", "Cancelado"):
		frappe.throw(_("Este chamado está encerrado. Reabra-o para continuar a conversa."))
	if not strip_html_tags(mensagem or "").strip() and not (frappe.request and frappe.request.files):
		frappe.throw(_("Escreva uma mensagem."))
	anexos = _salvar_anexos(doc.name)
	registrar_resposta(
		doc,
		mensagem=mensagem,
		autor=frappe.session.user,
		de_tecnico=tecnico and not _do_usuario(doc, frappe.session.user),
		via="Portal",
		anexos=anexos,
		interna=bool(cint(interna)) and tecnico,
	)
	return chamado(id)


@frappe.whitelist(methods=["POST"])
def avaliar(id, nota, comentario=None):
	doc, _tecnico = _chamado_acessivel(id)
	if not _do_usuario(doc, frappe.session.user):
		raise frappe.PermissionError(_("Só quem abriu o chamado pode avaliá-lo."))
	nota = cint(nota)
	if nota < 1 or nota > 5:
		frappe.throw(_("A avaliação vai de 1 a 5."))
	if doc.status not in ("Resolvido", "Fechado"):
		frappe.throw(_("O chamado ainda não foi resolvido."))
	frappe.db.set_value("Chamado TI", doc.name, {"avaliacao": nota, "comentario_avaliacao": comentario})
	from solucoes.central_ti.doctype.chamado_ti.chamado_ti import registrar_sistema

	registrar_sistema(doc.name, _("Atendimento avaliado com nota {0}.").format(nota))
	return chamado(id)


@frappe.whitelist(methods=["POST"])
def reabrir(id, motivo):
	doc, tecnico = _chamado_acessivel(id)
	if doc.status not in ("Resolvido", "Fechado"):
		frappe.throw(_("Só chamados resolvidos ou fechados podem ser reabertos."))
	if not (motivo or "").strip():
		frappe.throw(_("Conte o que ainda não está funcionando."))
	registrar_resposta(doc, mensagem=motivo, autor=frappe.session.user, de_tecnico=False, via="Portal")
	doc.reload()
	if doc.status in ("Resolvido", "Fechado"):
		doc.status = "Em Atendimento"
		doc.flags.ignore_permissions = True
		doc.save()
	return chamado(id)


@frappe.whitelist(methods=["POST"])
def cancelar(id, motivo=None):
	doc, tecnico = _chamado_acessivel(id)
	if not chamado(id)["pode"]["cancelar"]:
		raise frappe.PermissionError(_("Este chamado não pode mais ser cancelado por você."))
	if motivo:
		registrar_resposta(doc, mensagem=motivo, autor=frappe.session.user, de_tecnico=tecnico, via="Portal", interna=False)
		doc.reload()
	doc.status = "Cancelado"
	doc.flags.ignore_permissions = True
	doc.save()
	return chamado(id)


@frappe.whitelist()
def baixar_anexo(id, arquivo):
	doc, _tecnico = _chamado_acessivel(id)
	f = frappe.get_doc("File", arquivo)
	if f.attached_to_doctype != "Chamado TI" or f.attached_to_name != doc.name:
		raise frappe.PermissionError
	frappe.local.response.update(
		{"filename": f.file_name, "filecontent": f.get_content(), "type": "download", "display_content_as": "inline"}
	)


# ===================================================================== equipe de TI
@frappe.whitelist(methods=["POST"])
def alterar(id, status=None, prioridade=None, responsavel=None, categoria=None, solucao=None, equipamento=None):
	_exigir_tecnico()
	doc, _t = _chamado_acessivel(id)
	if status:
		if status == "Resolvido" and not strip_html_tags(solucao or doc.solucao or "").strip():
			frappe.throw(_("Descreva a solução antes de resolver: ela vai para o colaborador e para a base de conhecimento."))
		doc.status = status
	if solucao is not None:
		doc.solucao = solucao
	if prioridade:
		doc.prioridade = prioridade
	if responsavel:
		doc.responsavel = None if responsavel == "-" else responsavel  # "-" = sem responsável
	if categoria:
		doc.categoria = categoria
	if equipamento:
		doc.equipamento = None if equipamento == "-" else _equipamento_permitido(equipamento, True, None)
	if doc.status in ("Em Atendimento", "Resolvido") and not doc.primeira_resposta_em and status:
		doc.registrar_primeira_resposta()
	doc.flags.ignore_permissions = True
	doc.save()
	return chamado(id)


@frappe.whitelist()
def fila(aba="minha", busca=None, categoria=None, prioridade=None):
	_exigir_tecnico()
	usuario = frappe.session.user
	f = {}
	if aba == "minha":
		f.update({"status": ["in", ABERTOS], "responsavel": usuario})
	elif aba == "sem_responsavel":
		f.update({"status": ["in", ABERTOS], "responsavel": ["is", "not set"]})
	elif aba == "abertos":
		f["status"] = ["in", ABERTOS]
	elif aba == "encerrados":
		f.update({"status": ["in", ENCERRADOS], "modified": [">=", add_days(today(), -60)]})
	if categoria:
		f["categoria"] = categoria
	if prioridade:
		f["prioridade"] = prioridade
	or_filters = None
	if busca:
		like = f"%{busca}%"
		or_filters = {"name": ["like", like], "assunto": ["like", like], "nome_solicitante": ["like", like], "departamento": ["like", like]}
	linhas = frappe.get_all("Chamado TI", filters=f, or_filters=or_filters, fields=CAMPOS_LISTA, limit=500, order_by="modified desc")
	icones = _icones()
	lista = [_resumo(d, icones) for d in linhas]
	if aba == "risco":
		lista = [c for c in lista if c["aberto"] and ({c["sla_resposta"], c["sla_resolucao"]} & {"Em Risco", "Violado"})]
	ordem_p = {"Crítica": 0, "Alta": 1, "Média": 2, "Baixa": 3}
	ordem_sla = {"Violado": 0, "Em Risco": 1}
	if aba != "encerrados":
		lista.sort(
			key=lambda c: (
				min(ordem_sla.get(c["sla_resposta"], 9), ordem_sla.get(c["sla_resolucao"], 9)),
				ordem_p.get(c["prioridade"], 9),
				c["prazo_resolucao"] or "9999",
			)
		)
	return lista


@frappe.whitelist()
def buscar_pessoas(texto=None):
	_exigir_tecnico()
	like = f"%{texto or ''}%"
	return frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": ["in", ["System User", "Website User"]], "name": ["not in", ["Administrator", "Guest"]]},
		or_filters={"full_name": ["like", like], "name": ["like", like]},
		fields=["name as id", "full_name as nome"],
		limit=15,
		order_by="full_name asc",
	)


@frappe.whitelist()
def painel(dias=30):
	_exigir_tecnico()
	dias = max(7, min(cint(dias) or 30, 365))
	inicio = get_datetime(add_days(today(), -dias + 1))
	todos = frappe.get_all(
		"Chamado TI",
		filters=[["modified", ">=", add_days(inicio, -400)]],
		fields=CAMPOS_LISTA + ["horas_primeira_resposta", "horas_resolucao", "reaberturas", "fechado_em"],
		limit_page_length=0,
	)

	def no_periodo(valor):
		return bool(valor) and get_datetime(valor) >= inicio

	abertos_agora = [c for c in todos if c.status in ABERTOS]
	criados = [c for c in todos if no_periodo(c.aberto_em)]
	resolvidos = [c for c in todos if no_periodo(c.resolvido_em) and c.status in ("Resolvido", "Fechado")]
	respondidos = [c for c in todos if no_periodo(c.primeira_resposta_em)]
	avaliados = [c for c in resolvidos if c.avaliacao]

	# FCR: resolvidos sem reabertura e com no máximo uma resposta da TI
	respostas_ti = Counter(
		frappe.get_all(
			"Interacao Chamado TI",
			filters={"chamado": ["in", [c.name for c in resolvidos] or [""]], "tipo": "Resposta", "de_tecnico": 1},
			pluck="chamado",
		)
	)

	def pct(parte, total):
		return round(100 * parte / total, 1) if total else None

	def media(valores):
		valores = [v for v in valores if v is not None]
		return round(sum(valores) / len(valores), 1) if valores else None

	serie = {}
	for i in range(dias):
		serie[str(getdate(add_days(inicio, i)))] = [0, 0]
	for c in criados:
		chave = str(getdate(c.aberto_em))
		if chave in serie:
			serie[chave][0] += 1
	for c in resolvidos:
		chave = str(getdate(c.resolvido_em))
		if chave in serie:
			serie[chave][1] += 1

	por_tecnico = {}
	for t in tecnicos_ativos():
		meus_res = [c for c in resolvidos if c.responsavel == t]
		meus_av = [c.avaliacao for c in meus_res if c.avaliacao]
		por_tecnico[t] = {
			"id": t,
			"nome": _nome(t),
			"abertos": sum(1 for c in abertos_agora if c.responsavel == t),
			"resolvidos": len(meus_res),
			"mttr": media([c.horas_resolucao for c in meus_res]),
			"csat": media(meus_av),
		}

	return {
		"dias": dias,
		"kpis": {
			"abertos": len(abertos_agora),
			"sem_responsavel": sum(1 for c in abertos_agora if not c.responsavel),
			"em_risco": sum(1 for c in abertos_agora if "Em Risco" in (c.sla_resposta, c.sla_resolucao) and "Violado" not in (c.sla_resposta, c.sla_resolucao)),
			"violados": sum(1 for c in abertos_agora if "Violado" in (c.sla_resposta, c.sla_resolucao)),
			"aguardando_usuario": sum(1 for c in abertos_agora if c.status == "Aguardando Usuário"),
			"criados": len(criados),
			"resolvidos": len(resolvidos),
			"sla_resposta_pct": pct(sum(1 for c in respondidos if c.sla_resposta == "Cumprido"), len(respondidos)),
			"sla_resolucao_pct": pct(sum(1 for c in resolvidos if c.sla_resolucao == "Cumprido"), len(resolvidos)),
			"tempo_primeira_resposta_h": media([c.horas_primeira_resposta for c in respondidos]),
			"mttr_h": media([c.horas_resolucao for c in resolvidos]),
			"fcr_pct": pct(sum(1 for c in resolvidos if not c.reaberturas and respostas_ti.get(c.name, 0) <= 1), len(resolvidos)),
			"reabertos_pct": pct(sum(1 for c in resolvidos if c.reaberturas), len(resolvidos)),
			"csat": media([c.avaliacao for c in avaliados]),
			"csat_satisfeitos_pct": pct(sum(1 for c in avaliados if c.avaliacao >= 4), len(avaliados)),
			"taxa_avaliacao_pct": pct(len(avaliados), len(resolvidos)),
		},
		"serie": {"dias": list(serie), "criados": [v[0] for v in serie.values()], "resolvidos": [v[1] for v in serie.values()]},
		"por_categoria": Counter(c.categoria or "Sem categoria" for c in criados).most_common(),
		"por_prioridade": {p: sum(1 for c in abertos_agora if c.prioridade == p) for p in ("Crítica", "Alta", "Média", "Baixa")},
		"por_status": {s: sum(1 for c in abertos_agora if c.status == s) for s in ABERTOS},
		"por_tecnico": list(por_tecnico.values()),
		"csat_distribuicao": {n: sum(1 for c in avaliados if c.avaliacao == n) for n in range(1, 6)},
		"idade_fila": _idade_fila(abertos_agora),
		"recorrentes": _recorrentes(),
	}


def _idade_fila(abertos):
	"""Chamados em aberto por tempo de vida (dias corridos): fila envelhecendo = acúmulo escondido."""
	faixas = [("até 1 dia", 1), ("1 a 3 dias", 3), ("3 a 7 dias", 7), ("7 a 15 dias", 15), ("mais de 15 dias", None)]
	contagem = dict.fromkeys([f for f, _l in faixas], 0)
	agora = now_datetime()
	for c in abertos:
		dias = (agora - get_datetime(c.aberto_em)).total_seconds() / 86400 if c.aberto_em else 0
		for faixa, limite in faixas:
			if limite is None or dias < limite:
				contagem[faixa] += 1
				break
	return contagem


def _recorrentes():
	"""Problemas que voltam: categorias mês a mês (3 meses) e equipamentos com 3+ chamados em 90 dias."""
	hoje = getdate(today())
	inicio_janela = getdate(add_days(hoje, -92)).replace(day=1)
	linhas = frappe.get_all("Chamado TI", filters={"aberto_em": [">=", inicio_janela]}, fields=["categoria", "aberto_em", "equipamento"], limit_page_length=0)
	chaves = sorted({str(getdate(l.aberto_em))[:7] for l in linhas})[-3:]
	por_categoria = {}
	for l in linhas:
		mes = str(getdate(l.aberto_em))[:7]
		if mes in chaves:
			por_categoria.setdefault(l.categoria or "Sem categoria", dict.fromkeys(chaves, 0))[mes] += 1
	categorias = sorted(por_categoria.items(), key=lambda kv: -sum(kv[1].values()))[:6]
	desde = add_days(hoje, -90)
	equip = Counter(l.equipamento for l in linhas if l.equipamento and getdate(l.aberto_em) >= getdate(desde))
	return {
		"meses": chaves,
		"categorias": [{"categoria": k, "por_mes": [v[m] for m in chaves]} for k, v in categorias],
		"equipamentos": [{"id": e, "chamados": n} for e, n in equip.most_common() if n >= 3][:8],
	}
