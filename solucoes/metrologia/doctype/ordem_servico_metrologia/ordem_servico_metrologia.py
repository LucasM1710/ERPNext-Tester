import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, today

STATUS_FINAIS = ("Concluída", "Enviada")


class OrdemServicoMetrologia(Document):
	def validate(self):
		self.validar_equipamentos_do_cliente()
		self.registrar_mudanca_status()
		if self.status in STATUS_FINAIS and not self.data_conclusao:
			self.data_conclusao = today()

	def validar_equipamentos_do_cliente(self):
		for item in self.itens:
			cliente = frappe.db.get_value("Equipamento Cliente", item.equipamento, "cliente")
			if cliente != self.cliente:
				frappe.throw(
					_("Linha {0}: o equipamento {1} não pertence ao cliente {2}.").format(
						item.idx, item.equipamento, self.cliente
					)
				)

	def registrar_mudanca_status(self):
		anterior = self.get_doc_before_save()
		if anterior and anterior.status == self.status:
			return
		self.append("historico", {"status": self.status, "data": now_datetime(), "usuario": frappe.session.user})
