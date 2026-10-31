"""Dados de DEMONSTRAÇÃO do módulo Fiscal — NUNCA rodar em produção.

	bench --site erp.localhost execute solucoes.fiscal.demo.criar

Só roda com a Configuração Fiscal em "Simulação" e uma única vez (para refazer, apague os dados demo).
Cria: dados fictícios da nossa empresa, cadastros fiscais de clientes, itens de serviço e produto,
faturas para emitir e um histórico (notas, boletos pagos/vencidos, remessa e retorno).
"""

import frappe
from frappe.utils import add_days, getdate, today

from solucoes.fiscal import emissao, util

MARCA = "FISCAL-DEMO"
EMPRESA_CNPJ = "11.222.333/0001-81"  # CNPJ de exemplo, válido só no formato

CLIENTES = {  # cliente demo -> cadastro fiscal (Laticínios Delta fica SEM cadastro, para mostrar a pendência)
	"Indústria Alfa Demo": dict(base="45997418", uf="SP", municipio="São Paulo", codigo_municipio="3550308", cep="01310-100",
	                            logradouro="Avenida Paulista", numero="1000", bairro="Bela Vista", contribuinte_icms="Contribuinte",
	                            inscricao_estadual="110.042.490.114", email_nota="fiscal@alfa.demo"),
	"Metalúrgica Beta Demo": dict(base="17895646", uf="MG", municipio="Belo Horizonte", codigo_municipio="3106200", cep="30130-010",
	                              logradouro="Avenida Afonso Pena", numero="1500", bairro="Centro", contribuinte_icms="Contribuinte",
	                              inscricao_estadual="062.307.904.0081", email_nota="nfe@beta.demo", iss_retido=1, retem_impostos_federais=1),
	"Saneamento Gama Demo": dict(base="43776517", uf="SP", municipio="Campinas", codigo_municipio="3509502", cep="13015-904",
	                             logradouro="Avenida Anchieta", numero="200", bairro="Centro", contribuinte_icms="Não contribuinte",
	                             retem_impostos_federais=1),
}  # fmt: skip

SERVICOS = [  # código, nome, preço
	("SRV-CAL-BAL", "Calibração de balança analítica (RBC)", 180),
	("SRV-CAL-TERM", "Calibração de termômetro digital", 95),
	("SRV-CAL-PIP", "Calibração de pipeta automática", 70),
	("SRV-CAL-MAN", "Calibração de manômetro", 120),
	("SRV-MANUT", "Manutenção corretiva de balança", 350),
]
PRODUTOS = [  # código, nome, preço, NCM
	("PRD-PESO-1KG", "Peso padrão 1 kg classe M1 em aço inox", 650, "84239090"),
	("PRD-TERMO", "Termômetro digital tipo espeto -50 a 300 °C", 240, "90251990"),
]


def criar():
	cfg = frappe.get_single("Configuracao Fiscal")
	if cfg.ambiente != "Simulação":
		print("RECUSADO: a Configuração Fiscal não está em Simulação. A demo nunca roda fora da simulação.")
		return
	if frappe.db.exists("Item", "SRV-CAL-BAL"):
		print("A demo fiscal já foi criada (o item SRV-CAL-BAL existe). Nada foi feito.")
		return
	frappe.flags.mute_emails = True
	usuario_financeiro()
	configurar_empresa(cfg)
	cadastrar_clientes()
	criar_itens()
	historico()
	faturas_para_emitir()
	frappe.db.commit()
	print("Demo fiscal criada. Abra /fiscal.")


def apagar():
	"""Remove tudo o que a demo criou (faturas e recebimentos são cancelados antes) e zera a numeração.

	bench --site erp.localhost execute solucoes.fiscal.demo.apagar
	"""
	if frappe.db.get_single_value("Configuracao Fiscal", "ambiente") != "Simulação":
		print("RECUSADO: só apaga em Simulação.")
		return
	faturas = frappe.get_all("Sales Invoice", filters={"remarks": MARCA}, pluck="name")
	ref = frappe.qb.DocType("Payment Entry Reference")
	pagamentos = set(frappe.qb.from_(ref).select(ref.parent).where(ref.reference_name.isin(faturas or [""])).run(pluck=True))
	for nome in pagamentos:
		pe = frappe.get_doc("Payment Entry", nome)
		if pe.docstatus == 1:
			pe.cancel()
		frappe.delete_doc("Payment Entry", nome, force=True, ignore_permissions=True)
	for nome in frappe.get_all("Boleto Cobranca", pluck="name"):
		frappe.delete_doc("Boleto Cobranca", nome, force=True, ignore_permissions=True)
	for nome in frappe.get_all("Nota Fiscal", pluck="name"):
		frappe.delete_doc("Nota Fiscal", nome, force=True, ignore_permissions=True)
	for nome in faturas:
		si = frappe.get_doc("Sales Invoice", nome)
		if si.docstatus == 1:
			si.cancel()
		frappe.delete_doc("Sales Invoice", nome, force=True, ignore_permissions=True)
	partes = [*CLIENTES, "Laticínios Delta Demo", "Laboratório Externo de Calibração Demo"]
	for nome in frappe.get_all("Dados Fiscais Parte", or_filters={"observacao": MARCA, "parte": ["in", partes]}, pluck="name"):
		frappe.delete_doc("Dados Fiscais Parte", nome, force=True, ignore_permissions=True)
	for codigo, *_ in SERVICOS + PRODUTOS:
		if frappe.db.exists("Item", codigo):
			frappe.delete_doc("Item", codigo, force=True, ignore_permissions=True)
	frappe.db.sql("delete from tabSeries where name in ('NF-', 'BOL-') or name like 'NF-20%%' or name like 'BOL-20%%'")
	for campo in ("proximo_numero_nfe", "proximo_numero_dps", "proximo_nosso_numero"):
		frappe.db.set_single_value("Configuracao Fiscal", campo, 1)
	frappe.db.commit()
	print(f"Demo fiscal apagada: {len(faturas)} faturas, {len(pagamentos)} recebimentos.")


def usuario_financeiro():
	"""Auxiliar de financeiro demo: bia.financeiro@demo.com / Demo@12345 (papel Accounts User)."""
	email = "bia.financeiro@demo.com"
	if frappe.db.exists("User", email):
		return
	u = frappe.get_doc({"doctype": "User", "email": email, "first_name": "Beatriz", "last_name": "Prado", "send_welcome_email": 0,
	                    "user_type": "System User", "new_password": "Demo@12345", "roles": [{"role": "Accounts User"}]})  # fmt: skip
	u.flags.ignore_password_policy = True
	u.insert(ignore_permissions=True)


def configurar_empresa(cfg):
	empresa = cfg.empresa or frappe.db.get_value("Company", {}, "name")
	cfg.update({
		"empresa": empresa, "razao_social": "Soluções LMTECH Calibração Ltda (DEMO)", "nome_fantasia": "LMTECH Metrologia",
		"cnpj": EMPRESA_CNPJ, "inscricao_estadual": "244.123.456.119", "inscricao_municipal": "123456-7", "regime_tributario": "Lucro Presumido",
		"cnae": "7120-1/00", "telefone": "(19) 3333-0000", "email": "financeiro@lmtech.demo",
		"logradouro": "Rua das Calibrações", "numero": "123", "bairro": "Distrito Industrial", "cep": "13069-000",
		"municipio": "Campinas", "codigo_municipio": "3509502", "uf": "SP",
		"codigo_servico_nacional": "140101", "item_lista_servico": "14.01", "aliquota_iss": 2,
		"informacoes_complementares": "", "chave_pix": "financeiro@lmtech.demo", "banco_nome": "Banco Simulado", "banco_codigo": "000",
		"data_inicio": "2026-01-01",
		"conta_recebimento": frappe.db.get_value("Account", {"company": empresa, "account_type": "Bank", "is_group": 0}, "name"),
		"conta_retencoes": frappe.db.get_value("Account", {"company": empresa, "account_name": ["like", "Outros Impostos%Recuperar"], "is_group": 0}, "name"),
	})  # fmt: skip
	cfg.save(ignore_permissions=True)


def cadastrar_clientes():
	for cliente, d in CLIENTES.items():
		if not frappe.db.exists("Customer", cliente):
			frappe.get_doc({"doctype": "Customer", "customer_name": cliente, "customer_type": "Company"}).insert(ignore_permissions=True)
		cnpj = util.formatar_documento(util.completar_cnpj(d.pop("base") + "0001"))
		frappe.db.set_value("Customer", cliente, "tax_id", cnpj)
		frappe.get_doc({"doctype": "Dados Fiscais Parte", "tipo_parte": "Customer", "parte": cliente, "razao_social": cliente.replace(" Demo", " S.A. (demo)"),
		                "tipo_pessoa": "Jurídica", "cnpj_cpf": cnpj, "observacao": MARCA, **d}).insert(ignore_permissions=True)  # fmt: skip
	# fornecedor para a remessa de padrão (calibração externa)
	nome = "Laboratório Externo de Calibração Demo"
	if not frappe.db.exists("Supplier", nome):
		frappe.get_doc({"doctype": "Supplier", "supplier_name": nome, "supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")}).insert(ignore_permissions=True)
	frappe.get_doc({"doctype": "Dados Fiscais Parte", "tipo_parte": "Supplier", "parte": nome, "razao_social": "Laboratório Externo de Calibração Ltda (demo)",
	                "cnpj_cpf": util.formatar_documento(util.completar_cnpj("618294030001")), "contribuinte_icms": "Contribuinte",
	                "inscricao_estadual": "407.112.334.110", "email_nota": "recebimento@labexterno.demo", "logradouro": "Rua Metrologia", "numero": "45",
	                "bairro": "Jardim Técnico", "cep": "13560-000", "municipio": "São Carlos", "codigo_municipio": "3548906", "uf": "SP", "observacao": MARCA}).insert(ignore_permissions=True)  # fmt: skip


def criar_itens():
	for codigo, nome, preco in SERVICOS:
		frappe.get_doc({"doctype": "Item", "item_code": codigo, "item_name": nome, "item_group": "Services", "stock_uom": "Unit", "is_stock_item": 0,
		                "standard_rate": preco, "description": nome}).insert(ignore_permissions=True)  # fmt: skip
	for codigo, nome, preco, ncm in PRODUTOS:
		if not frappe.db.exists("Customs Tariff Number", ncm):
			frappe.get_doc({"doctype": "Customs Tariff Number", "tariff_number": ncm, "description": nome}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "Item", "item_code": codigo, "item_name": nome, "item_group": "Products", "stock_uom": "Unit", "is_stock_item": 0,
		                "customs_tariff_number": ncm, "standard_rate": preco, "description": nome}).insert(ignore_permissions=True)  # fmt: skip


def fatura(cliente, itens, data=None, vencimento_dias=15):
	data = getdate(data or today())
	precos = {c: p for c, _n, p, *_ in SERVICOS + PRODUTOS}
	si = frappe.get_doc({
		"doctype": "Sales Invoice", "customer": cliente, "company": frappe.db.get_single_value("Configuracao Fiscal", "empresa"),
		"set_posting_time": 1, "posting_date": data, "due_date": add_days(data, vencimento_dias),
		"items": [{"item_code": c, "qty": q, "rate": precos[c]} for c, q in itens],
		"remarks": MARCA,
	})  # fmt: skip
	si.insert(ignore_permissions=True)
	si.submit()
	return si


def faturas_para_emitir():
	fatura("Indústria Alfa Demo", [("SRV-CAL-BAL", 3), ("SRV-CAL-TERM", 5)])
	fatura("Metalúrgica Beta Demo", [("SRV-CAL-MAN", 12), ("SRV-MANUT", 2)])
	fatura("Indústria Alfa Demo", [("PRD-PESO-1KG", 2)])
	fatura("Metalúrgica Beta Demo", [("SRV-CAL-BAL", 2), ("PRD-TERMO", 3)])
	fatura("Laticínios Delta Demo", [("SRV-CAL-PIP", 8), ("SRV-CAL-TERM", 4)])  # sem cadastro fiscal -> pendência
	fatura("Saneamento Gama Demo", [("SRV-CAL-MAN", 6)])  # sem e-mail -> aviso


def historico():
	"""Notas e boletos de setembro/outubro: pagos, em aberto e vencidos — para os números da tela."""
	hoje = getdate(today())
	casos = [
		("Indústria Alfa Demo", [("SRV-CAL-BAL", 4), ("SRV-CAL-PIP", 6)], -40, "pago"),
		("Saneamento Gama Demo", [("SRV-CAL-MAN", 10)], -35, "pago"),
		("Metalúrgica Beta Demo", [("SRV-CAL-TERM", 8), ("SRV-MANUT", 1)], -28, "vencido"),
		("Indústria Alfa Demo", [("PRD-TERMO", 4)], -20, "pago"),
		("Saneamento Gama Demo", [("SRV-CAL-BAL", 3)], -12, "aberto"),
		("Indústria Alfa Demo", [("SRV-CAL-TERM", 10)], -6, "aberto"),
	]
	for cliente, itens, dias, destino in casos:
		data = add_days(hoje, dias)
		si = fatura(cliente, itens, data=data, vencimento_dias=10)
		emissao.emitir_fatura(si.name)
		for n in frappe.get_all("Nota Fiscal", filters={"fatura": si.name}, pluck="name"):
			frappe.db.set_value("Nota Fiscal", n, {"data_emissao": f"{data} 10:30:00", "creation": f"{data} 10:30:00"}, update_modified=False)
		bol = frappe.db.get_value("Boleto Cobranca", {"fatura": si.name}, "name")
		if not bol:
			continue
		frappe.db.set_value("Boleto Cobranca", bol, {"emissao": data, "vencimento": add_days(data, 10)}, update_modified=False)
		if destino == "pago":
			emissao.registrar_pagamento(bol, data=add_days(data, 8), origem="pagamento simulado")
	emissao.atualizar_boletos()  # marca o vencido

	# remessa de um padrão nosso para calibração externa (já passou do prazo) e retorno de equipamento a um cliente
	fornecedor = "Laboratório Externo de Calibração Demo"
	padrao = frappe.db.get_value("Padrao Metrologia", {}, ["name", "descricao", "numero_serie"], as_dict=True) or frappe._dict(name="PADRAO", descricao="Conjunto de massas padrão", numero_serie="")
	r = emissao.emitir_avulsa({"natureza": "Remessa para conserto ou calibração", "tipo_parte": "Supplier", "parte": fornecedor,
	                           "prazo_retorno": str(add_days(hoje, -5)),
	                           "itens": [{"descricao": padrao.descricao, "ncm": "90318099", "quantidade": 1, "valor_unitario": 8500, "numero_serie": padrao.numero_serie, "referencia": padrao.name}]})  # fmt: skip
	nota = r["notas"][0]["id"]
	frappe.db.set_value("Nota Fiscal", nota, {"data_emissao": f"{add_days(hoje, -45)} 09:00:00"}, update_modified=False)

	alfa = frappe.get_doc("Dados Fiscais Parte", {"tipo_parte": "Customer", "parte": "Indústria Alfa Demo"})
	chave_cliente = util.chave_nfe("SP", getdate(add_days(hoje, -15)), alfa.cnpj_cpf, 1, 4521, 31415926)
	emissao.emitir_avulsa({"natureza": "Retorno de conserto ou calibração", "tipo_parte": "Customer", "parte": "Indústria Alfa Demo", "nf_referenciada": chave_cliente,
	                       "itens": [{"descricao": "Balança analítica 220 g", "ncm": "84232000", "quantidade": 1, "valor_unitario": 12000, "numero_serie": "BAL-77821"},
	                                 {"descricao": "Termômetro digital", "ncm": "90251990", "quantidade": 2, "valor_unitario": 380}]})  # fmt: skip
	print("Para testar um retorno, use esta chave de nota do cliente Alfa:", chave_cliente)
