"""Instalação/atualização do app sem `bench migrate`.

	bench --site <site> execute solucoes.setup.instalar

Antes da primeira instalação na produção, conferir (só leitura):

	bench execute solucoes.setup.conferir

Idempotente: pode rodar quantas vezes quiser (após cada `git pull`). Faz:
1. garante os Module Defs do app;
2. sincroniza os DocTypes do app a partir dos JSONs (criação e alterações de campos);
3. nenhum Custom Field em DocType nativo (a configuração por cliente fica em Cliente Portal);
4. grava defaults ausentes da Configuracao Portal Metrologia;
5. limpa o cache.

O mesmo passo também roda no `after_migrate`, caso alguém use `bench migrate`.
"""

import os

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.model.sync import sync_for

APP = "solucoes"

# Nenhum campo em DocType nativo: a configuração por cliente fica em "Cliente Portal".
CAMPOS_CUSTOMIZADOS = {}


def instalar():
	garantir_modulos()
	sync_for(APP, force=True)
	after_migrate()
	frappe.db.commit()
	frappe.clear_cache()
	print("solucoes: DocTypes sincronizados, custom fields e configurações atualizados.")


def conferir():
	"""Conferência ANTES de instalar na produção. Só lê, não grava nada.

		bench execute solucoes.setup.conferir
	"""
	problemas = []
	# 1) Campos do ERP (ordem_servico, rastreabilidade, CRM) que o portal lê
	campos = {
		"Equipamentos": ["customer", "tag", "descricao", "grandeza", "marca_equipamento", "modelo_equipamento", "numero_serie", "capacidade", "tipo_equipamento"],
		"Ordem Servico Interna": ["status_order_service", "informe_numero_serie", "data_cal", "data_cal_recomendada", "anexo_certificado", "cal_rbc", "situacao_equipamento", "entry_date", "data_saida", "delivery_note_date", "repair_schedule_date"],
		"Ordem Servico Externa": ["status_order_service", "informe_numero_serie", "data_cal", "data_cal_recomendada", "anexo_certificado", "cal_rbc", "sales_order_reference", "repair_schedule_date"],
		"Rastreabilidade Padrao OS": ["codigo", "descricao", "certificado_padrao", "validade", "status", "arquivo_padrao", "padrao"],
		"Padrao de Calibracao": ["arquivo"],
		"Opportunity": ["contact_email", "contact_display", "opportunity_owner"],
		"CRM Note": ["note", "added_by", "added_on"],
	}  # fmt: skip
	for doctype, lista in campos.items():
		if not frappe.db.table_exists(doctype):
			problemas.append(f"FALTA a tabela {doctype}")
			continue
		problemas += [f"FALTA o campo {doctype}.{c}" for c in lista if not frappe.db.has_column(doctype, c)]

	# 2) Nenhum DocType/módulo do app (portal, Central de TI e Fiscal) pode já existir em outro app
	for pasta_modulo, nome_modulo in (("metrologia", "Metrologia"), ("central_ti", "Central TI"), ("fiscal", "Fiscal")):
		raiz = frappe.get_app_path(APP, pasta_modulo, "doctype")
		for pasta in sorted(os.listdir(raiz)):
			caminho = os.path.join(raiz, pasta, f"{pasta}.json")
			if not os.path.exists(caminho):
				continue
			nome = frappe.get_file_json(caminho)["name"]
			modulo = frappe.db.get_value("DocType", nome, "module")
			if modulo and modulo != nome_modulo:
				problemas.append(f"CONFLITO: já existe o DocType {nome} no módulo {modulo}")
	for modulo in frappe.get_module_list(APP):
		app = frappe.db.get_value("Module Def", modulo, "app_name")
		if app and app != APP:
			problemas.append(f"CONFLITO: o módulo {modulo} já pertence ao app {app}")

	print("\n=== Conferência do portal (nada foi alterado) ===")
	print("\n".join(problemas) if problemas else "OK: campos do ERP presentes e nenhum conflito de nomes.")

	# 3) Informativo
	padrao = frappe.db.get_value("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}, "email_id")
	portal = frappe.db.get_value("Email Account", {"email_id": "portal@eranalitica.com.br"}, ["enable_outgoing", "default_outgoing"], as_dict=True)
	print(f"E-mail padrão de saída: {padrao or 'NENHUM (os e-mails do portal não sairão)'}")
	print(f"Conta portal@eranalitica.com.br: {'existe' + (' (ATENÇÃO: marcada como padrão de saída)' if portal.default_outgoing else '') if portal else 'ainda não criada'}")
	print(f"App já ligado no site: {'sim' if APP in frappe.get_installed_apps() else 'não'}")
	return not problemas


def after_migrate():
	create_custom_fields(CAMPOS_CUSTOMIZADOS, update=True)
	preencher_padroes_configuracao()
	# Central de TI: papel Tecnico TI, defaults, prazos de SLA, categorias e tipos de equipamento
	from solucoes.central_ti.instalacao import configurar

	configurar()
	# Fiscal: defaults da configuração e naturezas de operação padrão
	from solucoes.fiscal.instalacao import configurar as configurar_fiscal

	configurar_fiscal()


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
