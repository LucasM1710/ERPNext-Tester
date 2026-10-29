"""E-mails da Central de TI.

Todos levam "(#CH-xxxxx)" no assunto e são ligados ao chamado: quando o colaborador
responde pelo Outlook, a resposta volta para o mesmo chamado (ver email.py).
Uma falha de e-mail nunca impede o chamado de ser salvo.
"""

import frappe
from frappe.utils import escape_html, format_datetime, get_url

from solucoes.central_ti.sla import config


def link(chamado, extra=""):
	return get_url(f"/ti/chamados/{chamado.name}{extra}")


def _email_de(usuario):
	if not usuario:
		return None
	return frappe.db.get_value("User", usuario, "email") or (usuario if "@" in usuario else None)


def _tecnicos():
	from solucoes.central_ti.doctype.chamado_ti.chamado_ti import tecnicos_ativos

	return [_email_de(t) for t in tecnicos_ativos()]


def _tem_email_de_saida():
	return bool(frappe.db.exists("Email Account", {"enable_outgoing": 1, "default_outgoing": 1}))


def _enviar(destinatarios, chamado, titulo, corpo_html, botao="Abrir chamado", url=None):
	if not config().notificar_por_email or not _tem_email_de_saida():
		return  # sem conta de saída configurada: o chamado segue normalmente, só sem e-mail
	eu = _email_de(frappe.session.user)
	destinatarios = sorted({d for d in destinatarios if d and d != eu})
	if not destinatarios:
		return
	try:
		frappe.sendmail(
			recipients=destinatarios,
			subject=f"{titulo}: {chamado.assunto} (#{chamado.name})",
			message=_modelo(chamado, titulo, corpo_html, botao, url or link(chamado)),
			reference_doctype=chamado.doctype,
			reference_name=chamado.name,
			reply_to=config().email_ti or None,
		)
	except Exception:
		frappe.clear_messages()  # o erro de e-mail não deve aparecer para quem abriu/respondeu
		frappe.log_error(title=f"Central de TI: e-mail do chamado {chamado.name}")


def _modelo(chamado, titulo, corpo_html, botao, url):
	nome_central = escape_html(config().titulo or "Central de TI")
	return f"""
<div style="font-family:Inter,Segoe UI,Arial,sans-serif;max-width:600px;margin:auto;color:#0f172a">
  <div style="background:#4f46e5;color:#fff;padding:18px 24px;border-radius:14px 14px 0 0">
    <div style="font-size:12px;opacity:.85">{nome_central}</div>
    <div style="font-size:18px;font-weight:600;margin-top:2px">{escape_html(titulo)}</div>
  </div>
  <div style="border:1px solid #e2e8f0;border-top:0;padding:22px 24px;border-radius:0 0 14px 14px">
    <p style="margin:0 0 4px;color:#64748b;font-size:13px">Chamado {chamado.name} · {escape_html(chamado.status)} · prioridade {escape_html(chamado.prioridade)}</p>
    <p style="margin:0 0 16px;font-size:16px;font-weight:600">{escape_html(chamado.assunto)}</p>
    {corpo_html}
    <p style="margin:24px 0 8px"><a href="{url}" style="background:#4f46e5;color:#fff;padding:10px 18px;border-radius:10px;text-decoration:none;font-weight:600">{escape_html(botao)}</a></p>
    <p style="color:#94a3b8;font-size:12px;margin-top:20px">Você pode responder a este e-mail: a resposta entra no chamado.</p>
  </div>
</div>"""


# ------------------------------------------------------------------ eventos
def chamado_aberto(chamado):
	_enviar(
		[chamado.email_solicitante],
		chamado,
		"Recebemos seu chamado",
		f"<p>Olá, {escape_html((chamado.nome_solicitante or '').split(' ')[0])}! Seu chamado foi registrado"
		f"{' e está com ' + escape_html(frappe.utils.get_fullname(chamado.responsavel)) if chamado.responsavel else ''}.</p>"
		f"<p>Previsão da primeira resposta: <b>{format_datetime(chamado.prazo_resposta, 'dd/MM/yyyy HH:mm')}</b>.</p>",
		"Acompanhar chamado",
	)
	destino = [_email_de(chamado.responsavel)] if chamado.responsavel else _tecnicos()
	_enviar(
		destino,
		chamado,
		"Novo chamado" + (" atribuído a você" if chamado.responsavel else " sem responsável"),
		f"<p><b>{escape_html(chamado.nome_solicitante or chamado.email_solicitante or '')}</b>"
		f"{' · ' + escape_html(chamado.departamento) if chamado.departamento else ''}</p>"
		f"<div style='background:#f8fafc;border-radius:10px;padding:12px 14px'>{chamado.descricao or '(sem descrição)'}</div>",
	)


def chamado_atribuido(chamado):
	_enviar([_email_de(chamado.responsavel)], chamado, "Chamado atribuído a você", "<p>Você é o novo responsável por este chamado.</p>")


def nova_resposta(chamado, interacao):
	if interacao.de_tecnico:
		_enviar(
			[chamado.email_solicitante],
			chamado,
			"Nova resposta da TI",
			f"<p><b>{escape_html(interacao.autor_nome or '')}</b> respondeu:</p>"
			f"<div style='background:#f8fafc;border-radius:10px;padding:12px 14px'>{interacao.mensagem or ''}</div>",
			"Ver e responder",
		)
	else:
		destino = [_email_de(chamado.responsavel)] if chamado.responsavel else _tecnicos()
		_enviar(
			destino,
			chamado,
			"Resposta do colaborador",
			f"<p><b>{escape_html(interacao.autor_nome or '')}</b> escreveu:</p>"
			f"<div style='background:#f8fafc;border-radius:10px;padding:12px 14px'>{interacao.mensagem or ''}</div>",
		)


def chamado_resolvido(chamado):
	avaliar = config().enviar_pesquisa_satisfacao
	solucao = ""
	if chamado.solucao:
		solucao = '<p><b>Solução:</b></p><div style="background:#f8fafc;border-radius:10px;padding:12px 14px">' + chamado.solucao + "</div>"
	convite = "Conte para a gente como foi: leva 5 segundos. " if avaliar else ""
	_enviar(
		[chamado.email_solicitante],
		chamado,
		"Chamado resolvido",
		"<p>A TI concluiu o atendimento.</p>" + solucao + f"<p>{convite}Se o problema continuar, é só reabrir o chamado.</p>",
		"Avaliar atendimento" if avaliar else "Abrir chamado",
		link(chamado, "?avaliar=1") if avaliar else None,
	)


def alerta_sla(chamado, situacao, qual):
	destino = [_email_de(chamado.responsavel)] if chamado.responsavel else _tecnicos()
	prazo = chamado.prazo_resposta if qual == "resposta" else chamado.prazo_resolucao
	texto = "está perto de vencer" if situacao == "Em Risco" else "venceu"
	_enviar(
		destino,
		chamado,
		f"SLA {situacao.lower()}",
		f"<p>O prazo de <b>{'primeira resposta' if qual == 'resposta' else 'resolução'}</b> {texto}: "
		f"<b>{format_datetime(prazo, 'dd/MM/yyyy HH:mm')}</b>.</p>",
	)
