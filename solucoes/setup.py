"""Instalação/atualização do app sem `bench migrate`.

	bench --site <site> execute solucoes.setup.instalar

Idempotente: pode rodar quantas vezes quiser (após cada `git pull`). Faz:
1. garante os Module Defs do app;
2. sincroniza os DocTypes do app a partir dos JSONs (criação e alterações de campos);
3. cria/atualiza os Custom Fields em DocTypes nativos (Customer etc.);
4. grava defaults ausentes da Configuracao Portal Metrologia;
5. limpa o cache.

O mesmo passo também roda no `after_migrate`, caso alguém use `bench migrate`.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.model.sync import sync_for

APP = "solucoes"

CAMPOS_CUSTOMIZADOS = {
	"Customer": [
		{
			"fieldname": "usa_controle_distritos",
			"fieldtype": "Check",
			"label": "Portal: controle por distritos",
			"description": "Equipamentos organizados por distrito; usuários do portal veem apenas os distritos atribuídos (gestores veem todos).",
			"insert_after": "portal_users",
		},
	],
}


def instalar():
	garantir_modulos()
	sync_for(APP, force=True)
	after_migrate()
	frappe.db.commit()
	frappe.clear_cache()
	print("solucoes: DocTypes sincronizados, custom fields e configurações atualizados.")


def after_migrate():
	create_custom_fields(CAMPOS_CUSTOMIZADOS, update=True)
	preencher_padroes_configuracao()


def garantir_modulos():
	for modulo in frappe.get_module_list(APP):
		if not frappe.db.exists("Module Def", modulo):
			frappe.get_doc({"doctype": "Module Def", "module_name": modulo, "app_name": APP}).insert(
				ignore_permissions=True
			)


def preencher_padroes_configuracao():
	"""Grava o default de campos da configuração ainda sem valor.

	Um Single só usa os defaults enquanto não tem nenhum valor salvo; ao gravar um campo
	(ou ao surgir um campo novo), os demais ficariam vazios (0 em Checks).
	"""
	doctype = "Configuracao Portal Metrologia"
	singles = frappe.qb.DocType("Singles")
	salvos = set(frappe.qb.from_(singles).select(singles.field).where(singles.doctype == doctype).run(pluck=True))
	for campo in frappe.get_meta(doctype).fields:
		if campo.default is not None and campo.fieldname not in salvos:
			frappe.db.set_single_value(doctype, campo.fieldname, campo.default)
