import frappe
from frappe import _
from frappe.model.document import Document


class DistritoEquipamento(Document):
	def validate(self):
		# Um distrito por equipamento.
		if frappe.db.exists(
			"Distrito Equipamento",
			{"equipamento_doctype": self.equipamento_doctype, "equipamento": self.equipamento, "name": ["!=", self.name]},
		):
			frappe.throw(_("O equipamento {0} já tem cadastro de distrito/observação.").format(self.equipamento))
		if self.distrito and frappe.db.get_value("Distrito Cliente", self.distrito, "cliente") != self.cliente:
			frappe.throw(_("O distrito {0} não pertence ao cliente {1}.").format(self.distrito, self.cliente))
