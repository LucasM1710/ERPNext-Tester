"""Auditoria do portal: o que cada usuário do portal acessou, baixou ou alterou.

Grava em "Log Portal". Uma falha aqui nunca impede a ação do usuário.
"""

import json

import frappe
from frappe.utils import today


def registrar(acao, cliente=None, doctype=None, nome=None, antes=None, depois=None):
	try:
		frappe.get_doc(
			{
				"doctype": "Log Portal",
				"usuario": frappe.session.user,
				"cliente": cliente,
				"acao": acao,
				"referencia_doctype": doctype,
				"referencia": nome,
				"pagina": frappe.form_dict.get("portal") or None,
				"valor_anterior": _json(antes),
				"valor_novo": _json(depois),
			}
		).insert(ignore_permissions=True)
		# Acesso e download são requisições GET, que o Frappe não confirma no banco: grava aqui.
		if getattr(frappe.local, "request", None) and frappe.local.request.method == "GET":
			frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Portal: falha ao registrar auditoria")


def registrar_acesso(clientes):
	"""Um registro de acesso por usuário e dia (o portal chama o contexto a cada página)."""
	if frappe.db.exists(
		"Log Portal", {"usuario": frappe.session.user, "acao": "Acesso ao portal", "creation": [">=", today()]}
	):
		return
	registrar("Acesso ao portal", cliente=clientes[0] if len(clientes) == 1 else None)


def _json(valor):
	if valor in (None, "", {}, []):
		return None
	return json.dumps(valor, ensure_ascii=False, default=str, indent=1)
