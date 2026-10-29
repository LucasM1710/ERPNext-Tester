import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_years, cint, flt, now_datetime

INATIVOS = ("Descartado", "Extraviado")


class EquipamentoTI(Document):
	def validate(self):
		self.nome = (self.nome or "").strip().upper()
		self.responsavel_nome = frappe.utils.get_fullname(self.responsavel) if self.responsavel else None
		self.ajustar_status_pelo_responsavel()
		self.registrar_troca_de_responsavel()
		vida = cint(frappe.db.get_value("Tipo Equipamento TI", self.tipo, "vida_util_anos")) if self.tipo else 0
		self.fim_vida_util = add_years(self.data_compra, vida) if self.data_compra and vida else None
		self.custo_total = flt(self.valor_compra) + flt(self.custo_manutencoes)

	def ajustar_status_pelo_responsavel(self):
		"""Entregou para alguém -> Em Uso; devolveu (tirou o responsável) -> Em Estoque.
		Equipamentos de uso coletivo (impressora, switch) ficam Em Uso sem responsável."""
		anterior = self.get_doc_before_save()
		if self.responsavel and self.status == "Em Estoque":
			self.status = "Em Uso"
		elif not self.responsavel and anterior and anterior.responsavel and self.status == "Em Uso":
			self.status = "Em Estoque"

	def registrar_troca_de_responsavel(self):
		anterior = self.get_doc_before_save()
		mudou = (anterior.responsavel if anterior else None) != self.responsavel
		if not mudou or (self.is_new() and not self.responsavel):
			return
		self.append(
			"historico_responsaveis",
			{
				"data": now_datetime(),
				"responsavel": self.responsavel,
				"responsavel_nome": self.responsavel_nome or _("(devolvido ao estoque da TI)"),
				"departamento": self.departamento,
				"registrado_por": frappe.session.user,
			},
		)


def recalcular(equipamento):
	"""Custos e contadores do equipamento a partir das manutenções e chamados ligados a ele."""
	if not equipamento or not frappe.db.exists("Equipamento TI", equipamento):
		return
	manutencoes = frappe.get_all("Manutencao Equipamento TI", filters={"equipamento": equipamento}, pluck="custo")
	custo = sum(flt(c) for c in manutencoes)
	valor = flt(frappe.db.get_value("Equipamento TI", equipamento, "valor_compra"))
	frappe.db.set_value(
		"Equipamento TI",
		equipamento,
		{
			"custo_manutencoes": custo,
			"qtd_manutencoes": len(manutencoes),
			"custo_total": valor + custo,
			"qtd_chamados": frappe.db.count("Chamado TI", {"equipamento": equipamento}),
		},
		update_modified=False,
	)
