"""Tarefas automáticas da Central de TI (scheduler)."""

import frappe
from frappe import _
from frappe.utils import get_datetime

from solucoes.central_ti import notificacoes
from solucoes.central_ti.sla import agora, config, expediente, horas_uteis_entre

ABERTOS = ("Aberto", "Em Atendimento", "Aguardando Usuário")


def atualizar_sla():
	"""A cada 15 min: recalcula a situação do SLA dos chamados em aberto e avisa a TI
	quando um prazo entra em risco ou vence (um aviso por mudança de situação)."""
	momento = agora()
	for nome in frappe.get_all("Chamado TI", filters={"status": ["in", ABERTOS]}, pluck="name"):
		doc = frappe.get_doc("Chamado TI", nome)
		antes = (doc.sla_resposta, doc.sla_resolucao)
		doc.atualizar_sla(momento)
		depois = (doc.sla_resposta, doc.sla_resolucao)
		if antes == depois:
			continue
		frappe.db.set_value(
			"Chamado TI", nome, {"sla_resposta": doc.sla_resposta, "sla_resolucao": doc.sla_resolucao}, update_modified=False
		)
		for qual, (velho, novo) in (("resposta", (antes[0], depois[0])), ("resolucao", (antes[1], depois[1]))):
			if novo != velho and novo in ("Em Risco", "Violado"):
				notificacoes.alerta_sla(doc, novo, qual)
	frappe.db.commit()


def fechar_resolvidos():
	"""De hora em hora: fecha chamados resolvidos sem retorno do colaborador após N dias úteis."""
	cfg = config()
	dias = cfg.dias_fechamento_automatico or 0
	if dias <= 0:
		return
	exp = expediente()
	horas_dia = (get_datetime(f"2000-01-01 {exp.fim}") - get_datetime(f"2000-01-01 {exp.inicio}")).total_seconds() / 3600
	momento = agora()
	for c in frappe.get_all("Chamado TI", filters={"status": "Resolvido", "resolvido_em": ["is", "set"]}, fields=["name", "resolvido_em"]):
		if horas_uteis_entre(c.resolvido_em, momento, exp) < dias * horas_dia:
			continue
		doc = frappe.get_doc("Chamado TI", c.name)
		doc.status = "Fechado"
		doc.flags.ignore_permissions = True
		doc.save()
		from solucoes.central_ti.doctype.chamado_ti.chamado_ti import registrar_sistema

		registrar_sistema(doc.name, _("Fechado automaticamente após {0} dia(s) útil(eis) sem retorno do colaborador.").format(dias))
	frappe.db.commit()
