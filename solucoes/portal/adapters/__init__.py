import frappe

from solucoes.portal.adapters.base import PortalAdapter

ADAPTER_PADRAO = "solucoes.portal.adapters.padrao.AdapterPadrao"


def get_adapter() -> PortalAdapter:
	"""Instancia o adapter configurado em Configuracao Portal Metrologia (ou o padrão)."""
	caminho = frappe.db.get_single_value("Configuracao Portal Metrologia", "adapter") or ADAPTER_PADRAO
	classe = frappe.get_attr(caminho)
	if not issubclass(classe, PortalAdapter):
		frappe.throw(f"{caminho} precisa herdar de PortalAdapter")
	return classe()
