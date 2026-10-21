"""Página inicial dos usuários do portal.

Outro app (o Builder) também define a página inicial dos usuários de site, e esse
gancho tem prioridade sobre o `role_home_page`. Aqui, quem tem acesso ao portal vai
para /consulta; para os demais usuários, a decisão continua sendo a do outro app.
"""

import frappe

ESTE = "solucoes.portal.pagina_inicial.pagina_inicial"


def pagina_inicial(usuario=None):
	usuario = usuario or frappe.session.user
	if usuario != "Guest" and _usuario_do_portal(usuario):
		return "consulta"
	for metodo in reversed(frappe.get_hooks("get_website_user_home_page")):
		if metodo != ESTE:
			return frappe.get_attr(metodo)(usuario)
	return None


def _usuario_do_portal(usuario) -> bool:
	if frappe.db.exists("Usuario Portal Cliente", {"usuario": usuario, "ativo": 1}):
		return True
	return frappe.db.get_value("User", usuario, "user_type") == "Website User" and "Customer" in frappe.get_roles(usuario)
