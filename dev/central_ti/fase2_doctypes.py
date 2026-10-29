"""Fase 2 (inventário, manutenções, estoque): acrescenta os DocTypes ao gerar_doctypes.py.

Executado uma vez para editar o gerador; mantido no repositório como registro da mudança.
"""

import os

p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gerar_doctypes.py")
s = open(p).read()


def sub(old, new):
	global s
	assert s.count(old) == 1, old[:70]
	s = s.replace(old, new)


sub('NOW = "2026-10-24 10:00:00.000000"', 'NOW = "2026-10-24 18:00:00.000000"')

# Chamado ganha o equipamento relacionado
sub(
	'			f("categoria", "Link", "Categoria", options="Categoria Chamado TI", in_list_view=1, in_standard_filter=1),\n',
	'			f("categoria", "Link", "Categoria", options="Categoria Chamado TI", in_list_view=1, in_standard_filter=1),\n'
	'			f("equipamento", "Link", "Equipamento", options="Equipamento TI", search_index=1),\n',
)

FASE2 = '''
# ================================================================== FASE 2: inventário
GRUPOS = "Computador\\nImpressora\\nCelular\\nRede e Servidores\\nPeriférico\\nOutro"
STATUS_EQP = "Em Uso\\nEm Estoque\\nEm Manutenção\\nEmprestado\\nDescartado\\nExtraviado"

write(
	doctype(
		"Tipo Equipamento TI",
		[
			f("nome", "Data", "Nome", reqd=1, unique=1, in_list_view=1),
			f("grupo", "Select", "Grupo", options=GRUPOS, reqd=1, default="Computador", in_list_view=1, in_standard_filter=1,
			  description="Define quais campos de configuração aparecem no equipamento"),
			f("icone", "Select", "Ícone", options="laptop\\nmonitor\\nprinter\\nsmartphone\\nserver\\nrouter\\nhard-drive\\nkeyboard\\nmouse\\nbattery-charging\\npackage", default="laptop"),
			cb("cb1"),
			f("vida_util_anos", "Int", "Vida útil (anos)", default="5", in_list_view=1, description="Base do plano de renovação"),
			f("grupo_item_erp", "Link", "Grupo de Item no ERP", options="Item Group",
			  description="Compras (Notas de Compra) de itens deste grupo aparecem em Compras de TI como este tipo"),
			f("controla_estoque", "Check", "Controlado em estoque (por quantidade)",
			  description="Para periféricos e consumíveis (mouse, teclado, cabos): não vira equipamento individual"),
			f("ativo", "Check", "Ativo", default="1"),
		],
		autoname="field:nome",
		naming_rule="By fieldname",
		track_changes=1,
	)
)

write(
	doctype(
		"Historico Responsavel TI",
		[
			f("data", "Datetime", "Data", in_list_view=1, columns=2),
			f("responsavel", "Link", "Responsável", options="User", in_list_view=1, columns=3),
			f("responsavel_nome", "Data", "Nome", in_list_view=1, columns=2),
			f("departamento", "Data", "Departamento", in_list_view=1, columns=2),
			f("registrado_por", "Link", "Registrado por", options="User"),
		],
		istable=1,
	)
)

COMPUTADOR = "eval:doc.grupo=='Computador'"
REDE = "eval:['Rede e Servidores','Impressora'].includes(doc.grupo)"
CELULAR = "eval:doc.grupo=='Celular'"
write(
	doctype(
		"Equipamento TI",
		[
			sb("sec_id", "Identificação"),
			f("nome", "Data", "Nome / Hostname", reqd=1, unique=1, in_list_view=1, in_global_search=1, bold=1,
			  description="Como a TI chama o equipamento (ex.: LAB-NB-07)"),
			f("tipo", "Link", "Tipo", options="Tipo Equipamento TI", reqd=1, in_list_view=1, in_standard_filter=1),
			f("grupo", "Data", "Grupo", fetch_from="tipo.grupo", read_only=1, in_standard_filter=1),
			f("status", "Select", "Status", options=STATUS_EQP, default="Em Estoque", in_list_view=1, in_standard_filter=1),
			cb("cb_id"),
			f("marca", "Data", "Marca"),
			f("modelo", "Data", "Modelo", in_standard_filter=1),
			f("numero_serie", "Data", "Número de Série", in_global_search=1),
			f("patrimonio", "Data", "Patrimônio", in_global_search=1),
			sb("sec_resp", "Com quem está"),
			f("responsavel", "Link", "Responsável", options="User", in_standard_filter=1),
			f("responsavel_nome", "Data", "Nome do responsável", read_only=1, in_list_view=1),
			f("departamento", "Data", "Departamento", in_standard_filter=1),
			cb("cb_resp"),
			f("localizacao", "Data", "Localização"),
			f("termo_responsabilidade", "Attach", "Termo de responsabilidade (assinado)"),
			f("data_termo", "Date", "Data do termo"),
			sb("sec_cfg", "Configuração", depends_on=COMPUTADOR),
			f("processador", "Data", "Processador", depends_on=COMPUTADOR),
			f("memoria_ram", "Data", "Memória RAM", depends_on=COMPUTADOR),
			cb("cb_cfg"),
			f("armazenamento", "Data", "Armazenamento", depends_on=COMPUTADOR),
			f("sistema_operacional", "Data", "Sistema operacional", depends_on=COMPUTADOR),
			sb("sec_rede", "Rede", depends_on=REDE),
			f("endereco_ip", "Data", "Endereço IP", depends_on=REDE),
			f("endereco_mac", "Data", "Endereço MAC", depends_on=REDE),
			cb("cb_rede"),
			f("firmware", "Data", "Firmware / versão", depends_on=REDE),
			sb("sec_cel", "Linha", depends_on=CELULAR),
			f("imei", "Data", "IMEI", depends_on=CELULAR),
			f("numero_linha", "Data", "Número da linha", depends_on=CELULAR),
			cb("cb_cel"),
			f("operadora", "Data", "Operadora", depends_on=CELULAR),
			sb("sec_outras"),
			f("especificacoes", "Small Text", "Outras especificações"),
			sb("sec_compra", "Compra e garantia"),
			f("data_compra", "Date", "Data da compra"),
			f("valor_compra", "Currency", "Valor de compra"),
			f("fornecedor", "Data", "Fornecedor"),
			cb("cb_compra"),
			f("garantia_ate", "Date", "Garantia até", in_standard_filter=1),
			f("nota_compra", "Link", "Nota de Compra (ERP)", options="Purchase Invoice"),
			f("item_nota", "Data", "Linha da nota", read_only=1, hidden=1),
			f("ativo_erp", "Link", "Ativo (ERP)", options="Asset", description="Opcional: o Ativo do ERPNext, se o equipamento for imobilizado"),
			sb("sec_ind", "Custos e indicadores", collapsible=1),
			f("fim_vida_util", "Date", "Fim da vida útil", read_only=1, description="Data da compra + vida útil do tipo"),
			f("custo_manutencoes", "Currency", "Custo das manutenções", read_only=1),
			f("custo_total", "Currency", "Custo total (compra + manutenções)", read_only=1),
			cb("cb_ind"),
			f("qtd_manutencoes", "Int", "Manutenções / upgrades", read_only=1),
			f("qtd_chamados", "Int", "Chamados", read_only=1),
			sb("sec_hist", "Histórico de responsáveis", collapsible=1),
			f("historico_responsaveis", "Table", "Histórico", options="Historico Responsavel TI", read_only=1),
			sb("sec_obs"),
			f("observacoes", "Small Text", "Observações"),
		],
		autoname="field:nome",
		naming_rule="By fieldname",
		title_field="nome",
		search_fields="tipo,modelo,responsavel_nome,departamento",
		track_changes=1,
		links=[
			{"link_doctype": "Manutencao Equipamento TI", "link_fieldname": "equipamento", "group": "Histórico"},
			{"link_doctype": "Chamado TI", "link_fieldname": "equipamento", "group": "Histórico"},
		],
	)
)

write(
	doctype(
		"Manutencao Equipamento TI",
		[
			f("equipamento", "Link", "Equipamento", options="Equipamento TI", reqd=1, in_list_view=1, in_standard_filter=1, search_index=1),
			f("data", "Date", "Data", reqd=1, default="Today", in_list_view=1),
			f("tipo", "Select", "Tipo",
			  options="Upgrade\\nManutenção Corretiva\\nManutenção Preventiva\\nFormatação / Reinstalação\\nTroca de Peça\\nOutro",
			  default="Upgrade", reqd=1, in_list_view=1, in_standard_filter=1),
			f("componente", "Select", "Componente alterado",
			  options="\\nMemória RAM\\nArmazenamento\\nProcessador\\nSistema Operacional\\nOutro",
			  depends_on="eval:['Upgrade','Troca de Peça','Formatação / Reinstalação'].includes(doc.tipo)",
			  description="Memória, armazenamento, processador ou sistema: o cadastro do equipamento é atualizado automaticamente"),
			f("valor_anterior", "Data", "Antes", read_only=1),
			f("valor_novo", "Data", "Depois", depends_on="componente"),
			cb("cb1"),
			f("custo", "Currency", "Custo"),
			f("fornecedor", "Data", "Fornecedor / assistência"),
			f("executado_por", "Link", "Executado por", options="User"),
			f("chamado", "Link", "Chamado relacionado", options="Chamado TI"),
			sb("sec2"),
			f("descricao", "Small Text", "O que foi feito", reqd=1, in_list_view=1),
			f("anexo", "Attach", "Anexo (nota, orçamento, laudo)"),
		],
		autoname="format:MAN-{#####}",
		naming_rule="Expression",
		title_field="equipamento",
		sort_field="data",
		track_changes=1,
	)
)

write(
	doctype(
		"Item Estoque TI",
		[
			f("nome", "Data", "Item", reqd=1, unique=1, in_list_view=1, description="Ex.: Mouse USB Logitech M90"),
			f("tipo", "Link", "Tipo", options="Tipo Equipamento TI", in_list_view=1),
			f("quantidade", "Int", "Quantidade em estoque", read_only=1, default="0", in_list_view=1),
			cb("cb1"),
			f("minimo", "Int", "Estoque mínimo", default="2", in_list_view=1, description="Abaixo disso a Central avisa para comprar"),
			f("localizacao", "Data", "Onde fica"),
			f("ativo", "Check", "Ativo", default="1"),
		],
		autoname="field:nome",
		naming_rule="By fieldname",
		track_changes=1,
		links=[{"link_doctype": "Movimento Estoque TI", "link_fieldname": "item", "group": "Movimentos"}],
	)
)

write(
	doctype(
		"Movimento Estoque TI",
		[
			f("item", "Link", "Item", options="Item Estoque TI", reqd=1, in_list_view=1, in_standard_filter=1),
			f("tipo", "Select", "Movimento", options="Entrada\\nSaída\\nAjuste", reqd=1, default="Saída", in_list_view=1,
			  description="Ajuste: informe a diferença (positiva ou negativa) encontrada na contagem"),
			f("quantidade", "Int", "Quantidade", reqd=1, in_list_view=1),
			f("data", "Datetime", "Data", default="now", in_list_view=1),
			cb("cb1"),
			f("para_usuario", "Link", "Entregue para", options="User"),
			f("chamado", "Link", "Chamado", options="Chamado TI"),
			f("nota_compra", "Link", "Nota de Compra (ERP)", options="Purchase Invoice"),
			f("item_nota", "Data", "Linha da nota", read_only=1, hidden=1),
			f("saldo_apos", "Int", "Saldo após o movimento", read_only=1),
			f("observacao", "Small Text", "Observação"),
		],
		autoname="hash",
		sort_field="data",
	)
)
'''
sub('\nprint("ti_gestao: DocTypes gerados em", os.path.abspath(RAIZ))', FASE2 + '\nprint("ti_gestao: DocTypes gerados em", os.path.abspath(RAIZ))')
open(p, "w").write(s)
print("gerador atualizado com a fase 2")
