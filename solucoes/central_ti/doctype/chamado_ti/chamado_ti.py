import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from solucoes.central_ti import notificacoes
from solucoes.central_ti.sla import (
	adicionar_horas_uteis,
	agora,
	config,
	expediente,
	horas_uteis_entre,
	prazos_da_prioridade,
	situacao,
)

ABERTOS = ("Aberto", "Em Atendimento", "Aguardando Usuário")
ENCERRADOS = ("Resolvido", "Fechado", "Cancelado")

# Pergunta simples ao colaborador ("quanto isso atrapalha?") -> prioridade
PRIORIDADE_POR_IMPACTO = {
	"Consigo trabalhar normalmente": "Baixa",
	"Atrapalha, mas consigo trabalhar": "Média",
	"Não consigo trabalhar": "Alta",
	"Afeta várias pessoas ou a empresa": "Crítica",
}


class ChamadoTI(Document):
	def before_insert(self):
		self.aberto_em = self.aberto_em or agora()
		self.preencher_solicitante()
		if self.impacto and not self.flags.prioridade_manual:
			self.prioridade = PRIORIDADE_POR_IMPACTO.get(self.impacto, self.prioridade)
		self.prioridade = self.prioridade or "Média"
		self.horas_pausadas = 0
		self.calcular_prazos()
		if not self.responsavel:
			self.responsavel = distribuir(self.categoria)

	def preencher_solicitante(self):
		if not self.solicitante and self.email_solicitante:
			self.solicitante = frappe.db.get_value("User", {"name": self.email_solicitante}) or frappe.db.get_value(
				"User", {"email": self.email_solicitante}
			)
		if self.solicitante:
			usuario = frappe.db.get_value("User", self.solicitante, ["email", "full_name"], as_dict=True) or {}
			self.email_solicitante = self.email_solicitante or usuario.get("email")
			self.nome_solicitante = self.nome_solicitante or usuario.get("full_name")
			if not self.departamento and frappe.db.table_exists("Employee"):
				self.departamento = frappe.db.get_value("Employee", {"user_id": self.solicitante}, "department")
		if not self.nome_solicitante and self.email_solicitante:
			self.nome_solicitante = self.email_solicitante.split("@")[0]

	def calcular_prazos(self):
		exp = expediente()
		resposta, resolucao = prazos_da_prioridade(self.prioridade)
		self.prazo_resposta = adicionar_horas_uteis(self.aberto_em, resposta, exp)
		self.prazo_resolucao = adicionar_horas_uteis(self.aberto_em, resolucao + flt(self.horas_pausadas), exp)

	def validate(self):
		anterior = self.get_doc_before_save()
		if anterior:
			if anterior.prioridade != self.prioridade:
				self.calcular_prazos()
			if anterior.status != self.status:
				self.mudou_status(anterior.status)
		self.atualizar_sla()

	def mudou_status(self, de):
		para, momento, exp = self.status, agora(), expediente()
		# pausa do SLA de resolução enquanto aguarda o colaborador (boa prática ITIL)
		if para == "Aguardando Usuário":
			self.pausado_em = momento
		elif de == "Aguardando Usuário" and self.pausado_em:
			pausa = horas_uteis_entre(self.pausado_em, momento, exp)
			self.horas_pausadas = flt(self.horas_pausadas) + pausa
			self.prazo_resolucao = adicionar_horas_uteis(self.prazo_resolucao, pausa, exp)
			self.pausado_em = None

		if para in ABERTOS and de in ("Resolvido", "Fechado"):
			self.reaberturas = cint(self.reaberturas) + 1
			self.resolvido_em = self.fechado_em = None
			self.horas_resolucao = None
			self.avaliacao = None
		if para == "Resolvido":
			self.resolvido_em = momento
			self.horas_resolucao = max(0, horas_uteis_entre(self.aberto_em, momento, exp) - flt(self.horas_pausadas))
		if para in ("Fechado", "Cancelado"):
			self.fechado_em = momento
			if para == "Fechado" and not self.resolvido_em:
				self.resolvido_em = momento
				self.horas_resolucao = max(0, horas_uteis_entre(self.aberto_em, momento, exp) - flt(self.horas_pausadas))

	def registrar_primeira_resposta(self):
		if self.primeira_resposta_em:
			return
		self.primeira_resposta_em = agora()
		self.horas_primeira_resposta = horas_uteis_entre(self.aberto_em, self.primeira_resposta_em, expediente())

	def atualizar_sla(self, momento=None):
		momento = momento or agora()
		exp, alerta = expediente(), config().alerta_sla_percentual
		self.sla_resposta = situacao(self.aberto_em, self.prazo_resposta, self.primeira_resposta_em, momento, alerta, exp)
		if self.status == "Cancelado":
			return
		if self.status == "Aguardando Usuário":
			return  # SLA de resolução pausado: mantém a situação em que estava
		self.sla_resolucao = situacao(self.aberto_em, self.prazo_resolucao, self.resolvido_em, momento, alerta, exp)

	def after_insert(self):
		registrar_sistema(self.name, _("Chamado aberto por {0} via {1}.").format(self.nome_solicitante or self.email_solicitante, self.canal))
		if self.equipamento:
			atualizar_contagem_equipamentos(self.equipamento)
		if self.responsavel:
			registrar_sistema(self.name, _("Atribuído automaticamente a {0}.").format(nome(self.responsavel)))
		notificacoes.chamado_aberto(self)

	def on_update(self):
		anterior = self.get_doc_before_save()
		if not anterior:
			return
		if anterior.status != self.status:
			registrar_sistema(
				self.name, _("Status alterado de {0} para {1} por {2}.").format(anterior.status, self.status, nome(frappe.session.user))
			)
			if self.status == "Resolvido":
				notificacoes.chamado_resolvido(self)
		if anterior.responsavel != self.responsavel and self.responsavel:
			registrar_sistema(self.name, _("Atribuído a {0} por {1}.").format(nome(self.responsavel), nome(frappe.session.user)))
			if self.responsavel != frappe.session.user:
				notificacoes.chamado_atribuido(self)
		if anterior.prioridade != self.prioridade:
			registrar_sistema(
				self.name, _("Prioridade alterada de {0} para {1}; prazos recalculados.").format(anterior.prioridade, self.prioridade)
			)
		if anterior.equipamento != self.equipamento:
			atualizar_contagem_equipamentos(anterior.equipamento, self.equipamento)
			if self.equipamento:
				registrar_sistema(self.name, _("Equipamento {0} vinculado ao chamado.").format(self.equipamento))


# ------------------------------------------------------------------ apoio
def atualizar_contagem_equipamentos(*equipamentos):
	from solucoes.central_ti.doctype.equipamento_ti.equipamento_ti import recalcular

	for e in equipamentos:
		recalcular(e)


def nome(usuario):
	if not usuario:
		return ""
	return frappe.utils.get_fullname(usuario) or usuario


def registrar_sistema(chamado, mensagem):
	frappe.get_doc(
		{
			"doctype": "Interacao Chamado TI",
			"chamado": chamado,
			"tipo": "Sistema",
			"via": "Sistema",
			"autor": frappe.session.user,
			"autor_nome": nome(frappe.session.user),
			"mensagem": mensagem,
		}
	).insert(ignore_permissions=True)


def tecnicos_ativos(automatico=False) -> list:
	return [
		t.usuario
		for t in config().tecnicos or []
		if t.ativo and (t.recebe_automatico or not automatico) and frappe.db.get_value("User", t.usuario, "enabled")
	]


def distribuir(categoria=None):
	"""Técnico para um chamado novo: o padrão da categoria ou quem tem menos chamados em aberto;
	no empate, quem recebeu menos chamados nos últimos 30 dias (rodízio justo)."""
	ativos = tecnicos_ativos(automatico=True)
	if not ativos:
		return None
	padrao = frappe.db.get_value("Categoria Chamado TI", categoria, "tecnico_padrao") if categoria else None
	if padrao and padrao in tecnicos_ativos():
		return padrao
	carga = {t: 0 for t in ativos}
	for r in frappe.get_all("Chamado TI", filters={"status": ["in", ABERTOS], "responsavel": ["in", ativos]}, pluck="responsavel"):
		carga[r] = carga.get(r, 0) + 1
	recentes = {t: 0 for t in ativos}
	desde = frappe.utils.add_days(agora(), -30)
	for r in frappe.get_all("Chamado TI", filters={"aberto_em": [">=", desde], "responsavel": ["in", ativos]}, pluck="responsavel"):
		recentes[r] = recentes.get(r, 0) + 1
	return min(ativos, key=lambda t: (carga[t], recentes[t], ativos.index(t)))
