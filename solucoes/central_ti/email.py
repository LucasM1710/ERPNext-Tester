"""E-mails recebidos pela conta da TI (Email Account com "Append To" = Chamado TI).

- E-mail novo: o Frappe cria o chamado só com assunto e remetente; aqui o corpo vira a descrição.
- Resposta (mesmo assunto com "#CH-xxxxx" ou resposta ao nosso e-mail): vira mensagem na conversa
  e, se veio do colaborador, devolve o chamado para atendimento.
"""

import frappe
from frappe.utils import strip_html_tags


def ao_receber_email(doc, method=None):
	if doc.reference_doctype != "Chamado TI" or not doc.reference_name:
		return
	if doc.communication_type != "Communication" or doc.sent_or_received != "Received":
		return
	try:
		_processar(doc)
	except Exception:
		frappe.log_error(title=f"Central de TI: e-mail recebido para {doc.reference_name}")


def _processar(comunicacao):
	from solucoes.central_ti.doctype.chamado_ti.chamado_ti import tecnicos_ativos

	chamado = frappe.get_doc("Chamado TI", comunicacao.reference_name)
	anexos = _ligar_anexos(comunicacao, chamado.name)
	conteudo = comunicacao.content or ""

	if not chamado.descricao and not frappe.db.exists("Interacao Chamado TI", {"chamado": chamado.name, "tipo": "Resposta"}):
		# primeiro e-mail: é a abertura do chamado
		chamado.descricao = conteudo
		chamado.canal = "E-mail"
		chamado.flags.ignore_permissions = True
		chamado.save()
		return

	remetente = comunicacao.sender
	usuario = frappe.db.get_value("User", {"email": remetente}) or frappe.db.get_value("User", {"name": remetente})
	de_tecnico = bool(usuario and usuario in tecnicos_ativos())
	from solucoes.central_ti.servico import registrar_resposta

	registrar_resposta(
		chamado,
		mensagem=conteudo if strip_html_tags(conteudo).strip() else "(e-mail sem texto)",
		autor=usuario,
		autor_nome=comunicacao.sender_full_name or remetente,
		de_tecnico=de_tecnico,
		via="E-mail",
		anexos=anexos,
	)


def _ligar_anexos(comunicacao, chamado):
	urls = []
	for f in frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Communication", "attached_to_name": comunicacao.name},
		fields=["file_name", "file_url", "is_private"],
	):
		if not frappe.db.exists("File", {"attached_to_doctype": "Chamado TI", "attached_to_name": chamado, "file_url": f.file_url}):
			frappe.get_doc(
				{
					"doctype": "File",
					"file_name": f.file_name,
					"file_url": f.file_url,
					"is_private": f.is_private,
					"attached_to_doctype": "Chamado TI",
					"attached_to_name": chamado,
				}
			).insert(ignore_permissions=True)
		urls.append(f.file_url)
	return urls
