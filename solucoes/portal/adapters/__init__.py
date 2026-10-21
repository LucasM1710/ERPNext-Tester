import frappe

from solucoes.portal.adapters.base import PortalAdapter

ADAPTER_PADRAO = "solucoes.portal.adapters.padrao.AdapterPadrao"
# Página /consulta: lê os DocTypes da empresa (Equipamentos, OS Interna/Externa), só leitura.
ADAPTER_CONSULTA = "solucoes.portal.adapters.er.AdapterER"


def modo_portal() -> str:
	"""Qual página fez a chamada: "consulta" (/consulta) ou "completo" (/cliente)."""
	return "consulta" if frappe.form_dict.get("portal") == "consulta" else "completo"


def get_adapter() -> PortalAdapter:
	"""Adapter da página que chamou: /consulta usa o da empresa; /cliente, o configurado (ou o padrão)."""
	if modo_portal() == "consulta":
		caminho = ADAPTER_CONSULTA
	else:
		caminho = frappe.db.get_single_value("Configuracao Portal Metrologia", "adapter") or ADAPTER_PADRAO
	classe = frappe.get_attr(caminho)
	if not issubclass(classe, PortalAdapter):
		frappe.throw(f"{caminho} precisa herdar de PortalAdapter")
	return classe()
