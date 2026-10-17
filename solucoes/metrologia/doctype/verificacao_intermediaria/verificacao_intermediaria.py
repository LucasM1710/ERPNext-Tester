import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class VerificacaoIntermediaria(Document):
	def validate(self):
		if not self.pontos:
			frappe.throw(_("Informe ao menos uma leitura."))
		if self.equipamento_doctype == "Equipamento Cliente":
			eqp = frappe.db.get_value(
				"Equipamento Cliente",
				self.equipamento,
				["tag", "cliente", "distrito", "tolerancia", "tolerancia_verificacao"],
				as_dict=True,
			)
			self.tag, self.cliente, self.distrito = eqp.tag, eqp.cliente, eqp.distrito
			self.tolerancia = self.tolerancia or eqp.tolerancia_verificacao or eqp.tolerancia
		# Outros DocTypes (adapter da empresa): tag/cliente/tolerância vêm preenchidos pelo adapter

		tolerancia = abs(flt(self.tolerancia))
		for p in self.pontos:
			p.desvio = flt(p.valor_lido) - flt(p.valor_referencia)
			p.conforme = int(not tolerancia or abs(p.desvio) <= tolerancia)
		self.resultado = "Conforme" if all(p.conforme for p in self.pontos) else "Não Conforme"
		self.realizado_por = self.realizado_por or frappe.session.user

	def on_update(self):
		if self.equipamento_doctype == "Equipamento Cliente":
			frappe.get_doc("Equipamento Cliente", self.equipamento).atualizar_pela_ultima_verificacao()
