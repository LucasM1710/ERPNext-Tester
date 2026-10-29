"""Configuração da Central de TI (módulo "Central TI" do app solucoes).

Chamado por solucoes.setup.after_migrate — ou seja, por `bench --site <site> execute solucoes.setup.instalar`.
Idempotente: cria o papel "Tecnico TI", grava defaults ausentes da configuração e, se vazios,
os prazos de SLA, as categorias de chamado e os tipos de equipamento padrão.
"""

import frappe

CONFIG = "Configuracao Central TI"
PAPEL_TECNICO = "Tecnico TI"

PRAZOS_PADRAO = [  # prioridade, 1ª resposta (h úteis), resolução (h úteis)
	("Crítica", 1, 4),
	("Alta", 2, 8),
	("Média", 4, 16),
	("Baixa", 8, 40),
]

CATEGORIAS_PADRAO = [  # nome, ícone, descrição
	("Acesso e Senha", "key-round", "Senha bloqueada ou esquecida, novo acesso a pasta ou sistema"),
	("Computador e Notebook", "laptop", "Lentidão, travamento, não liga, tela, teclado, mouse"),
	("E-mail e Microsoft 365", "mail", "Outlook, Teams, OneDrive, SharePoint, licença do Office"),
	("Internet e Rede", "wifi", "Sem internet, Wi-Fi, VPN, pasta de rede"),
	("Impressora e Scanner", "printer", "Não imprime, papel, toner, digitalização"),
	("Sistema ERP", "layout-grid", "Erro, acesso ou dúvida no ERP"),
	("Sistemas do Laboratório", "flask-conical", "Software de equipamentos e sistemas usados nas análises"),
	("Instalação de Software", "package", "Instalar ou atualizar um programa"),
	("Celular e Telefonia", "smartphone", "Celular corporativo, ramal, WhatsApp da empresa"),
	("Segurança da Informação", "shield", "E-mail suspeito, vírus, perda ou roubo de equipamento"),
	("Outros", "life-buoy", "O que não se encaixa nas outras categorias"),
]


TIPOS_PADRAO = [  # nome, grupo, ícone, vida útil (anos), controlado em estoque
	("Notebook", "Computador", "laptop", 4, 0),
	("Desktop", "Computador", "monitor", 5, 0),
	("Monitor", "Periférico", "monitor", 6, 0),
	("Impressora", "Impressora", "printer", 5, 0),
	("Celular", "Celular", "smartphone", 3, 0),
	("Switch", "Rede e Servidores", "router", 7, 0),
	("Firewall / Roteador", "Rede e Servidores", "router", 5, 0),
	("Servidor", "Rede e Servidores", "server", 5, 0),
	("Nobreak", "Rede e Servidores", "battery-charging", 5, 0),
	("Mouse", "Periférico", "mouse", 2, 1),
	("Teclado", "Periférico", "keyboard", 3, 1),
	("Outros", "Outro", "package", 5, 0),
]


def configurar():
	garantir_papel()
	preencher_padroes_configuracao()
	garantir_prazos()
	garantir_categorias()
	garantir_tipos()


def garantir_papel():
	if not frappe.db.exists("Role", PAPEL_TECNICO):
		frappe.get_doc({"doctype": "Role", "role_name": PAPEL_TECNICO, "desk_access": 1}).insert(ignore_permissions=True)


def preencher_padroes_configuracao():
	"""Um Single só usa os defaults enquanto nada foi salvo; grava os que faltam."""
	singles = frappe.qb.DocType("Singles")
	salvos = set(frappe.qb.from_(singles).select(singles.field).where(singles.doctype == CONFIG).run(pluck=True))
	for campo in frappe.get_meta(CONFIG).fields:
		if campo.default is not None and campo.fieldname not in salvos:
			frappe.db.set_single_value(CONFIG, campo.fieldname, campo.default)


def garantir_prazos():
	cfg = frappe.get_doc(CONFIG)
	if cfg.prazos:
		return
	for prioridade, resposta, resolucao in PRAZOS_PADRAO:
		cfg.append("prazos", {"prioridade": prioridade, "primeira_resposta_horas": resposta, "resolucao_horas": resolucao})
	cfg.flags.ignore_permissions = True
	cfg.save()


def garantir_categorias():
	if frappe.db.count("Categoria Chamado TI"):
		return
	for ordem, (nome, icone, descricao) in enumerate(CATEGORIAS_PADRAO, start=1):
		frappe.get_doc(
			{"doctype": "Categoria Chamado TI", "nome": nome, "icone": icone, "descricao": descricao, "ordem": ordem * 10, "ativo": 1}
		).insert(ignore_permissions=True)


def garantir_tipos():
	if frappe.db.count("Tipo Equipamento TI"):
		return
	for nome, grupo, icone, vida, estoque in TIPOS_PADRAO:
		frappe.get_doc(
			{"doctype": "Tipo Equipamento TI", "nome": nome, "grupo": grupo, "icone": icone,
			 "vida_util_anos": vida, "controla_estoque": estoque, "ativo": 1}
		).insert(ignore_permissions=True)  # fmt: skip
