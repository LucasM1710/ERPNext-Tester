import frappe
from frappe import _
from frappe.model.document import Document

from solucoes.central_ti.doctype.equipamento_ti.equipamento_ti import recalcular

# Componente do upgrade -> campo do equipamento que passa a refletir a mudança
CAMPO_DO_COMPONENTE = {
	"Memória RAM": "memoria_ram",
	"Armazenamento": "armazenamento",
	"Processador": "processador",
	"Sistema Operacional": "sistema_operacional",
}


class ManutencaoEquipamentoTI(Document):
	def validate(self):
		self.executado_por = self.executado_por or frappe.session.user
		campo = CAMPO_DO_COMPONENTE.get(self.componente)
		if campo and self.is_new():
			if not (self.valor_novo or "").strip():
				frappe.throw(_("Informe como ficou o componente (ex.: 16 GB)."))
			self.valor_anterior = frappe.db.get_value("Equipamento TI", self.equipamento, campo)

	def after_insert(self):
		campo = CAMPO_DO_COMPONENTE.get(self.componente)
		if campo:
			# o cadastro do equipamento passa a mostrar a configuração nova
			eqp = frappe.get_doc("Equipamento TI", self.equipamento)
			eqp.set(campo, self.valor_novo.strip())
			eqp.add_comment("Info", _("{0}: {1} → {2} ({3})").format(self.componente, self.valor_anterior or "—", self.valor_novo, self.name))
			eqp.flags.ignore_permissions = True
			eqp.save()

	def on_update(self):
		recalcular(self.equipamento)

	def after_delete(self):
		recalcular(self.equipamento)
