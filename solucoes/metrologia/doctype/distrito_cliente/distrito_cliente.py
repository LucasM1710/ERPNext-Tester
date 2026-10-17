import frappe
from frappe import _
from frappe.model.document import Document


class DistritoCliente(Document):
	def validate(self):
		self.nome_distrito = (self.nome_distrito or "").strip()
		duplicado = frappe.db.exists(
			"Distrito Cliente",
			{"cliente": self.cliente, "nome_distrito": self.nome_distrito, "name": ["!=", self.name]},
		)
		if duplicado:
			frappe.throw(_("O cliente já possui o distrito {0}.").format(self.nome_distrito))
