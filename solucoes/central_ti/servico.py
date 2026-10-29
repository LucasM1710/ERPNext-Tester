"""Regras de negócio da conversa do chamado — usadas pela página /ti e pelos e-mails recebidos."""

import frappe

from solucoes.central_ti import notificacoes


def registrar_resposta(chamado, mensagem, autor=None, autor_nome=None, de_tecnico=False, via="Portal", anexos=None, interna=False):
	"""Mensagem na conversa + efeitos no chamado (1ª resposta, status) + e-mail para o outro lado."""
	interacao = frappe.get_doc(
		{
			"doctype": "Interacao Chamado TI",
			"chamado": chamado.name,
			"tipo": "Nota Interna" if interna else "Resposta",
			"via": via,
			"autor": autor,
			"autor_nome": autor_nome or (frappe.utils.get_fullname(autor) if autor else ""),
			"de_tecnico": int(bool(de_tecnico)),
			"mensagem": mensagem,
			"anexos": "\n".join(anexos or []),
		}
	).insert(ignore_permissions=True)

	if interna:
		return interacao

	if de_tecnico:
		chamado.registrar_primeira_resposta()
		if chamado.status == "Aberto":
			chamado.status = "Em Atendimento"
		if not chamado.responsavel and autor:
			chamado.responsavel = autor
	elif chamado.status in ("Aguardando Usuário", "Resolvido"):
		# o colaborador respondeu: volta para a TI (reabre, se estava resolvido)
		chamado.status = "Em Atendimento"
	chamado.flags.ignore_permissions = True
	chamado.save()
	notificacoes.nova_resposta(chamado, interacao)
	return interacao
