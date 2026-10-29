"""Gera os JSONs dos DocTypes do módulo Central TI (app solucoes).

	python3 dev/central_ti/gerar_doctypes.py   (na raiz do app solucoes)

Os JSONs gerados são a fonte de verdade; ao mudar um campo aqui, rode o script,
suba o `modified` (NOW) e depois `bench --site <site> execute solucoes.setup.instalar`.
Compatível com Frappe 15 e 16 (só tipos de campo e propriedades comuns às duas versões).
"""

import json
import os

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "solucoes", "central_ti")
MODULO = "Central TI"
NOW = "2026-10-25 09:00:00.000000"

PAPEIS_TI = ("System Manager", "Tecnico TI")


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
		"permissions": [] if kw.get("istable") else perms(*PAPEIS_TI),
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


PRIORIDADES = "Baixa\nMédia\nAlta\nCrítica"
STATUS = "Aberto\nEm Atendimento\nAguardando Usuário\nResolvido\nFechado\nCancelado"
SLA = "\nNo Prazo\nEm Risco\nViolado\nCumprido"

# ------------------------------------------------------------------ Categoria
write(
	doctype(
		"Categoria Chamado TI",
		[
			f("nome", "Data", "Nome", reqd=1, unique=1, in_list_view=1),
			f("descricao", "Small Text", "Descrição", description="Aparece para o colaborador ao escolher a categoria"),
			f("icone", "Select", "Ícone",
			  options="key-round\nlaptop\nprinter\nmail\nwifi\nlayout-grid\npackage\nsmartphone\nflask-conical\nshield\nlife-buoy",
			  default="life-buoy"),
			cb("cb1"),
			f("tecnico_padrao", "Link", "Técnico Padrão", options="User", description="Recebe os chamados desta categoria; vazio = distribuição automática"),
			f("ordem", "Int", "Ordem", default="10"),
			f("ativo", "Check", "Ativo", default="1", in_list_view=1),
		],
		autoname="field:nome",
		naming_rule="By fieldname",
		track_changes=1,
	)
)

# ------------------------------------------------------------------ Configuração (single + filhas)
write(
	doctype(
		"Prazo SLA TI",
		[
			f("prioridade", "Select", "Prioridade", options=PRIORIDADES, reqd=1, in_list_view=1, columns=3),
			f("primeira_resposta_horas", "Float", "1ª Resposta (horas úteis)", reqd=1, in_list_view=1, columns=3),
			f("resolucao_horas", "Float", "Resolução (horas úteis)", reqd=1, in_list_view=1, columns=3),
		],
		istable=1,
		editable_grid=1,
	)
)
write(
	doctype(
		"Tecnico TI",
		[
			f("usuario", "Link", "Usuário", options="User", reqd=1, in_list_view=1, columns=4),
			f("ativo", "Check", "Ativo", default="1", in_list_view=1, columns=2),
			f("recebe_automatico", "Check", "Recebe Distribuição Automática", default="1", in_list_view=1, columns=3),
		],
		istable=1,
		editable_grid=1,
	)
)
write(
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
		"Configuracao Central TI",
		[
			sb("sec_geral", "Geral"),
			f("titulo", "Data", "Título", default="Central de TI"),
			f("email_ti", "Data", "E-mail da TI", options="Email", description="Endereço que recebe chamados por e-mail (ex.: ti@empresa.com.br). Configure a Email Account com 'Append To' = Chamado TI."),
			cb("cb_geral"),
			f("notificar_por_email", "Check", "Notificar por e-mail", default="1"),
			f("enviar_pesquisa_satisfacao", "Check", "Pedir avaliação ao resolver", default="1"),
			sb("sec_expediente", "Expediente (para contar o SLA em horas úteis)"),
			f("horario_inicio", "Time", "Início", default="08:00:00"),
			f("horario_fim", "Time", "Fim", default="18:00:00"),
			cb("cb_exp"),
			f("trabalha_sabado", "Check", "Atende aos sábados"),
			f("lista_feriados", "Link", "Lista de Feriados", options="Holiday List", description="Opcional: feriados não contam no SLA"),
			sb("sec_sla", "Prazos por Prioridade (SLA)"),
			f("prazos", "Table", "Prazos", options="Prazo SLA TI"),
			f("alerta_sla_percentual", "Int", "Alertar quando consumir (%) do prazo", default="80"),
			sb("sec_equipe", "Equipe de TI"),
			f("tecnicos", "Table", "Técnicos", options="Tecnico TI"),
			sb("sec_auto", "Automações"),
			f("dias_fechamento_automatico", "Int", "Fechar resolvidos após (dias úteis sem resposta)", default="3"),
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
		],
		issingle=1,
		permissions=[{"create": 1, "delete": 1, "email": 1, "print": 1, "read": 1, "role": p, "share": 1, "write": 1} for p in PAPEIS_TI],
	)
)

# ------------------------------------------------------------------ Chamado
write(
	doctype(
		"Chamado TI",
		[
			sb("sec_principal"),
			f("assunto", "Data", "Assunto", reqd=1, in_list_view=1, in_global_search=1, bold=1),
			f("categoria", "Link", "Categoria", options="Categoria Chamado TI", in_list_view=1, in_standard_filter=1),
			f("equipamento", "Link", "Equipamento", options="Equipamento TI", search_index=1),
			f("prioridade", "Select", "Prioridade", options=PRIORIDADES, default="Média", in_list_view=1, in_standard_filter=1),
			f("impacto", "Select", "Impacto (informado pelo colaborador)",
			  options="\nConsigo trabalhar normalmente\nAtrapalha, mas consigo trabalhar\nNão consigo trabalhar\nAfeta várias pessoas ou a empresa"),
			cb("cb_principal"),
			f("status", "Select", "Status", options=STATUS, default="Aberto", reqd=1, in_list_view=1, in_standard_filter=1, bold=1),
			f("responsavel", "Link", "Técnico Responsável", options="User", in_list_view=1, in_standard_filter=1),
			f("canal", "Select", "Canal", options="Portal\nE-mail\nTelefone\nPresencial", default="Portal"),
			sb("sec_solicitante", "Solicitante"),
			f("solicitante", "Link", "Usuário", options="User", search_index=1),
			f("email_solicitante", "Data", "E-mail", options="Email", search_index=1),
			cb("cb_sol"),
			f("nome_solicitante", "Data", "Nome"),
			f("departamento", "Data", "Departamento"),
			sb("sec_descricao", "Descrição"),
			f("descricao", "Text Editor", "Descrição do problema"),
			sb("sec_sla", "Prazos (SLA)", collapsible=1),
			f("aberto_em", "Datetime", "Aberto em", read_only=1),
			f("prazo_resposta", "Datetime", "Prazo da 1ª resposta", read_only=1),
			f("primeira_resposta_em", "Datetime", "1ª resposta em", read_only=1),
			f("sla_resposta", "Select", "SLA da resposta", options=SLA, read_only=1, in_standard_filter=1),
			cb("cb_sla"),
			f("prazo_resolucao", "Datetime", "Prazo de resolução", read_only=1),
			f("resolvido_em", "Datetime", "Resolvido em", read_only=1),
			f("sla_resolucao", "Select", "SLA da resolução", options=SLA, read_only=1, in_standard_filter=1),
			f("pausado_em", "Datetime", "Pausado em (aguardando usuário)", read_only=1, hidden=1),
			f("horas_pausadas", "Float", "Horas úteis pausadas (aguardando usuário)", read_only=1, precision="2", default="0"),
			f("alerta_enviado", "Check", "Alerta de SLA enviado", read_only=1, hidden=1),
			cb("cb_sla2"),
			f("horas_primeira_resposta", "Float", "Horas úteis até a 1ª resposta", read_only=1, precision="2"),
			f("horas_resolucao", "Float", "Horas úteis até resolver", read_only=1, precision="2"),
			f("fechado_em", "Datetime", "Fechado em", read_only=1),
			f("reaberturas", "Int", "Reaberturas", read_only=1, default="0"),
			sb("sec_solucao", "Solução e Avaliação"),
			f("solucao", "Text Editor", "Solução aplicada"),
			cb("cb_sol2"),
			f("avaliacao", "Int", "Avaliação (1 a 5)", read_only=1),
			f("comentario_avaliacao", "Small Text", "Comentário da avaliação", read_only=1),
		],
		autoname="format:CH-{#####}",
		naming_rule="Expression",
		title_field="assunto",
		search_fields="assunto,nome_solicitante,status",
		track_changes=1,
		# e-mails para a TI viram chamados (Email Account > Append To = Chamado TI)
		email_append_to=1,
		subject_field="assunto",
		sender_field="email_solicitante",
		sender_name_field="nome_solicitante",
		links=[{"link_doctype": "Interacao Chamado TI", "link_fieldname": "chamado", "group": "Conversa"}],
	)
)

# ------------------------------------------------------------------ Interação (conversa)
write(
	doctype(
		"Interacao Chamado TI",
		[
			f("chamado", "Link", "Chamado", options="Chamado TI", reqd=1, in_list_view=1, search_index=1),
			f("tipo", "Select", "Tipo", options="Resposta\nNota Interna\nSistema", default="Resposta", in_list_view=1,
			  description="Nota Interna: visível só para a TI"),
			f("via", "Select", "Via", options="Portal\nE-mail\nSistema", default="Portal"),
			cb("cb1"),
			f("autor", "Link", "Autor", options="User", in_list_view=1),
			f("autor_nome", "Data", "Nome do Autor"),
			f("de_tecnico", "Check", "Enviada pela TI"),
			sb("sec_msg"),
			f("mensagem", "Text Editor", "Mensagem"),
			f("anexos", "Small Text", "Anexos (URLs)", read_only=1, hidden=1),
		],
		autoname="hash",
		sort_field="creation",
		sort_order="ASC",
	)
)
# ================================================================== FASE 2: inventário
GRUPOS = "Computador\nImpressora\nCelular\nRede e Servidores\nPeriférico\nOutro"
STATUS_EQP = "Em Uso\nEm Estoque\nEm Manutenção\nEmprestado\nDescartado\nExtraviado"

write(
	doctype(
		"Tipo Equipamento TI",
		[
			f("nome", "Data", "Nome", reqd=1, unique=1, in_list_view=1),
			f("grupo", "Select", "Grupo", options=GRUPOS, reqd=1, default="Computador", in_list_view=1, in_standard_filter=1,
			  description="Define quais campos de configuração aparecem no equipamento"),
			f("icone", "Select", "Ícone", options="laptop\nmonitor\nprinter\nsmartphone\nserver\nrouter\nhard-drive\nkeyboard\nmouse\nbattery-charging\npackage", default="laptop"),
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
			  options="Upgrade\nManutenção Corretiva\nManutenção Preventiva\nFormatação / Reinstalação\nTroca de Peça\nOutro",
			  default="Upgrade", reqd=1, in_list_view=1, in_standard_filter=1),
			f("componente", "Select", "Componente alterado",
			  options="\nMemória RAM\nArmazenamento\nProcessador\nSistema Operacional\nOutro",
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
			f("tipo", "Select", "Movimento", options="Entrada\nSaída\nAjuste", reqd=1, default="Saída", in_list_view=1,
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

print("Central TI: DocTypes gerados em", os.path.abspath(RAIZ))
