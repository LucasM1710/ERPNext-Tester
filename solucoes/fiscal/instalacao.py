"""Configuração do módulo Fiscal (app solucoes).

Chamado por solucoes.setup.after_migrate — ou seja, por `bench --site <site> execute solucoes.setup.instalar`.
Idempotente: grava defaults ausentes da Configuracao Fiscal e cria as naturezas de operação padrão que faltarem
(as já existentes não são alteradas: o contador pode ajustá-las à vontade).
"""

import frappe

CONFIG = "Configuracao Fiscal"

# CFOPs e CSOSN/CST usuais — CONFIRME COM O CONTADOR antes da produção.
NATUREZAS_PADRAO = [
	{
		"nome": "Prestação de serviço", "documento": "NFS-e", "tipo": "Serviço", "gera_boleto": 1,
		"explicacao": "Calibração, manutenção, consultoria: tudo que é serviço sai em NFS-e.",
	},
	{
		"nome": "Venda de mercadoria", "documento": "NF-e", "tipo": "Venda", "gera_boleto": 1, "icms_tributado": 1,
		"cfop_dentro_estado": "5102", "cfop_fora_estado": "6102", "csosn": "102", "cst_icms": "00",
		"explicacao": "Venda de peças, acessórios ou equipamentos comprados para revenda.",
	},
	{
		"nome": "Retorno de conserto ou calibração", "documento": "NF-e", "tipo": "Retorno", "exige_nf_referenciada": 1,
		"cfop_dentro_estado": "5916", "cfop_fora_estado": "6916", "csosn": "400", "cst_icms": "50",
		"texto_complementar": "Retorno de mercadoria recebida para conserto/calibração através da NF-e chave {nf_referenciada}. ICMS suspenso.",
		"explicacao": "Devolver ao cliente o equipamento que ele mandou para calibrar ou consertar. Precisa da chave da nota com que o equipamento chegou.",
	},
	{
		"nome": "Remessa para conserto ou calibração", "documento": "NF-e", "tipo": "Remessa", "controla_retorno": 1,
		"cfop_dentro_estado": "5915", "cfop_fora_estado": "6915", "csosn": "400", "cst_icms": "50",
		"texto_complementar": "Remessa para conserto/calibração com retorno previsto até {prazo}. ICMS suspenso.",
		"explicacao": "Enviar um equipamento ou padrão nosso para calibrar ou consertar fora (outro laboratório ou fabricante).",
	},
	{
		"nome": "Remessa para demonstração", "documento": "NF-e", "tipo": "Remessa", "controla_retorno": 1,
		"cfop_dentro_estado": "5912", "cfop_fora_estado": "6912", "csosn": "400", "cst_icms": "50",
		"texto_complementar": "Remessa para demonstração com retorno previsto até {prazo}.",
		"explicacao": "Emprestar um equipamento para o cliente testar, com retorno.",
	},
	{
		"nome": "Retorno de demonstração", "documento": "NF-e", "tipo": "Retorno", "exige_nf_referenciada": 1,
		"cfop_dentro_estado": "5913", "cfop_fora_estado": "6913", "csosn": "400", "cst_icms": "50",
		"texto_complementar": "Retorno de mercadoria recebida para demonstração através da NF-e chave {nf_referenciada}.",
		"explicacao": "Devolver um equipamento que recebemos para demonstração.",
	},
	{
		"nome": "Remessa em comodato", "documento": "NF-e", "tipo": "Remessa", "controla_retorno": 1,
		"cfop_dentro_estado": "5908", "cfop_fora_estado": "6908", "csosn": "400", "cst_icms": "50",
		"texto_complementar": "Remessa em comodato. Retorno previsto até {prazo}.",
		"explicacao": "Emprestar um equipamento por contrato (comodato).",
	},
]  # fmt: skip


def configurar():
	preencher_padroes_configuracao()
	garantir_naturezas()


def preencher_padroes_configuracao():
	"""Grava o default de campos ainda sem valor (um Single só usa os defaults enquanto não tem nada salvo)."""
	singles = frappe.qb.DocType("Singles")
	salvos = set(frappe.qb.from_(singles).select(singles.field).where(singles.doctype == CONFIG).run(pluck=True))
	for campo in frappe.get_meta(CONFIG).fields:
		if campo.default is not None and campo.fieldname not in salvos:
			frappe.db.set_single_value(CONFIG, campo.fieldname, campo.default)
	if "empresa" not in salvos:
		empresa = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
		if empresa:
			frappe.db.set_single_value(CONFIG, "empresa", empresa)


def garantir_naturezas():
	for dados in NATUREZAS_PADRAO:
		if not frappe.db.exists("Natureza Operacao Fiscal", dados["nome"]):
			frappe.get_doc({"doctype": "Natureza Operacao Fiscal", "ativo": 1, **dados}).insert(ignore_permissions=True)
