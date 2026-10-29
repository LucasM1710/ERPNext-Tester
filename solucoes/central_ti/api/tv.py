"""Painel da TV (/ti/tv?chave=…): indicadores sem login, por um link secreto revogável.

A TV não abre sessão no ERP: o link só dá acesso a esta leitura agregada. Por padrão, sem nomes
de colaboradores (a TV costuma ficar em área comum) — configurável em Configuracao Central TI.
"""

import secrets
from collections import Counter

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_datetime, get_first_day, get_url, getdate, now_datetime, today

from solucoes.central_ti.api.central import _exigir_tecnico
from solucoes.central_ti.doctype.chamado_ti.chamado_ti import ABERTOS, tecnicos_ativos
from solucoes.central_ti.doctype.equipamento_ti.equipamento_ti import INATIVOS
from solucoes.central_ti.sla import CONFIG, config

PESO_SLA = {"Violado": 0, "Em Risco": 1}
PESO_PRIORIDADE = {"Crítica": 0, "Alta": 1, "Média": 2, "Baixa": 3}


# ===================================================================== gestão do link (equipe de TI)
def _info_link():
	cfg = config()
	return {
		"ativo": bool(cfg.tv_ativo and cfg.tv_chave),
		"url": get_url(f"/ti/tv?chave={cfg.tv_chave}") if cfg.tv_ativo and cfg.tv_chave else None,
		"mostrar_nomes": bool(cfg.tv_mostrar_nomes),
		"segundos_slide": cint(cfg.tv_segundos_slide) or 20,
	}


@frappe.whitelist()
def link():
	_exigir_tecnico()
	return _info_link()


@frappe.whitelist(methods=["POST"])
def gerar_link():
	"""Cria um link novo (o anterior para de funcionar na hora)."""
	_exigir_tecnico()
	frappe.db.set_single_value(CONFIG, {"tv_chave": secrets.token_urlsafe(24), "tv_ativo": 1})
	frappe.clear_document_cache(CONFIG, CONFIG)
	return _info_link()


@frappe.whitelist(methods=["POST"])
def desativar_link():
	_exigir_tecnico()
	frappe.db.set_single_value(CONFIG, {"tv_chave": None, "tv_ativo": 0})
	frappe.clear_document_cache(CONFIG, CONFIG)
	return _info_link()


# ===================================================================== dados da TV (sem login)
@frappe.whitelist(allow_guest=True)
def dados(chave=None):
	cfg = config()
	if not (cfg.tv_ativo and cfg.tv_chave and chave and secrets.compare_digest(str(chave), cfg.tv_chave)):
		raise frappe.PermissionError(_("Link da TV inválido ou revogado. Gere um novo em Indicadores > Modo TV."))

	agora = now_datetime()
	hoje = getdate(today())
	inicio_mes = get_datetime(get_first_day(hoje))
	campos = [
		"name", "assunto", "categoria", "prioridade", "status", "responsavel", "nome_solicitante", "departamento",
		"aberto_em", "primeira_resposta_em", "prazo_resposta", "prazo_resolucao", "sla_resposta", "sla_resolucao",
		"resolvido_em", "avaliacao", "horas_resolucao",
	]  # fmt: skip
	recentes = frappe.get_all("Chamado TI", filters=[["modified", ">=", add_days(hoje, -40)]], fields=campos, limit_page_length=0)
	abertos = frappe.get_all("Chamado TI", filters={"status": ["in", ABERTOS]}, fields=campos, limit_page_length=0)

	def pior_sla(c):
		return min(PESO_SLA.get(c.sla_resposta, 9), PESO_SLA.get(c.sla_resolucao, 9))

	def no(valor, desde):
		return bool(valor) and get_datetime(valor) >= desde

	# ---------------------------------------------------------------- atenção agora
	atencao = sorted(
		[c for c in abertos if pior_sla(c) < 9 or c.prioridade in ("Crítica", "Alta")],
		key=lambda c: (pior_sla(c), PESO_PRIORIDADE.get(c.prioridade, 9), str(c.aberto_em)),
	)[:7]
	mostrar_nomes = bool(cfg.tv_mostrar_nomes)

	def primeiro_nome(usuario):
		return (frappe.utils.get_fullname(usuario) or "").split(" ")[0] if usuario else None

	def item(c):
		sla = "Violado" if pior_sla(c) == 0 else "Em Risco" if pior_sla(c) == 1 else None
		prazo = c.prazo_resolucao if c.primeira_resposta_em else c.prazo_resposta
		return {
			"id": c.name,
			"assunto": c.assunto,
			"categoria": c.categoria,
			"departamento": c.departamento,
			"solicitante": c.nome_solicitante if mostrar_nomes else None,
			"prioridade": c.prioridade,
			"status": c.status,
			"sla": sla,
			"prazo": str(prazo) if prazo else None,
			"tecnico": primeiro_nome(c.responsavel),
			"aberto_em": str(c.aberto_em),
		}

	# ---------------------------------------------------------------- mês corrente
	resolvidos_mes = [c for c in recentes if no(c.resolvido_em, inicio_mes) and c.status in ("Resolvido", "Fechado")]
	respondidos_mes = [c for c in recentes if no(c.primeira_resposta_em, inicio_mes)]
	avaliados_mes = [c.avaliacao for c in resolvidos_mes if c.avaliacao]

	def pct(parte, total):
		return round(100 * parte / total) if total else None

	serie = {str(add_days(hoje, -i)): [0, 0] for i in range(13, -1, -1)}
	for c in recentes:
		if c.aberto_em and str(getdate(c.aberto_em)) in serie:
			serie[str(getdate(c.aberto_em))][0] += 1
		if c.resolvido_em and str(getdate(c.resolvido_em)) in serie:
			serie[str(getdate(c.resolvido_em))][1] += 1

	# ---------------------------------------------------------------- patrimônio
	equipamentos = frappe.get_all(
		"Equipamento TI", filters={"status": ["not in", INATIVOS]}, fields=["name", "tipo", "garantia_ate", "fim_vida_util", "valor_compra"], limit_page_length=0
	)
	em_60 = add_days(hoje, 60)
	garantias = sorted(
		[e for e in equipamentos if e.garantia_ate and hoje <= getdate(e.garantia_ate) <= getdate(em_60)], key=lambda e: str(e.garantia_ate)
	)
	proximo_ano = [e for e in equipamentos if e.fim_vida_util and getdate(e.fim_vida_util).year == hoje.year + 1]
	estoque_baixo = [
		{"item": i.name, "quantidade": cint(i.quantidade), "minimo": cint(i.minimo)}
		for i in frappe.get_all("Item Estoque TI", filters={"ativo": 1}, fields=["name", "quantidade", "minimo"])
		if cint(i.quantidade) < cint(i.minimo)
	]

	carga = Counter(c.responsavel for c in abertos if c.responsavel)
	resolvidos_por = Counter(c.responsavel for c in resolvidos_mes if c.responsavel)
	return {
		"titulo": cfg.titulo or "Central de TI",
		"empresa": frappe.defaults.get_global_default("company"),
		"gerado_em": str(agora),
		"segundos_slide": cint(cfg.tv_segundos_slide) or 20,
		"agora": {
			"abertos": len(abertos),
			"sem_responsavel": sum(1 for c in abertos if not c.responsavel),
			"em_risco": sum(1 for c in abertos if pior_sla(c) == 1),
			"vencidos": sum(1 for c in abertos if pior_sla(c) == 0),
			"aguardando_usuario": sum(1 for c in abertos if c.status == "Aguardando Usuário"),
			"criticos": sum(1 for c in abertos if c.prioridade == "Crítica"),
		},
		"atencao": [item(c) for c in atencao],
		"hoje": {
			"abertos": sum(1 for c in recentes if c.aberto_em and getdate(c.aberto_em) == hoje),
			"resolvidos": sum(1 for c in recentes if c.resolvido_em and getdate(c.resolvido_em) == hoje),
		},
		"serie": {"dias": list(serie), "abertos": [v[0] for v in serie.values()], "resolvidos": [v[1] for v in serie.values()]},
		"mes": {
			"nome": hoje.strftime("%m/%Y"),
			"resolvidos": len(resolvidos_mes),
			"sla_resposta_pct": pct(sum(1 for c in respondidos_mes if c.sla_resposta == "Cumprido"), len(respondidos_mes)),
			"sla_resolucao_pct": pct(sum(1 for c in resolvidos_mes if c.sla_resolucao == "Cumprido"), len(resolvidos_mes)),
			"csat": round(sum(avaliados_mes) / len(avaliados_mes), 1) if avaliados_mes else None,
			"csat_satisfeitos_pct": pct(sum(1 for a in avaliados_mes if a >= 4), len(avaliados_mes)),
			"mttr_h": round(sum(flt(c.horas_resolucao) for c in resolvidos_mes) / len(resolvidos_mes), 1) if resolvidos_mes else None,
		},
		"tecnicos": [
			{"nome": primeiro_nome(t), "abertos": carga.get(t, 0), "resolvidos_mes": resolvidos_por.get(t, 0)} for t in tecnicos_ativos()
		],
		"patrimonio": {
			"equipamentos": len(equipamentos),
			"garantias_60d": [{"nome": e.name, "tipo": e.tipo, "ate": str(e.garantia_ate)} for e in garantias[:6]],
			"garantias_60d_total": len(garantias),
			"vida_util_vencida": sum(1 for e in equipamentos if e.fim_vida_util and getdate(e.fim_vida_util) <= hoje),
			"renovacao_proximo_ano": {"ano": hoje.year + 1, "quantidade": len(proximo_ano), "valor": round(sum(flt(e.valor_compra) for e in proximo_ano))},
			"estoque_baixo": estoque_baixo,
		},
	}
