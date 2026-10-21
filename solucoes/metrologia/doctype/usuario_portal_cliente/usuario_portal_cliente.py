import frappe
from frappe import _
from frappe.model.document import Document

from solucoes.portal.sessao import usa_distritos


class UsuarioPortalCliente(Document):
	def validate(self):
		self.garantir_usuario()
		duplicado = frappe.db.exists(
			"Usuario Portal Cliente",
			{"usuario": self.usuario, "cliente": self.cliente, "name": ["!=", self.name]},
		)
		if duplicado:
			frappe.throw(_("O usuário {0} já tem acesso configurado para {1}.").format(self.usuario, self.cliente))

		if self.perfil != "Líder":
			# Gestor vê todos os distritos; Usuário vê os equipamentos dos quais é dono.
			self.distritos = []
		elif usa_distritos(self.cliente) and not self.distritos:
			frappe.throw(
				_("Este cliente usa controle por distritos: informe ao menos um distrito para o perfil {0} (o Gestor vê todos).").format(
					self.perfil
				)
			)
		for linha in self.distritos:
			if frappe.db.get_value("Distrito Cliente", linha.distrito, "cliente") != self.cliente:
				frappe.throw(_("O distrito {0} não pertence ao cliente {1}.").format(linha.distrito, self.cliente))
		self.validar_historico()

	def validar_historico(self):
		"""Histórico de atendimento: só Gestor/Líder e só oportunidades escolhidas deste cliente."""
		if self.perfil == "Usuário":
			self.ver_historico = 0
		if not self.ver_historico:
			self.oportunidades = []
			return
		if not self.oportunidades:
			frappe.throw(_("Escolha ao menos uma oportunidade para o histórico de atendimento."))
		for linha in self.oportunidades:
			origem = frappe.db.get_value("Opportunity", linha.oportunidade, ["opportunity_from", "party_name"])
			if not origem or origem[0] != "Customer" or origem[1] != self.cliente:
				frappe.throw(_("A oportunidade {0} não é do cliente {1}.").format(linha.oportunidade, self.cliente))

	def on_update(self):
		vincular_contato(self.usuario, self.cliente)

	def garantir_usuario(self):
		"""O usuário "nasce" aqui: cadastrado pela empresa no sistema ou convidado pelo gestor no portal."""
		self.email = (self.email or self.usuario or "").strip().lower()
		if not self.email:
			frappe.throw(_("Informe o e-mail do usuário."))
		frappe.utils.validate_email_address(self.email, throw=True)
		if self.usuario and self.usuario != self.email:
			frappe.throw(_("O e-mail não pode ser trocado; cadastre um novo acesso."))
		self.usuario = criar_usuario_portal(self.email, self.nome_completo, cliente=self.cliente, perfil=self.perfil)
		if not self.nome_completo:
			self.nome_completo = frappe.db.get_value("User", self.usuario, "full_name")


def criar_usuario_portal(email, nome=None, boas_vindas=True, cliente=None, perfil=None):
	"""Usuário de site (sem acesso ao sistema) com o papel Customer. Já existindo, reaproveita."""
	if frappe.db.exists("User", email):
		if frappe.db.get_value("User", email, "user_type") == "System User" and not frappe.db.exists(
			"Usuario Portal Cliente", {"usuario": email}
		):
			# Usuário interno da empresa: entra no portal pelo perfil interno, não por convite.
			frappe.throw(_("Este e-mail pertence a um usuário interno do sistema."))
		return email
	partes = (nome or email.split("@")[0]).strip().split(" ", 1)
	frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": partes[0],
			"last_name": partes[1] if len(partes) > 1 else "",
			"user_type": "Website User",
			# o convite é o e-mail do portal (com a marca da ER), não o padrão do Frappe
			"send_welcome_email": 0,
			"roles": [{"role": "Customer"}],
		}
	).insert(ignore_permissions=True)
	if boas_vindas:
		from solucoes.portal.emails import enviar_convite

		enviar_convite(email, cliente, perfil)
	return email


def vincular_contato(usuario, cliente):
	"""Liga o contato do usuário ao cliente.

	Sem isso, no primeiro login o ERPNext cria um Cliente novo para o usuário de site
	(Portal Settings > papel padrão "Customer"), porque não acha contato ligado a cliente.
	"""
	contatos = set(frappe.get_all("Contact", filters={"user": usuario}, pluck="name")) | set(
		frappe.get_all("Contact", filters={"email_id": usuario}, pluck="name")
	)
	if not contatos:
		nome = frappe.utils.get_fullname(usuario) or usuario
		contato = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": nome,
				"user": usuario,
				"email_ids": [{"email_id": usuario, "is_primary": 1}],
			}
		)
		contato.flags.ignore_mandatory = True
		contato.insert(ignore_permissions=True)
		contatos = {contato.name}
	for nome in contatos:
		contato = frappe.get_doc("Contact", nome)
		if not any(l.link_doctype == "Customer" and l.link_name == cliente for l in contato.links):
			contato.append("links", {"link_doctype": "Customer", "link_name": cliente})
			contato.flags.ignore_mandatory = True
			contato.save(ignore_permissions=True)
