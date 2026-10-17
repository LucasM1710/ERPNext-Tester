import frappe
from frappe.utils import add_days, getdate, today


CONFIG = "Configuracao Portal Metrologia"


def get_dias_alerta() -> int:
	return frappe.db.get_single_value(CONFIG, "dias_alerta") or 30


def get_dias_alerta_padroes() -> int:
	return frappe.db.get_single_value(CONFIG, "dias_alerta_padroes") or 45


def calcular_situacao(proxima_calibracao, dias_alerta: int | None = None) -> str:
	"""Em Dia / A Vencer / Vencido / Sem Calibração a partir da data de vencimento."""
	if not proxima_calibracao:
		return "Sem Calibração"

	if dias_alerta is None:
		dias_alerta = get_dias_alerta()

	proxima = getdate(proxima_calibracao)
	hoje = getdate(today())
	if proxima < hoje:
		return "Vencido"
	if proxima <= getdate(add_days(hoje, dias_alerta)):
		return "A Vencer"
	return "Em Dia"


def atualizar_situacao_equipamentos():
	"""Job diário: a situação depende da data de hoje, então precisa ser recalculada."""
	dias_alerta = get_dias_alerta()
	for eqp in frappe.get_all(
		"Equipamento Cliente",
		filters={"status": ["not in", ["Inativo", "Sucateado"]]},
		fields=["name", "proxima_calibracao", "situacao_calibracao"],
	):
		situacao = calcular_situacao(eqp.proxima_calibracao, dias_alerta)
		if situacao != eqp.situacao_calibracao:
			frappe.db.set_value(
				"Equipamento Cliente", eqp.name, "situacao_calibracao", situacao, update_modified=False
			)


def atualizar_situacao_padroes():
	"""Job diário: recalcula a situação dos padrões e avisa o laboratório dos vencidos/a vencer."""
	dias = get_dias_alerta_padroes()
	atencao = []
	for p in frappe.get_all(
		"Padrao Metrologia",
		filters={"status": ["!=", "Inativo"]},
		fields=["name", "codigo", "descricao", "data_validade", "situacao", "status"],
	):
		situacao = calcular_situacao(p.data_validade, dias)
		if situacao != p.situacao:
			frappe.db.set_value("Padrao Metrologia", p.name, "situacao", situacao, update_modified=False)
		if situacao in ("Vencido", "A Vencer") and p.status != "Bloqueado":
			atencao.append({**p, "situacao": situacao})

	destinatarios = [
		e.strip() for e in (frappe.db.get_single_value(CONFIG, "emails_alerta_padroes") or "").splitlines() if e.strip()
	]
	if atencao and destinatarios:
		linhas = "".join(
			f"<tr><td><b>{frappe.utils.escape_html(p['codigo'])}</b></td><td>{frappe.utils.escape_html(p['descricao'])}</td>"
			f"<td>{frappe.utils.formatdate(p['data_validade'])}</td><td>{p['situacao']}</td></tr>"
			for p in sorted(atencao, key=lambda p: str(p["data_validade"] or ""))
		)
		frappe.sendmail(
			recipients=destinatarios,
			subject=f"Padrões: {sum(p['situacao'] == 'Vencido' for p in atencao)} vencido(s), "
			f"{sum(p['situacao'] == 'A Vencer' for p in atencao)} a vencer",
			message=f"<p>Padrões que precisam de calibração (alerta de {dias} dias):</p>"
			f"<table border='1' cellpadding='6' style='border-collapse:collapse'><tr><th>Código</th><th>Descrição</th>"
			f"<th>Validade</th><th>Situação</th></tr>{linhas}</table>"
			"<p>Padrões vencidos são bloqueados automaticamente na emissão de certificados.</p>",
		)
