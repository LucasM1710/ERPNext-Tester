import frappe

no_cache = 1


def get_context(context):
	# Já logado: vai direto para o portal (ou para onde pediu).
	if frappe.session.user != "Guest":
		frappe.local.flags.redirect_location = frappe.form_dict.get("redirect-to") or "/consulta"
		raise frappe.Redirect
	context.no_breadcrumbs = True
