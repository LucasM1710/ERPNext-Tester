"""Página de entrada do portal (/acesso): recuperação de senha com o e-mail do portal."""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60 * 60)
def recuperar_senha(email=None):
	"""Envia o link de nova senha a um usuário do portal. A resposta é sempre a mesma,
	exista ou não o e-mail (não revela quem tem acesso)."""
	email = (email or "").strip().lower()
	if email and frappe.db.get_value("User", email, "enabled") and frappe.db.exists(
		"Usuario Portal Cliente", {"usuario": email, "ativo": 1}
	):
		from solucoes.portal.emails import enviar_recuperacao

		enviar_recuperacao(email)
	return _("Se o e-mail tiver acesso ao portal, você receberá o link para criar uma nova senha.")
