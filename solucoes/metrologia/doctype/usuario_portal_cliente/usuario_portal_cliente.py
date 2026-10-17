import frappe
from frappe import _
from frappe.model.document import Document


class UsuarioPortalCliente(Document):
	def validate(self):
		duplicado = frappe.db.exists(
			"Usuario Portal Cliente",
			{"usuario": self.usuario, "cliente": self.cliente, "name": ["!=", self.name]},
		)
		if duplicado:
			frappe.throw(_("O usuário {0} já tem acesso configurado para {1}.").format(self.usuario, self.cliente))

		if self.perfil == "Gestor":
			self.distritos = []
		for linha in self.distritos:
			if frappe.db.get_value("Distrito Cliente", linha.distrito, "cliente") != self.cliente:
				frappe.throw(_("O distrito {0} não pertence ao cliente {1}.").format(linha.distrito, self.cliente))
