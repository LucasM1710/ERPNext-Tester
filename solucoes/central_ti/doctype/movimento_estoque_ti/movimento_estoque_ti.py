import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class MovimentoEstoqueTI(Document):
	def validate(self):
		self.quantidade = cint(self.quantidade)
		if self.tipo in ("Entrada", "Saída") and self.quantidade <= 0:
			frappe.throw(_("A quantidade deve ser maior que zero."))
		if self.tipo == "Ajuste" and not self.quantidade:
			frappe.throw(_("Informe a diferença do ajuste (ex.: -2 ou 3)."))
		if self.is_new():
			saldo = cint(frappe.db.get_value("Item Estoque TI", self.item, "quantidade")) + self.efeito()
			if saldo < 0:
				frappe.throw(_("Estoque insuficiente de {0}: há {1}.").format(self.item, saldo - self.efeito()))
			self.saldo_apos = saldo

	def efeito(self):
		"""Quanto o movimento soma ao saldo (Saída subtrai; Ajuste já vem com sinal)."""
		return -cint(self.quantidade) if self.tipo == "Saída" else cint(self.quantidade)

	def after_insert(self):
		recalcular_saldo(self.item)

	def after_delete(self):
		recalcular_saldo(self.item)


def recalcular_saldo(item):
	saldo = 0
	for m in frappe.get_all("Movimento Estoque TI", filters={"item": item}, fields=["tipo", "quantidade"]):
		saldo += -cint(m.quantidade) if m.tipo == "Saída" else cint(m.quantidade)
	frappe.db.set_value("Item Estoque TI", item, "quantidade", saldo, update_modified=False)
