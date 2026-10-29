"""Fase 2b: modo TV (link secreto) e orçamento anual de TI na configuração.

Executado uma vez para editar o gerador; mantido como registro da mudança.
"""

import os

p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gerar_doctypes.py")
s = open(p).read()


def sub(old, new):
	global s
	assert s.count(old) == 1, old[:70]
	s = s.replace(old, new)


sub('NOW = "2026-10-24 18:00:00.000000"', 'NOW = "2026-10-25 09:00:00.000000"')

sub(
	'			f("dias_fechamento_automatico", "Int", "Fechar resolvidos após (dias úteis sem resposta)", default="3"),\n',
	'''			f("dias_fechamento_automatico", "Int", "Fechar resolvidos após (dias úteis sem resposta)", default="3"),
			sb("sec_tv", "Painel na TV", description="Tela de indicadores para a TV da TI, aberta por um link secreto (sem login). Gere o link em Indicadores > Modo TV."),
			f("tv_ativo", "Check", "Painel da TV ativo", default="1"),
			f("tv_chave", "Data", "Chave do link da TV", read_only=1, description="Gerar um novo link invalida o anterior"),
			cb("cb_tv"),
			f("tv_mostrar_nomes", "Check", "Mostrar nomes dos colaboradores na TV", default="0",
			  description="Desmarcado: a TV mostra assunto e departamento, sem o nome de quem abriu (recomendado se a TV fica em área comum)"),
			f("tv_segundos_slide", "Int", "Segundos por slide", default="20"),
			sb("sec_orc", "Orçamento de TI", description="Valores planejados por ano; a Visão do gestor compara com o realizado (compras do ERP e manutenções)."),
			f("orcamentos", "Table", "Orçamento anual", options="Orcamento Anual TI"),
			f("numero_colaboradores", "Int", "Número de colaboradores", description="Para o custo de TI por colaborador. Vazio = funcionários ativos do ERPNext"),
''',
)

sub(
	'''write(
	doctype(
		"Configuracao Central TI",''',
	'''write(
	doctype(
		"Orcamento Anual TI",
		[
			f("ano", "Int", "Ano", reqd=1, in_list_view=1, columns=2),
			f("compras", "Currency", "Compras de equipamentos", in_list_view=1, columns=3),
			f("manutencoes", "Currency", "Manutenções", in_list_view=1, columns=3),
			f("observacao", "Data", "Observação", in_list_view=1, columns=2),
		],
		istable=1,
		editable_grid=1,
	)
)
write(
	doctype(
		"Configuracao Central TI",''',
)
open(p, "w").write(s)
print("gerador atualizado: TV e orçamento")
