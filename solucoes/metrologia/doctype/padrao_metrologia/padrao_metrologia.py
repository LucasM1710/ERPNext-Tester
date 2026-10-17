import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, getdate

from solucoes.metrologia.utils import calcular_situacao, get_dias_alerta_padroes


class PadraoMetrologia(Document):
	def validate(self):
		self.codigo = (self.codigo or "").strip().upper()
		for c in self.calibracoes:
			if not c.data_validade and self.periodicidade_meses:
				c.data_validade = add_months(c.data_calibracao, self.periodicidade_meses)
			if c.data_validade and getdate(c.data_validade) < getdate(c.data_calibracao):
				frappe.throw(_("Linha {0}: a validade não pode ser anterior à data da calibração.").format(c.idx))
		self.atualizar_vigente()
		self.situacao = calcular_situacao(self.data_validade, get_dias_alerta_padroes())

	def atualizar_vigente(self):
		"""Resumo "Calibração Vigente" = a calibração mais recente do histórico."""
		ultima = max(self.calibracoes, key=lambda c: getdate(c.data_calibracao), default=None)
		for campo in ("data_calibracao", "data_validade", "numero_certificado", "laboratorio_calibrador", "acreditado"):
			self.set(campo, ultima.get(campo) if ultima else None)
		self.arquivo_certificado = ultima.arquivo if ultima else None
		if ultima and ultima.incerteza_expandida:
			self.incerteza_expandida = ultima.incerteza_expandida

	def calibracao_em(self, data):
		"""Calibração do padrão válida numa data (a mais recente que cobre a data)."""
		data = getdate(data)
		validas = [
			c
			for c in self.calibracoes
			if getdate(c.data_calibracao) <= data and (not c.data_validade or getdate(c.data_validade) >= data)
		]
		return max(validas, key=lambda c: getdate(c.data_calibracao), default=None)

	def disponivel_em(self, data):
		"""(motivo, calibração). motivo None = o padrão pode ser usado nesta data."""
		if self.status in ("Bloqueado", "Inativo"):
			return _("o padrão está {0}").format(self.status.lower()), None
		calibracao = self.calibracao_em(data)
		if not calibracao:
			if not self.calibracoes:
				return _("o padrão não tem calibração registrada"), None
			return _("nenhuma calibração do padrão estava válida em {0}").format(frappe.utils.formatdate(data)), None
		return None, calibracao


@frappe.whitelist()
def certificados_afetados(padrao, desde=None):
	"""Rastreabilidade reversa: certificados emitidos com o padrão (a partir de `desde`)."""
	frappe.has_permission("Padrao Metrologia", "read", padrao, throw=True)
	cert = frappe.qb.DocType("Certificado Calibracao")
	uso = frappe.qb.DocType("Certificado Padrao Utilizado")
	q = (
		frappe.qb.from_(cert)
		.join(uso)
		.on(uso.parent == cert.name)
		.select(cert.name, cert.tag, cert.descricao_equipamento, cert.cliente, cert.data_calibracao, cert.resultado)
		.where((uso.padrao == padrao) & (uso.parenttype == "Certificado Calibracao"))
		.orderby(cert.data_calibracao, order=frappe.qb.desc)
	)
	if desde:
		q = q.where(cert.data_calibracao >= desde)
	return q.run(as_dict=True)
