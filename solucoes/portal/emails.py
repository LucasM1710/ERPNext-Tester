"""E-mails do portal com a marca da ER (modelos em templates/emails/).

Remetente: a conta de e-mail `portal@eranalitica.com.br` quando ela existir no ERP com saída
habilitada; sem ela, a conta padrão de saída do ERP. O logo vai embutido (não depende do
servidor estar acessível pela internet).

Só usuários do portal recebem estes e-mails; os modelos globais do Frappe (usuários internos)
não são alterados.
"""

import frappe
from frappe import _
from frappe.utils import get_url

REMETENTE_PORTAL = "portal@eranalitica.com.br"
PORTAL = "/consulta"

DESCRICAO_PERFIL = {
	"Gestor": "vê todo o parque, os relatórios e organiza distritos e equipe.",
	"Líder": "vê e acompanha os equipamentos dos distritos sob sua responsabilidade.",
	"Usuário": "vê os equipamentos sob sua responsabilidade.",
}


def remetente():
	"""portal@ se a conta existir e enviar; senão None (o Frappe usa a conta padrão de saída)."""
	conta = frappe.db.get_value("Email Account", {"email_id": REMETENTE_PORTAL, "enable_outgoing": 1}, "email_id")
	return conta or None


def montar(modelo, **ctx):
	ctx.setdefault("portal", get_url(PORTAL))
	conteudo = frappe.render_template(f"solucoes/templates/emails/{modelo}.html", ctx)
	return frappe.render_template("solucoes/templates/emails/base.html", {**ctx, "conteudo": conteudo})


def enviar(destinatarios, assunto, modelo, sender=None, agora=False, **ctx) -> bool:
	"""Envia (ou põe na fila). Uma falha de e-mail nunca impede o cadastro que a disparou:
	vira aviso na tela e registro no Error Log."""
	destinatarios = destinatarios if isinstance(destinatarios, list) else [destinatarios]
	try:
		frappe.sendmail(
			recipients=destinatarios,
			sender=sender or remetente(),
			subject=assunto,
			message=montar(modelo, **ctx),
			now=agora,
			delayed=not agora,
		)
		return True
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"Portal: e-mail '{modelo}' não enviado")
		frappe.msgprint(
			_("O acesso foi salvo, mas o e-mail ({0}) para {1} não pôde ser enviado. Confira a conta de e-mail de saída.").format(
				modelo.replace("_", " "), ", ".join(destinatarios)
			),
			indicator="orange",
			alert=True,
		)
		return False


def _contexto_usuario(usuario, cliente=None, perfil=None):
	return {
		"email": usuario,
		"nome": (frappe.utils.get_fullname(usuario) or "").split(" ")[0] if frappe.db.exists("User", usuario) else "",
		"cliente": frappe.db.get_value("Customer", cliente, "customer_name") if cliente else None,
		"perfil": perfil,
		"descricao_perfil": DESCRICAO_PERFIL.get(perfil, ""),
	}


def enviar_convite(usuario, cliente=None, perfil=None):
	"""Link para o usuário criar a senha (substitui o e-mail de boas-vindas padrão do Frappe)."""
	link = frappe.get_doc("User", usuario).reset_password(send_email=False)
	enviar(usuario, _("Seu acesso ao Portal do Cliente — ER Analítica"), "convite", link=link, **_contexto_usuario(usuario, cliente, perfil))


def enviar_acesso_liberado(usuario, cliente=None, perfil=None):
	"""Aviso de acesso criado com senha inicial (a senha nunca vai por e-mail)."""
	enviar(usuario, _("Seu acesso ao Portal do Cliente está pronto"), "acesso_liberado", **_contexto_usuario(usuario, cliente, perfil))


def enviar_recuperacao(usuario):
	link = frappe.get_doc("User", usuario).reset_password(send_email=False)
	enviar(usuario, _("Redefinir sua senha — Portal do Cliente"), "recuperar_senha", link=link, **_contexto_usuario(usuario))
