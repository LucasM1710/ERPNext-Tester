"""Gera os JSONs dos DocTypes do módulo Fiscal (app solucoes).

	python3 dev/fiscal/gerar_doctypes.py   (na raiz do app solucoes)

Os JSONs gerados são a fonte de verdade; ao mudar um campo aqui, rode o script,
suba o `modified` (NOW) e depois `bench --site <site> execute solucoes.setup.instalar`.
Compatível com Frappe 15 e 16 (só tipos de campo e propriedades comuns às duas versões).
"""

import json
import os

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "solucoes", "fiscal")
MODULO = "Fiscal"
NOW = "2026-11-01 09:00:00.000000"

PAPEIS = ("System Manager", "Accounts Manager", "Accounts User")


def f(fieldname, fieldtype, label=None, **kw):
	d = {"fieldname": fieldname, "fieldtype": fieldtype}
	if label:
		d["label"] = label
	d.update(kw)
	return d


def sb(n, label=None, **kw):
	return f(n, "Section Break", label, **kw)


def cb(n):
	return f(n, "Column Break")


def perms(*papeis):
	return [
		{"create": 1, "delete": 1, "email": 1, "export": 1, "print": 1, "read": 1, "report": 1, "role": p, "share": 1, "write": 1}
		for p in papeis
	]


def doctype(name, fields, **kw):
	d = {
		"actions": [],
		"creation": NOW,
		"doctype": "DocType",
		"engine": "InnoDB",
		"field_order": [x["fieldname"] for x in fields],
		"fields": fields,
		"links": [],
		"modified": NOW,
		"modified_by": "Administrator",
		"module": MODULO,
		"name": name,
		"owner": "Administrator",
		"permissions": [] if kw.get("istable") else perms(*PAPEIS),
		"sort_field": "creation",
		"sort_order": "DESC",
		"states": [],
	}
	d.update(kw)
	return d


def scrub(name):
	return name.lower().replace(" ", "_")


def write(d):
	pasta = os.path.join(RAIZ, "doctype", scrub(d["name"]))
	os.makedirs(pasta, exist_ok=True)
	open(os.path.join(pasta, "__init__.py"), "a").close()
	with open(os.path.join(pasta, scrub(d["name"]) + ".json"), "w") as fp:
		fp.write(json.dumps(d, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
	controlador = os.path.join(pasta, scrub(d["name"]) + ".py")
	if not os.path.exists(controlador):
		classe = d["name"].replace(" ", "").replace("-", "")  # regra do Frappe
		with open(controlador, "w") as fp:
			fp.write(f"from frappe.model.document import Document\n\n\nclass {classe}(Document):\n\tpass\n")


ENDERECO = [
	f("logradouro", "Data", "Logradouro"),
	f("numero", "Data", "Número"),
	f("complemento", "Data", "Complemento"),
	f("bairro", "Data", "Bairro"),
	f("cep", "Data", "CEP"),
	f("municipio", "Data", "Município"),
	f("codigo_municipio", "Data", "Código IBGE do Município", description="7 dígitos (ex.: 3509502 = Campinas/SP)"),
	f("uf", "Data", "UF", length=2),
]

# ------------------------------------------------------------------ Evento (filha comum: nota e boleto)
write(
	doctype(
		"Evento Fiscal",
		[
			f("data", "Datetime", "Data", in_list_view=1, columns=2),
			f("evento", "Data", "Evento", in_list_view=1, columns=3),
			f("detalhe", "Small Text", "Detalhe", in_list_view=1, columns=4),
			f("usuario", "Link", "Usuário", options="User", columns=1),
		],
		istable=1,
		editable_grid=0,
	)
)

# ------------------------------------------------------------------ Configuração (single)
write(
	doctype(
		"Configuracao Fiscal",
		[
			sb("sec_ambiente", "Ambiente"),
			f("ambiente", "Select", "Ambiente", options="Simulação\nHomologação\nProdução", default="Simulação",
			  description="Simulação: tudo acontece só aqui, sem valor fiscal. Homologação: testes no provedor/SEFAZ (sem valor fiscal). Produção: notas e boletos reais."),
			f("provedor_notas", "Select", "Provedor de Notas", options="Simulador\nFocus NFe\nPlugNotas\nNuvem Fiscal\nNFE.io", default="Simulador"),
			f("provedor_token", "Password", "Token do Provedor de Notas"),
			f("provedor_boleto", "Select", "Provedor de Boletos", options="Simulador\nAPI do Banco\nAsaas\nEfí", default="Simulador"),
			f("boleto_credencial", "Password", "Credencial do Provedor de Boletos"),
			cb("cb_amb"),
			f("certificado_a1", "Attach", "Certificado Digital A1 (.pfx)", description="Exigido para homologação e produção. Não é usado na simulação."),
			f("certificado_senha", "Password", "Senha do Certificado"),
			f("certificado_validade", "Date", "Validade do Certificado"),
			f("simulacao_falha_percentual", "Int", "Simulação: % de Rejeições Aleatórias", default="0",
			  description="Para treinar a equipe: parte das emissões simuladas volta rejeitada (ex.: 10)."),
			sb("sec_emitente", "Emitente (sua empresa)"),
			f("empresa", "Link", "Empresa", options="Company"),
			f("razao_social", "Data", "Razão Social"),
			f("nome_fantasia", "Data", "Nome Fantasia"),
			f("cnpj", "Data", "CNPJ"),
			f("inscricao_estadual", "Data", "Inscrição Estadual"),
			f("inscricao_municipal", "Data", "Inscrição Municipal"),
			f("regime_tributario", "Select", "Regime Tributário", options="Simples Nacional\nLucro Presumido\nLucro Real", default="Simples Nacional"),
			f("cnae", "Data", "CNAE Principal"),
			f("telefone", "Data", "Telefone"),
			f("email", "Data", "E-mail", options="Email"),
			cb("cb_emit"),
			*ENDERECO,
			sb("sec_nfse", "NFS-e (serviços)"),
			f("codigo_servico_nacional", "Data", "Código de Tributação Nacional (cTribNac)", description="6 dígitos do serviço na NFS-e Nacional. Confirme com o contador."),
			f("item_lista_servico", "Data", "Item da Lista de Serviços (LC 116)"),
			f("codigo_nbs", "Data", "Código NBS"),
			f("aliquota_iss", "Percent", "Alíquota de ISS", default="2"),
			f("descricao_padrao_servico", "Small Text", "Discriminação Padrão do Serviço",
			  default="Serviços de calibração e manutenção de equipamentos conforme fatura {fatura}."),
			cb("cb_nfse"),
			f("serie_dps", "Data", "Série da DPS", default="1"),
			f("proximo_numero_dps", "Int", "Próximo Número da NFS-e", default="1"),
			f("aliquota_pis", "Percent", "Retenção de PIS", default="0.65"),
			f("aliquota_cofins", "Percent", "Retenção de COFINS", default="3"),
			f("aliquota_csll", "Percent", "Retenção de CSLL", default="1"),
			f("aliquota_ir", "Percent", "Retenção de IR", default="1.5"),
			sb("sec_nfe", "NF-e (produtos, remessa e retorno)"),
			f("serie_nfe", "Int", "Série da NF-e", default="1"),
			f("proximo_numero_nfe", "Int", "Próximo Número da NF-e", default="1"),
			f("aliquota_icms_interna", "Percent", "ICMS Interno", default="18"),
			f("aliquota_icms_interestadual", "Percent", "ICMS Interestadual", default="12"),
			cb("cb_nfe"),
			f("informacoes_complementares", "Small Text", "Informações Complementares (todas as NF-e)",
			  default="Documento emitido por ME ou EPP optante pelo Simples Nacional. Não gera direito a crédito fiscal de IPI."),
			f("prazo_retorno_remessa_dias", "Int", "Prazo de Retorno das Remessas (dias)", default="180",
			  description="Usado para avisar quando um equipamento enviado está demorando a voltar. Confira o prazo do seu estado com o contador."),
			sb("sec_reforma", "Reforma tributária (2026)"),
			f("destacar_ibs_cbs", "Check", "Destacar IBS/CBS (informativo)", default="1"),
			f("aliquota_cbs", "Percent", "Alíquota CBS (teste 2026)", default="0.9"),
			f("aliquota_ibs", "Percent", "Alíquota IBS (teste 2026)", default="0.1"),
			sb("sec_boleto", "Boleto e Pix"),
			f("banco_nome", "Data", "Banco", default="Banco Simulado"),
			f("banco_codigo", "Data", "Código do Banco", default="000"),
			f("agencia", "Data", "Agência", default="0001"),
			f("conta", "Data", "Conta", default="1234567"),
			f("carteira", "Data", "Carteira", default="09"),
			f("chave_pix", "Data", "Chave Pix"),
			f("proximo_nosso_numero", "Int", "Próximo Nosso Número", default="1"),
			cb("cb_bol"),
			f("dias_vencimento", "Int", "Dias para Vencimento", default="10", description="Usado quando a fatura não tem data de vencimento futura"),
			f("multa_percentual", "Percent", "Multa por Atraso", default="2"),
			f("juros_mes_percentual", "Percent", "Juros ao Mês", default="1"),
			f("instrucoes_boleto", "Small Text", "Instruções do Boleto", default="Após o vencimento, cobrar multa e juros. Não receber após 60 dias do vencimento."),
			f("conta_recebimento", "Link", "Conta de Recebimento (Banco)", options="Account", description="Onde o ERP lança o valor recebido do boleto"),
			f("conta_retencoes", "Link", "Conta de Impostos Retidos pelo Cliente", options="Account",
			  description="Recebe a diferença entre a fatura e o boleto quando o cliente retém ISS ou impostos federais"),
			sb("sec_auto", "Automação"),
			f("data_inicio", "Date", "Considerar Faturas a Partir de", description="Faturas anteriores não aparecem em Para emitir"),
			f("emitir_ao_confirmar_fatura", "Check", "Emitir Sozinho ao Confirmar a Fatura", default="0",
			  description="Se a conferência estiver toda verde, a nota e o boleto saem no momento em que a fatura é confirmada."),
			f("enviar_email_cliente", "Check", "Enviar Nota e Boleto por E-mail", default="1",
			  description="Na simulação o e-mail não sai: só fica registrado no histórico."),
			cb("cb_auto"),
			f("lembrete_dias_antes", "Int", "Lembrete ao Cliente (dias antes do vencimento)", default="3"),
			f("cobranca_dias_depois", "Int", "Cobrança (dias depois do vencimento)", default="1"),
		],
		issingle=1,
		track_changes=1,
	)
)

# ------------------------------------------------------------------ Natureza da operação
write(
	doctype(
		"Natureza Operacao Fiscal",
		[
			f("nome", "Data", "Nome", reqd=1, unique=1, in_list_view=1),
			f("documento", "Select", "Documento", options="NF-e\nNFS-e", reqd=1, in_list_view=1),
			f("tipo", "Select", "Tipo", options="Venda\nServiço\nRemessa\nRetorno", reqd=1, in_list_view=1),
			f("explicacao", "Small Text", "Explicação (em linguagem simples)", description="Aparece para quem emite, para escolher a opção certa"),
			cb("cb1"),
			f("cfop_dentro_estado", "Data", "CFOP Dentro do Estado"),
			f("cfop_fora_estado", "Data", "CFOP Fora do Estado"),
			f("csosn", "Data", "CSOSN (Simples Nacional)"),
			f("cst_icms", "Data", "CST do ICMS (Regime Normal)"),
			f("icms_tributado", "Check", "Destaca ICMS"),
			f("gera_boleto", "Check", "Gera Boleto"),
			f("exige_nf_referenciada", "Check", "Exige a Nota de Origem", description="Retorno: informar a chave da nota com que o equipamento chegou"),
			f("controla_retorno", "Check", "Acompanhar Retorno", description="Remessa: fica em Remessas em aberto até voltar"),
			f("texto_complementar", "Small Text", "Texto Complementar", description="Use {nf_referenciada} e {prazo}"),
			f("ativo", "Check", "Ativo", default="1", in_list_view=1),
		],
		autoname="field:nome",
		naming_rule="By fieldname",
		track_changes=1,
	)
)

# ------------------------------------------------------------------ Dados fiscais de cliente / fornecedor
write(
	doctype(
		"Dados Fiscais Parte",
		[
			f("tipo_parte", "Select", "Tipo", options="Customer\nSupplier", default="Customer", reqd=1, in_list_view=1),
			f("parte", "Dynamic Link", "Cliente / Fornecedor", options="tipo_parte", reqd=1, in_list_view=1, in_standard_filter=1),
			f("razao_social", "Data", "Razão Social / Nome", in_list_view=1),
			f("tipo_pessoa", "Select", "Pessoa", options="Jurídica\nFísica", default="Jurídica"),
			f("cnpj_cpf", "Data", "CNPJ / CPF", in_list_view=1),
			f("contribuinte_icms", "Select", "Contribuinte de ICMS", options="Não contribuinte\nContribuinte\nIsento", default="Não contribuinte"),
			f("inscricao_estadual", "Data", "Inscrição Estadual"),
			f("inscricao_municipal", "Data", "Inscrição Municipal"),
			f("email_nota", "Data", "E-mail para Notas e Boletos", options="Email"),
			cb("cb1"),
			*ENDERECO,
			sb("sec_ret", "Retenções feitas pelo cliente"),
			f("iss_retido", "Check", "Cliente Retém o ISS", description="O próprio cliente recolhe o ISS; o boleto sai pelo valor líquido"),
			f("retem_impostos_federais", "Check", "Cliente Retém PIS/COFINS/CSLL/IR", description="Comum em empresas grandes e órgãos públicos"),
			cb("cb2"),
			f("observacao", "Small Text", "Observação"),
		],
		autoname="hash",
		title_field="razao_social",
		show_title_field_in_link=0,
		search_fields="cnpj_cpf,razao_social",
		track_changes=1,
	)
)

# ------------------------------------------------------------------ Nota fiscal
write(
	doctype(
		"Item Nota Fiscal",
		[
			f("item_code", "Link", "Item", options="Item", columns=2),
			f("descricao", "Small Text", "Descrição", in_list_view=1, columns=3, reqd=1),
			f("ncm", "Data", "NCM", in_list_view=1, columns=1),
			f("cfop", "Data", "CFOP", columns=1),
			f("unidade", "Data", "Unidade", default="UN"),
			f("quantidade", "Float", "Quantidade", in_list_view=1, columns=1, default="1"),
			f("valor_unitario", "Currency", "Valor Unitário", in_list_view=1, columns=1),
			f("valor_total", "Currency", "Valor Total", in_list_view=1, columns=1),
			f("numero_serie", "Data", "Número de Série"),
			f("referencia", "Data", "Referência", description="Equipamento, padrão ou linha da fatura de origem"),
		],
		istable=1,
		editable_grid=1,
	)
)
write(
	doctype(
		"Nota Fiscal",
		[
			f("tipo_documento", "Select", "Documento", options="NFS-e\nNF-e", reqd=1, in_list_view=1, in_standard_filter=1),
			f("natureza", "Link", "Natureza da Operação", options="Natureza Operacao Fiscal", reqd=1),
			f("status", "Select", "Situação", options="Rascunho\nProcessando\nAutorizada\nRejeitada\nSubstituída\nCancelada", default="Rascunho",
			  in_list_view=1, in_standard_filter=1),
			f("ambiente", "Data", "Ambiente", read_only=1),
			f("fatura", "Link", "Fatura", options="Sales Invoice", in_standard_filter=1),
			cb("cb1"),
			f("tipo_parte", "Select", "Tipo do Destinatário", options="Customer\nSupplier", default="Customer"),
			f("parte", "Dynamic Link", "Destinatário", options="tipo_parte", in_standard_filter=1),
			f("nome_parte", "Data", "Nome do Destinatário", in_list_view=1),
			f("documento_parte", "Data", "CNPJ/CPF do Destinatário"),
			f("uf_destino", "Data", "UF do Destinatário"),
			cb("cb2"),
			f("numero", "Data", "Número", in_list_view=1),
			f("serie", "Data", "Série"),
			f("chave_acesso", "Data", "Chave de Acesso"),
			f("protocolo", "Data", "Protocolo"),
			f("data_emissao", "Datetime", "Emitida em"),
			sb("sec_ref", "Remessa e retorno", collapsible=1),
			f("nf_referenciada", "Data", "Chave da Nota de Origem", description="Retorno: nota com que o equipamento chegou"),
			f("nota_remessa", "Link", "Remessa de Origem", options="Nota Fiscal"),
			cb("cb_ref"),
			f("situacao_remessa", "Select", "Situação da Remessa", options="\nEm aberto\nRetornada"),
			f("prazo_retorno", "Date", "Retorno Previsto até"),
			f("retorno_chave", "Data", "Chave da Nota de Retorno"),
			f("retorno_data", "Date", "Retornou em"),
			sb("sec_itens", "Itens"),
			f("itens", "Table", "Itens", options="Item Nota Fiscal"),
			f("discriminacao", "Small Text", "Discriminação do Serviço"),
			f("informacoes_complementares", "Small Text", "Informações Complementares"),
			sb("sec_valores", "Valores"),
			f("cfop", "Data", "CFOP"),
			f("valor_total", "Currency", "Valor Total", in_list_view=1),
			f("base_icms", "Currency", "Base do ICMS"),
			f("aliquota_icms", "Percent", "Alíquota do ICMS"),
			f("valor_icms", "Currency", "ICMS"),
			f("aliquota_iss", "Percent", "Alíquota do ISS"),
			f("valor_iss", "Currency", "ISS"),
			f("iss_retido", "Check", "ISS Retido pelo Cliente"),
			cb("cb_val"),
			f("valor_pis_retido", "Currency", "PIS Retido"),
			f("valor_cofins_retido", "Currency", "COFINS Retido"),
			f("valor_csll_retido", "Currency", "CSLL Retido"),
			f("valor_ir_retido", "Currency", "IR Retido"),
			f("valor_retencoes", "Currency", "Total Retido pelo Cliente"),
			f("valor_liquido", "Currency", "Valor Líquido a Receber"),
			f("valor_cbs", "Currency", "CBS (informativo)"),
			f("valor_ibs", "Currency", "IBS (informativo)"),
			sb("sec_ret", "Retorno do provedor"),
			f("codigo_retorno", "Data", "Código"),
			f("mensagem_retorno", "Small Text", "Mensagem"),
			f("orientacao", "Small Text", "Como Resolver"),
			cb("cb_ret"),
			f("motivo_cancelamento", "Small Text", "Motivo do Cancelamento"),
			f("cancelada_em", "Datetime", "Cancelada em"),
			f("boleto", "Link", "Boleto", options="Boleto Cobranca"),
			f("email_enviado_em", "Datetime", "E-mail Enviado em"),
			f("xml", "Attach", "XML"),
			f("destinatario_json", "Long Text", "Dados do Destinatário na Emissão", hidden=1),
			sb("sec_hist", "Histórico"),
			f("eventos", "Table", "Eventos", options="Evento Fiscal"),
		],
		autoname="NF-.YYYY.-.#####",
		naming_rule="Expression (old style)",
		title_field="nome_parte",
		search_fields="numero,nome_parte,fatura",
		track_changes=1,
	)
)

# ------------------------------------------------------------------ Boleto
write(
	doctype(
		"Boleto Cobranca",
		[
			f("status", "Select", "Situação", options="Em aberto\nPago\nVencido\nCancelado", default="Em aberto", in_list_view=1, in_standard_filter=1),
			f("cliente", "Link", "Cliente", options="Customer", reqd=1, in_standard_filter=1),
			f("nome_cliente", "Data", "Nome do Cliente", in_list_view=1),
			f("documento_cliente", "Data", "CNPJ/CPF"),
			f("email_cliente", "Data", "E-mail", options="Email"),
			f("fatura", "Link", "Fatura", options="Sales Invoice", in_standard_filter=1),
			f("nota_fiscal", "Link", "Nota Fiscal", options="Nota Fiscal"),
			f("ambiente", "Data", "Ambiente", read_only=1),
			cb("cb1"),
			f("valor", "Currency", "Valor", in_list_view=1, reqd=1),
			f("parcela", "Data", "Parcela", in_list_view=1, description="Ex.: 2/3 quando a fatura é parcelada"),
			f("payment_term", "Data", "Condição de Pagamento da Parcela"),
			f("valor_retencao", "Currency", "Retenção Abatida nesta Parcela", description="Parte dos impostos retidos pelo cliente que este boleto já desconta"),
			f("emissao", "Date", "Emitido em"),
			f("vencimento", "Date", "Vencimento", in_list_view=1, reqd=1),
			f("multa_percentual", "Percent", "Multa"),
			f("juros_mes_percentual", "Percent", "Juros ao Mês"),
			f("instrucoes", "Small Text", "Instruções"),
			sb("sec_cod", "Códigos"),
			f("banco", "Data", "Banco"),
			f("nosso_numero", "Data", "Nosso Número"),
			f("linha_digitavel", "Data", "Linha Digitável"),
			f("codigo_barras", "Data", "Código de Barras"),
			f("pix_copia_cola", "Small Text", "Pix Copia e Cola"),
			sb("sec_pag", "Pagamento"),
			f("pago_em", "Date", "Pago em"),
			f("valor_pago", "Currency", "Valor Pago"),
			f("pagamento", "Link", "Lançamento no ERP", options="Payment Entry"),
			cb("cb_pag"),
			f("motivo_cancelamento", "Small Text", "Motivo do Cancelamento"),
			f("ultimo_lembrete", "Date", "Último Lembrete"),
			sb("sec_hist", "Histórico"),
			f("eventos", "Table", "Eventos", options="Evento Fiscal"),
		],
		autoname="BOL-.YYYY.-.#####",
		naming_rule="Expression (old style)",
		title_field="nome_cliente",
		search_fields="nome_cliente,fatura,nosso_numero",
		track_changes=1,
	)
)
print("DocTypes do módulo Fiscal gerados em", os.path.normpath(RAIZ))
