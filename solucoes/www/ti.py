import frappe

no_cache = 1


def get_context(context):
	# Painel da TV: abre sem login com ?chave=… (a chave é validada pela API solucoes.central_ti.api.tv.dados)
	if frappe.request.path.rstrip("/") == "/ti/tv" and frappe.form_dict.get("chave"):
		context.csrf_token = ""
		return

	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=" + frappe.utils.quote(frappe.request.path)
		raise frappe.Redirect

	context.csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()
