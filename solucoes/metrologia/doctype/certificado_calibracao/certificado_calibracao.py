import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, flt


class CertificadoCalibracao(Document):
	def validate(self):
		equipamento = frappe.get_cached_doc("Equipamento Cliente", self.equipamento)
		self.cliente = equipamento.cliente

		if not self.data_validade and equipamento.periodicidade_meses:
			self.data_validade = add_months(self.data_calibracao, equipamento.periodicidade_meses)
		if self.data_validade and self.data_validade < self.data_calibracao:
			frappe.throw(_("A validade não pode ser anterior à data da calibração."))

		self.calcular_resultado(equipamento.tolerancia)
		self.validar_padroes()

	def validar_padroes(self):
		"""ISO/IEC 17025 6.4/6.5: só emite com padrões válidos na data da calibração."""
		textos = []
		for linha in self.padroes:
			padrao = frappe.get_doc("Padrao Metrologia", linha.padrao)
			motivo, calibracao = padrao.disponivel_em(self.data_calibracao)
			if self.origem == "Interno" and motivo:
				frappe.throw(
					_("Padrão {0} não pode ser usado em {1}: {2}.").format(
						padrao.codigo, frappe.utils.formatdate(self.data_calibracao), motivo
					),
					title=_("Padrão inválido"),
				)
			# congela a calibração do padrão usada (não muda quando o padrão for recalibrado)
			if calibracao and (linha.is_new() or not linha.numero_certificado or self.has_value_changed("data_calibracao")):
				linha.descricao = padrao.descricao
				linha.numero_certificado = calibracao.numero_certificado
				linha.laboratorio_calibrador = calibracao.laboratorio_calibrador
				linha.acreditado = calibracao.acreditado
				linha.data_validade = calibracao.data_validade
			textos.append(
				f"{padrao.codigo} – {linha.descricao or padrao.descricao} · Cert. {linha.numero_certificado or 's/n'}"
				f" ({linha.laboratorio_calibrador or '—'}{', RBC' if linha.acreditado else ''})"
				f" · válido até {frappe.utils.formatdate(linha.data_validade)}"
			)
		if textos:
			self.padroes_utilizados = "\n".join(textos)

	def calcular_resultado(self, tolerancia_equipamento):
		"""Análise crítica: conforme quando |erro| + U <= tolerância."""
		if not self.pontos:
			if not self.resultado:
				self.resultado = "Sem Critério"
			return

		avaliados = 0
		reprovado = False
		for ponto in self.pontos:
			ponto.erro = flt(ponto.valor_medido) - flt(ponto.valor_nominal)
			tolerancia = flt(ponto.tolerancia) or flt(tolerancia_equipamento)
			if not tolerancia:
				ponto.conforme = 0
				continue
			avaliados += 1
			ponto.conforme = int(abs(ponto.erro) + abs(flt(ponto.incerteza)) <= tolerancia)
			reprovado = reprovado or not ponto.conforme

		if not avaliados:
			self.resultado = "Sem Critério"
		else:
			self.resultado = "Reprovado" if reprovado else "Aprovado"

	def on_update(self):
		self.sincronizar_equipamento()

	def after_delete(self):
		self.sincronizar_equipamento()

	def sincronizar_equipamento(self):
		if frappe.db.exists("Equipamento Cliente", self.equipamento):
			frappe.get_doc("Equipamento Cliente", self.equipamento).atualizar_pela_ultima_calibracao()
