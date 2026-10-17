"""Quem é o usuário e o que ele pode ver/fazer no portal.

O resultado é um `Escopo`: a lista de clientes visíveis (é uma `list`, então os
adapters podem usá-la diretamente em filtros) acrescida de perfil e distritos.

Controle por distritos é OPCIONAL por cliente (Customer.usa_controle_distritos):
- desativado: todo usuário do cliente vê tudo (comportamento padrão do portal);
- ativado: o acesso vem de "Usuario Portal Cliente" — Gestor vê todos os distritos,
  Responsável/Consulta só os distritos atribuídos.
"""

import frappe
from frappe import _

PAPEIS_INTERNOS = ("System Manager", "Sales Manager", "Sales User")
GESTOR, RESPONSAVEL, CONSULTA = "Gestor", "Responsável", "Consulta"


class Escopo(list):
	def __init__(self, clientes, perfis=None, distritos=None, usuario=None):
		super().__init__(clientes)
		self.perfis: dict[str, str] = perfis or {}
		# cliente -> set de distritos permitidos | None (= todos)
		self.distritos: dict[str, set[str] | None] = distritos or {}
		self.usuario = usuario

	@property
	def restrito(self) -> bool:
		return any(self.distritos.get(c) is not None for c in self)

	def perfil(self, cliente) -> str:
		return self.perfis.get(cliente, GESTOR)

	def distritos_de(self, cliente) -> set[str] | None:
		return self.distritos.get(cliente)

	def pode_ver(self, cliente, distrito=None) -> bool:
		if cliente not in self:
			return False
		permitidos = self.distritos.get(cliente)
		return permitidos is None or distrito in permitidos

	def pode_editar(self, cliente, distrito=None) -> bool:
		return self.pode_ver(cliente, distrito) and self.perfil(cliente) != CONSULTA

	def eh_gestor(self, cliente) -> bool:
		return cliente in self and self.perfil(cliente) == GESTOR

	def restringir(self, cliente=None, distrito=None) -> "Escopo":
		"""Novo escopo limitado a um cliente e/ou distrito (que precisam estar dentro deste)."""
		clientes = list(self)
		if cliente:
			if cliente not in self:
				raise frappe.PermissionError(_("Você não tem acesso a este cliente."))
			clientes = [cliente]
		distritos = {c: self.distritos.get(c) for c in clientes}
		if distrito:
			dono = frappe.db.get_value("Distrito Cliente", distrito, "cliente")
			if dono not in clientes or not self.pode_ver(dono, distrito):
				raise frappe.PermissionError(_("Você não tem acesso a este distrito."))
			clientes, distritos = [dono], {dono: {distrito}}
		return Escopo(clientes, {c: self.perfil(c) for c in clientes}, distritos, self.usuario)


def is_usuario_interno(user: str | None = None) -> bool:
	return bool(set(frappe.get_roles(user)) & set(PAPEIS_INTERNOS))


def clientes_com_distritos(clientes) -> set[str]:
	if not clientes:
		return set()
	return set(
		frappe.get_all("Customer", filters={"name": ["in", list(clientes)], "usa_controle_distritos": 1}, pluck="name")
	)


def get_clientes_do_usuario(user: str | None = None) -> list[str]:
	"""Clientes vinculados via Customer > Portal Users, Contact > Links ou Usuario Portal Cliente."""
	user = user or frappe.session.user
	via_portal = frappe.get_all("Portal User", filters={"user": user, "parenttype": "Customer"}, pluck="parent")

	contatos = frappe.get_all("Contact", filters={"user": user}, pluck="name")
	via_contato = (
		frappe.get_all(
			"Dynamic Link",
			filters={"parent": ["in", contatos], "parenttype": "Contact", "link_doctype": "Customer"},
			pluck="link_name",
		)
		if contatos
		else []
	)
	acessos = frappe.get_all("Usuario Portal Cliente", filters={"usuario": user}, fields=["cliente", "ativo"])
	ativos = {a.cliente for a in acessos if a.ativo}
	bloqueados = {a.cliente for a in acessos if not a.ativo}
	return sorted((set(via_portal) | set(via_contato) | ativos) - bloqueados)


def get_escopo(user: str | None = None) -> Escopo:
	"""Escopo completo do usuário (sem filtros da requisição)."""
	user = user or frappe.session.user
	if is_usuario_interno(user):
		clientes = get_clientes_do_usuario(user) or frappe.get_all("Customer", filters={"disabled": 0}, pluck="name")
		return Escopo(clientes, usuario=user)

	clientes = get_clientes_do_usuario(user)
	com_distritos = clientes_com_distritos(clientes)
	perfis, distritos = {}, {}
	for acesso in frappe.get_all(
		"Usuario Portal Cliente",
		filters={"usuario": user, "ativo": 1, "cliente": ["in", clientes or [""]]},
		fields=["name", "cliente", "perfil"],
	):
		perfis[acesso.cliente] = acesso.perfil
		if acesso.cliente in com_distritos and acesso.perfil != GESTOR:
			distritos[acesso.cliente] = set(
				frappe.get_all("Usuario Portal Distrito", filters={"parent": acesso.name}, pluck="distrito")
			)
	# cliente com distritos e usuário sem cadastro de acesso => legado (Portal User/Contato): gestor
	return Escopo(clientes, perfis, distritos, user)


def get_contato_do_usuario(user: str | None = None) -> str | None:
	return frappe.db.get_value("Contact", {"user": user or frappe.session.user}, "name")


def resolver_clientes(cliente: str | None = None) -> Escopo:
	"""Escopo desta requisição. Aceita os filtros `cliente` e `distrito` (lido do form_dict).

	- Usuário do portal: seus clientes/distritos (ou o recorte pedido, se permitido).
	- Usuário interno: qualquer cliente informando `cliente` (útil para suporte).
	"""
	if frappe.session.user == "Guest":
		raise frappe.PermissionError(_("Faça login para acessar o portal."))

	distrito = frappe.form_dict.get("distrito") or None
	if is_usuario_interno() and cliente and cliente not in (escopo := get_escopo()):
		if not frappe.db.exists("Customer", cliente):
			raise frappe.DoesNotExistError(_("Cliente não encontrado."))
		return Escopo([cliente], usuario=frappe.session.user).restringir(distrito=distrito)

	escopo = get_escopo()
	if not escopo:
		raise frappe.PermissionError(_("Seu usuário não está vinculado a nenhum cliente."))
	return escopo.restringir(cliente, distrito)


def resolver_escopo_unico(cliente: str | None = None) -> Escopo:
	"""Para criação de registros: escopo de exatamente um cliente, com perfil que possa editar."""
	escopo = resolver_clientes(cliente)
	if len(escopo) != 1:
		frappe.throw(_("Selecione o cliente para esta operação."))
	if escopo.perfil(escopo[0]) == CONSULTA:
		raise frappe.PermissionError(_("Seu perfil é somente consulta."))
	return escopo
