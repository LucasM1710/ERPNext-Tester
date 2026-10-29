"""Dados de demonstração da Central de TI (NUNCA rodar na produção).

	bench --site <site> execute solucoes.central_ti.demo.criar
	bench --site <site> execute solucoes.central_ti.demo.apagar

Cria 2 técnicos, 12 colaboradores e ~90 chamados nos últimos 60 dias, passando cada um pelo
fluxo real (abertura, resposta, espera pelo colaborador, solução, avaliação) com o relógio
"voltado no tempo" — assim SLA, tempos e indicadores saem calculados pelas regras de verdade.
Nenhum e-mail é enviado. Senha de todos: Demo@12345
"""

import random
from datetime import datetime, time, timedelta

import frappe
from frappe.utils import now_datetime

from solucoes.central_ti import sla
from solucoes.central_ti.doctype.chamado_ti import chamado_ti as modulo_chamado
from solucoes.central_ti.servico import registrar_resposta

SENHA = "Demo@12345"
TECNICOS = [("ana.ti@demo.com", "Ana Souza"), ("rafael.ti@demo.com", "Rafael Lima")]
COLABORADORES = [
	("joana.lab@demo.com", "Joana Martins", "Laboratório Físico-Químico"),
	("pedro.lab@demo.com", "Pedro Alves", "Laboratório Físico-Químico"),
	("carla.micro@demo.com", "Carla Nunes", "Microbiologia"),
	("diego.micro@demo.com", "Diego Rocha", "Microbiologia"),
	("fernanda.qual@demo.com", "Fernanda Dias", "Qualidade"),
	("marcos.qual@demo.com", "Marcos Pinto", "Qualidade"),
	("lucia.com@demo.com", "Lúcia Ferraz", "Comercial"),
	("bruno.com@demo.com", "Bruno Teixeira", "Comercial"),
	("paula.fin@demo.com", "Paula Gomes", "Financeiro"),
	("renato.adm@demo.com", "Renato Costa", "Administrativo"),
	("sofia.log@demo.com", "Sofia Ramos", "Logística"),
	("tiago.cal@demo.com", "Tiago Moreira", "Metrologia"),
]
ASSUNTOS = {
	"Acesso e Senha": ["Senha do Windows bloqueada", "Preciso de acesso à pasta da Qualidade", "Esqueci a senha do ERP", "Liberar acesso ao SharePoint do laboratório"],
	"Computador e Notebook": ["Notebook muito lento", "Computador não liga", "Tela piscando no monitor", "Teclado com teclas falhando", "Mouse sem fio parou"],
	"E-mail e Microsoft 365": ["Outlook não sincroniza", "Teams sem áudio na reunião", "OneDrive não sincroniza arquivos", "Caixa de e-mail cheia", "Não recebo e-mails de cliente"],
	"Internet e Rede": ["Sem internet na sala 2", "Wi-Fi caindo toda hora", "VPN não conecta em casa", "Pasta de rede não abre"],
	"Impressora e Scanner": ["Impressora do laboratório não imprime", "Scanner não envia para e-mail", "Toner acabando na recepção", "Papel atolando na impressora"],
	"Sistema ERP": ["Erro ao emitir nota no ERP", "Relatório do ERP não abre", "ERP lento para salvar OS"],
	"Sistemas do Laboratório": ["Software do espectrofotômetro não abre", "Exportação de dados do cromatógrafo falhou", "Licença do software de análise expirou"],
	"Instalação de Software": ["Instalar Power BI", "Atualizar Adobe Reader", "Instalar software do novo equipamento"],
	"Celular e Telefonia": ["Ramal sem linha", "Celular corporativo não carrega", "Configurar e-mail no celular novo"],
	"Segurança da Informação": ["Recebi um e-mail suspeito de boleto", "Antivírus mostrou alerta", "Perdi o crachá/token de acesso"],
	"Outros": ["Projetor da sala de reunião", "Dúvida sobre backup dos meus arquivos"],
}
PESOS_CATEGORIA = [6, 8, 9, 5, 6, 4, 3, 3, 2, 2, 2]
IMPACTOS = [
	("Consigo trabalhar normalmente", 3),
	("Atrapalha, mas consigo trabalhar", 6),
	("Não consigo trabalhar", 3),
	("Afeta várias pessoas ou a empresa", 1),
]
SOLUCOES = [
	"Reiniciado o serviço e limpo o cache; testado com o usuário.",
	"Senha redefinida e MFA reconfigurado no Microsoft 365.",
	"Driver atualizado e equipamento testado.",
	"Permissão concedida no grupo de segurança correspondente.",
	"Perfil do Outlook recriado; sincronização normalizada.",
	"Cabo de rede substituído; conexão estável.",
	"Software instalado e licença ativada.",
	"E-mail analisado: phishing. Bloqueado o remetente e orientado o colaborador.",
]


def criar():
	if frappe.db.count("Chamado TI"):
		print("Os chamados de demonstração já existem (nada foi feito). Para recriar: solucoes.central_ti.demo.apagar e depois criar.")
		return
	random.seed(2026)
	frappe.flags.mute_emails = True
	frappe.set_user("Administrator")
	_usuarios()
	_configurar_equipe()
	agora_real = now_datetime()
	categorias = list(ASSUNTOS)
	try:
		plano = [(random.triangular(4, 60, 10), None) for _ in range(75)]
		plano += [(random.uniform(0, 4), random.choices(["sem_resposta", "respondido", "aguardando", "resolvido"], [4, 6, 3, 2])[0]) for _ in range(15)]
		plano.sort(key=lambda p: -p[0])  # do mais antigo para o mais recente
		for dias_atras, estagio in plano:
			_um_chamado(agora_real, random.choices(categorias, PESOS_CATEGORIA)[0], dias_atras, estagio)
		_viajar(agora_real)
		from solucoes.central_ti.tarefas import atualizar_sla

		atualizar_sla()
	finally:
		_viajar(None)
		frappe.set_user("Administrator")
	frappe.db.commit()
	print(f"Central de TI: {frappe.db.count('Chamado TI')} chamados. Técnicos: {', '.join(t for t, _ in TECNICOS)} · "
	      f"colaborador ex.: {COLABORADORES[0][0]} · senha {SENHA}")  # fmt: skip


def apagar():
	frappe.set_user("Administrator")
	for nome in frappe.get_all("Chamado TI", pluck="name"):
		for f in frappe.get_all("File", filters={"attached_to_doctype": "Chamado TI", "attached_to_name": nome}, pluck="name"):
			frappe.delete_doc("File", f, force=True, ignore_permissions=True)
		frappe.db.delete("Interacao Chamado TI", {"chamado": nome})
		frappe.delete_doc("Chamado TI", nome, force=True, ignore_permissions=True)
	frappe.db.commit()
	print("Chamados de demonstração removidos (usuários mantidos).")


# ------------------------------------------------------------------ apoio
def _viajar(momento):
	"""Faz o relógio das regras de SLA marcar `momento` (None = relógio real)."""
	relogio = (lambda: momento) if momento else now_datetime
	modulo_chamado.agora = relogio
	sla.agora = relogio


def _usuarios():
	for email, nome in TECNICOS:
		_usuario(email, nome, "System User", ["Tecnico TI"])
	for email, nome, _dep in COLABORADORES:
		_usuario(email, nome, "Website User", [])


def _usuario(email, nome, tipo, papeis):
	if frappe.db.exists("User", email):
		return
	primeiro, _, resto = nome.partition(" ")
	u = frappe.get_doc(
		{"doctype": "User", "email": email, "first_name": primeiro, "last_name": resto, "user_type": tipo,
		 "send_welcome_email": 0, "roles": [{"role": p} for p in papeis]}
	).insert(ignore_permissions=True)  # fmt: skip
	u.new_password = SENHA
	u.save(ignore_permissions=True)


def _configurar_equipe():
	cfg = frappe.get_doc("Configuracao Central TI")
	if not cfg.tecnicos:
		for email, _nome in TECNICOS:
			cfg.append("tecnicos", {"usuario": email, "ativo": 1, "recebe_automatico": 1})
		cfg.flags.ignore_permissions = True
		cfg.save()
	frappe.clear_document_cache("Configuracao Central TI", "Configuracao Central TI")


def _hora_util(agora_real, dias_atras):
	dia = (agora_real - timedelta(days=dias_atras)).date()
	while dia.weekday() >= 5:
		dia -= timedelta(days=1)
	return datetime.combine(dia, time(random.randint(8, 16), random.choice([0, 10, 20, 30, 40, 50])))


def _depois(momento, horas_uteis):
	return sla.adicionar_horas_uteis(momento, horas_uteis, sla.expediente())


def _marcar_criacao(antes, momento):
	for nome in frappe.get_all("Interacao Chamado TI", filters={"name": ["not in", list(antes) or [""]]}, pluck="name"):
		frappe.db.set_value("Interacao Chamado TI", nome, "creation", momento, update_modified=False)


def _passo(momento, usuario, acao):
	antes = set(frappe.get_all("Interacao Chamado TI", pluck="name"))
	_viajar(momento)
	frappe.set_user(usuario)
	acao()
	frappe.set_user("Administrator")
	_marcar_criacao(antes, momento)


def _um_chamado(agora_real, categoria, dias_atras, estagio=None):
	"""estagio: None = fluxo completo; senão o chamado para em sem_resposta/respondido/aguardando/resolvido."""
	email, nome, departamento = random.choice(COLABORADORES)
	t0 = _hora_util(agora_real, dias_atras)
	if t0 > agora_real:
		t0 = agora_real - timedelta(hours=1)
	impacto = random.choices([x for x, _ in IMPACTOS], [w for _, w in IMPACTOS])[0]
	doc = {}

	def abrir():
		d = frappe.get_doc(
			{"doctype": "Chamado TI", "assunto": random.choice(ASSUNTOS[categoria]), "categoria": categoria, "impacto": impacto,
			 "descricao": f"<p>{random.choice(['Desde hoje cedo', 'Desde ontem', 'Há alguns dias'])} estou com esse problema. "
			              f"Pode me ajudar? ({departamento})</p>",
			 "solicitante": email, "departamento": departamento, "aberto_em": t0,
			 "canal": random.choices(["Portal", "E-mail", "Telefone"], [7, 2, 1])[0]}
		).insert(ignore_permissions=True)  # fmt: skip
		doc["d"] = d

	_passo(t0, email, abrir)
	d = doc["d"]
	tecnico = d.responsavel or TECNICOS[0][0]
	idade_h = sla.horas_uteis_entre(t0, agora_real, sla.expediente())

	# 1ª resposta: na maioria dentro do prazo; ~12% atrasadas
	prazo_r, prazo_s = sla.prazos_da_prioridade(d.prioridade)
	atraso = random.random() < 0.12
	h_resp = prazo_r * (random.uniform(1.1, 2.5) if atraso else random.uniform(0.1, 0.9))
	if estagio == "sem_resposta" or h_resp >= idade_h:
		return  # ainda sem resposta (chamado recente)
	if estagio:
		h_resp = min(h_resp, idade_h * 0.5)
	t1 = _depois(t0, h_resp)
	_passo(t1, tecnico, lambda: registrar_resposta(
		frappe.get_doc("Chamado TI", d.name), "<p>Olá! Já estou verificando. Você consegue me mandar um print do erro?</p>",
		autor=tecnico, de_tecnico=True))  # fmt: skip

	if estagio == "respondido":
		return
	t_atual = t1
	if estagio == "aguardando":
		def so_aguardar():
			c = frappe.get_doc("Chamado TI", d.name)
			c.status = "Aguardando Usuário"
			c.flags.ignore_permissions = True
			c.save()

		_passo(_depois(t1, 0.1) if _depois(t1, 0.1) < agora_real else t1, tecnico, so_aguardar)
		return
	if random.random() < 0.3:  # aguardando o colaborador
		def aguardar():
			c = frappe.get_doc("Chamado TI", d.name)
			c.status = "Aguardando Usuário"
			c.flags.ignore_permissions = True
			c.save()

		_passo(_depois(t1, 0.2), tecnico, aguardar)
		t_resp = _depois(t1, random.uniform(1, 6))
		if t_resp >= agora_real:
			return
		_passo(t_resp, email, lambda: registrar_resposta(
			frappe.get_doc("Chamado TI", d.name), "<p>Segue o print. Aconteceu de novo agora.</p>", autor=email))  # fmt: skip
		t_atual = t_resp

	# resolução: ~15% estouram o prazo; os mais recentes podem seguir em aberto
	estouro = random.random() < 0.15
	h_sol = prazo_s * (random.uniform(1.05, 2.2) if estouro else random.uniform(0.15, 0.85))
	t2 = max(_depois(t0, h_sol), _depois(t_atual, 0.3))
	if estagio == "resolvido":
		t2 = min(t2, agora_real - timedelta(minutes=30))
	elif t2 >= agora_real:
		return

	def resolver():
		c = frappe.get_doc("Chamado TI", d.name)
		c.solucao = f"<p>{random.choice(SOLUCOES)}</p>"
		c.status = "Resolvido"
		c.flags.ignore_permissions = True
		c.save()

	_passo(t2, tecnico, resolver)

	if random.random() < 0.06 and _depois(t2, 4) < agora_real:  # reaberto e resolvido de novo
		t3 = _depois(t2, random.uniform(1, 3))
		_passo(t3, email, lambda: registrar_resposta(
			frappe.get_doc("Chamado TI", d.name), "<p>Voltou a acontecer depois de reiniciar.</p>", autor=email))  # fmt: skip
		t4 = _depois(t3, random.uniform(1, 4))
		if t4 < agora_real:
			_passo(t4, tecnico, resolver)
			t2 = t4

	if random.random() < 0.75:  # avaliação
		nota = random.choices([5, 4, 3, 2, 1], [55, 30, 10, 3, 2])[0]
		comentario = {5: "Rápido e resolveu!", 4: "Bom atendimento.", 3: "Resolveu, mas demorou.", 2: "Demorou bastante.", 1: "Ainda tenho problemas."}[nota]
		frappe.db.set_value("Chamado TI", d.name, {"avaliacao": nota, "comentario_avaliacao": comentario}, update_modified=False)

	t_fecha = _depois(t2, 3 * 10)
	if not estagio and t_fecha < agora_real:
		def fechar():
			c = frappe.get_doc("Chamado TI", d.name)
			c.status = "Fechado"
			c.flags.ignore_permissions = True
			c.save()

		_passo(t_fecha, "Administrator", fechar)
