import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, getdate

from solucoes.metrologia.utils import calcular_situacao


class EquipamentoCliente(Document):
	def validate(self):
		self.tag = (self.tag or "").strip().upper()
		self.validar_tag_unica()
		if self.distrito and frappe.db.get_value("Distrito Cliente", self.distrito, "cliente") != self.cliente:
			frappe.throw(_("O distrito {0} não pertence ao cliente {1}.").format(self.distrito, self.cliente))
		if self.calibrado_por != "Terceiro":
			self.fornecedor_externo = None
		self.recalcular_vencimento_se_periodicidade_mudou()
		self.situacao_calibracao = calcular_situacao(self.proxima_calibracao)
		self.proxima_verificacao = (
			add_days(self.ultima_verificacao, self.verificacao_intervalo_dias)
			if self.ultima_verificacao and self.verificacao_intervalo_dias
			else None
		)

	def validar_tag_unica(self):
		duplicado = frappe.db.exists(
			"Equipamento Cliente",
			{"cliente": self.cliente, "tag": self.tag, "name": ["!=", self.name]},
		)
		if duplicado:
			frappe.throw(
				_("Já existe o equipamento {0} com a TAG {1} para este cliente.").format(duplicado, self.tag),
				title=_("TAG duplicada"),
			)

	def recalcular_vencimento_se_periodicidade_mudou(self):
		"""A periodicidade é decisão do cliente: ao alterá-la, o vencimento segue a nova regra."""
		anterior = self.get_doc_before_save()
		if (
			anterior
			and self.ultima_calibracao
			and self.periodicidade_meses
			and anterior.periodicidade_meses != self.periodicidade_meses
		):
			self.proxima_calibracao = add_months(self.ultima_calibracao, self.periodicidade_meses)

	def atualizar_pela_ultima_calibracao(self):
		"""Sincroniza última/próxima calibração com o certificado mais recente."""
		ultimo = frappe.get_all(
			"Certificado Calibracao",
			filters={"equipamento": self.name},
			fields=["name", "data_calibracao", "data_validade"],
			order_by="data_calibracao desc, creation desc",
			limit=1,
		)
		if ultimo:
			self.ultima_calibracao = ultimo[0].data_calibracao
			self.proxima_calibracao = ultimo[0].data_validade
			self.ultimo_certificado = ultimo[0].name
		else:
			self.ultima_calibracao = self.ultimo_certificado = None
		self.save(ignore_permissions=True)

	def atualizar_pela_ultima_verificacao(self):
		ultima = frappe.get_all(
			"Verificacao Intermediaria",
			filters={"equipamento_doctype": self.doctype, "equipamento": self.name},
			fields=["data", "resultado"],
			order_by="data desc",
			limit=1,
		)
		self.ultima_verificacao = getdate(ultima[0].data) if ultima else None
		self.resultado_ultima_verificacao = ultima[0].resultado if ultima else None
		self.save(ignore_permissions=True)
