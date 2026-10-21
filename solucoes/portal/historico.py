"""Histórico de atendimento: as notas (aba Comentários, tabela CRM Note) das oportunidades
que a ER liberou para cada Gestor/Líder no cadastro do acesso.

Nada é liberado por padrão: só as oportunidades escolhidas, uma a uma, aparecem no portal.
"""

import frappe
from frappe.utils import get_fullname
from frappe.utils.html_utils import sanitize_html

from solucoes.portal.sessao import is_usuario_interno

OPP = "Opportunity"


def oportunidades_do_cliente(cliente):
	"""Oportunidades do cliente (para a ER escolher), mais recentes primeiro, com o contato e o nº de notas."""
	opps = frappe.get_all(
		OPP,
		filters={"opportunity_from": "Customer", "party_name": cliente},
		fields=["name as id", "title", "status", "transaction_date", "creation", "contact_email", "contact_display", "opportunity_owner"],
		order_by="creation desc",
		limit=500,
	)
	notas = {}
	for n in frappe.get_all("CRM Note", filters={"parenttype": OPP, "parent": ["in", [o.id for o in opps] or [""]]}, fields=["parent", "added_on"]):
		qtd, ultima = notas.get(n.parent, (0, None))
		notas[n.parent] = (qtd + 1, max(filter(None, [ultima, n.added_on]), default=None))
	for o in opps:
		o.notas, o.ultima_nota = notas.get(o.id, (0, None))
		o.contact_email = (o.contact_email or "").strip().lower() or None
		o.contato = (o.contact_display or "").split("\n")[0].strip() or None
		o.responsavel = get_fullname(o.opportunity_owner) if o.opportunity_owner else None
		del o["contact_display"], o["opportunity_owner"]
	return opps


def liberadas(escopo):
	"""{cliente: [oportunidades]} que o usuário logado pode ver.

	Usuário do portal: as do próprio acesso (Gestor/Líder, ativo, com o histórico habilitado).
	Usuário interno: as liberadas para qualquer acesso ativo do cliente (para conferir o que o cliente vê).
	"""
	filtros = {"cliente": ["in", list(escopo) or [""]], "ativo": 1, "ver_historico": 1, "perfil": ["!=", "Usuário"]}
	if not is_usuario_interno():
		filtros["usuario"] = frappe.session.user
	por_cliente = {}
	for a in frappe.get_all("Usuario Portal Cliente", filters=filtros, fields=["name", "cliente"]):
		for o in frappe.get_all("Usuario Portal Oportunidade", filters={"parent": a.name, "parenttype": "Usuario Portal Cliente"}, pluck="oportunidade"):
			por_cliente.setdefault(a.cliente, set()).add(o)
	return por_cliente


def historico(escopo):
	"""Oportunidades liberadas com as notas (mais recentes primeiro). Revalida o vínculo com o cliente."""
	resultado = []
	for cliente, opps in liberadas(escopo).items():
		for o in frappe.get_all(
			OPP,
			filters={"name": ["in", list(opps)], "opportunity_from": "Customer", "party_name": cliente},
			fields=["name as id", "title", "status", "transaction_date", "creation"],
		):
			o.cliente = cliente
			o.notas = [
				{
					"texto": sanitize_html(n.note or ""),
					"autor": get_fullname(n.added_by) if n.added_by else "ER Analítica",
					"data": n.added_on,
				}
				for n in frappe.get_all(
					"CRM Note",
					filters={"parenttype": OPP, "parent": o.id},
					fields=["note", "added_by", "added_on"],
					order_by="added_on desc",
				)
			]
			o.ultima_nota = o.notas[0]["data"] if o.notas else None
			resultado.append(o)
	resultado.sort(key=lambda o: str(o.ultima_nota or o.creation), reverse=True)
	return resultado
