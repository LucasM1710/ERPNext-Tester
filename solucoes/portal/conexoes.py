"""Seção "Portal do cliente" nas Conexões do cadastro do Cliente (ERP).

Mostra, a partir do Customer, tudo o que o portal amarra a ele — com contagem e link —,
sem campo novo no Customer (os doctypes do portal guardam o cliente no campo `cliente`).
"""

from frappe import _

DOCTYPES_PORTAL = [
	"Cliente Portal",
	"Distrito Cliente",
	"Usuario Portal Cliente",
	"Distrito Equipamento",
	"Equipamento Cliente",
	"Log Portal",
]


def customer_dashboard(data):
	data = data or {}
	data.setdefault("non_standard_fieldnames", {})
	for doctype in DOCTYPES_PORTAL:
		data["non_standard_fieldnames"][doctype] = "cliente"
	transacoes = data.setdefault("transactions", [])
	# A cadeia que alimenta o portal: equipamentos e OS do ERP (campo `customer`)...
	transacoes.append({"label": _("Equipamentos e OS"), "items": ["Equipamentos", "Ordem Servico Interna", "Ordem Servico Externa"]})
	# ...e o que o portal guarda (campo `cliente`).
	transacoes.append({"label": _("Portal do cliente"), "items": DOCTYPES_PORTAL})
	return data
