"""Autoatendimento do GESTOR do cliente (controle por distritos): distritos e usuários.

Disponível só para clientes com Customer.usa_controle_distritos e usuários com perfil Gestor
(ou usuários internos). Distritos e acessos vivem neste app, independente do adapter.
"""

import json

import frappe
from frappe import _

from solucoes.portal.adapters import get_adapter
from solucoes.portal.sessao import CONSULTA, GESTOR, RESPONSAVEL, resolver_clientes

PERFIS = (GESTOR, RESPONSAVEL, CONSULTA)


def _cliente_gerenciavel(cliente: str) -> str:
	escopo = resolver_clientes(cliente)
	if len(escopo) != 1 or not escopo.eh_gestor(escopo[0]):
		raise frappe.PermissionError(_("Apenas gestores podem administrar distritos e usuários."))
	if not frappe.db.get_value("Customer", escopo[0], "usa_controle_distritos"):
		frappe.throw(_("O controle por distritos não está ativado para este cliente."))
	return escopo[0]


def _lista(valor):
	if isinstance(valor, str):
		return json.loads(valor) if valor else []
	return valor or []


# ===================================================================== distritos
@frappe.whitelist()
def distritos(cliente):
	cliente = _cliente_gerenciavel(cliente)
	linhas = frappe.get_all(
		"Distrito Cliente",
		filters={"cliente": cliente},
		fields=["name as id", "nome_distrito as nome", "descricao", "ativo"],
		order_by="nome_distrito",
	)
	ranking = {r["distrito"]: r for r in get_adapter().resumo_por_distrito(get_adapter().listar_equipamentos([cliente]))}
	usuarios = {}
	for acesso in frappe.get_all(
		"Usuario Portal Cliente", filters={"cliente": cliente, "ativo": 1, "perfil": ["!=", GESTOR]}, pluck="name"
	):
		for d in frappe.get_all("Usuario Portal Distrito", filters={"parent": acesso}, pluck="distrito"):
			usuarios[d] = usuarios.get(d, 0) + 1
	for linha in linhas:
		r = ranking.get(linha.id, {})
		linha.update(
			{
				"total": r.get("total", 0),
				"vencidos": r.get("Vencido", 0),
				"a_vencer": r.get("A Vencer", 0),
				"em_dia_pct": r.get("em_dia_pct", 0),
				"usuarios": usuarios.get(linha.id, 0),
			}
		)
	sem_distrito = frappe.db.count("Equipamento Cliente", {"cliente": cliente, "distrito": ["is", "not set"]})
	return {"distritos": linhas, "equipamentos_sem_distrito": sem_distrito}


@frappe.whitelist(methods=["POST"])
def salvar_distrito(cliente, nome, id=None, descricao=None, ativo=1):
	cliente = _cliente_gerenciavel(cliente)
	if id:
		doc = frappe.get_doc("Distrito Cliente", id)
		if doc.cliente != cliente:
			raise frappe.PermissionError
	else:
		doc = frappe.new_doc("Distrito Cliente")
		doc.cliente = cliente
	doc.update({"nome_distrito": nome, "descricao": descricao, "ativo": frappe.utils.cint(ativo)})
	doc.save(ignore_permissions=True)
	return {"id": doc.name, "nome": doc.nome_distrito}


@frappe.whitelist(methods=["POST"])
def distribuir_equipamentos(cliente, distrito, equipamentos):
	"""Move equipamentos para um distrito (organização inicial ou transferência). Fica no histórico."""
	cliente = _cliente_gerenciavel(cliente)
	if frappe.db.get_value("Distrito Cliente", distrito, "cliente") != cliente:
		raise frappe.PermissionError
	movidos = 0
	for id in _lista(equipamentos):
		doc = frappe.get_doc("Equipamento Cliente", id)
		if doc.cliente != cliente:
			raise frappe.PermissionError
		if doc.distrito != distrito:
			doc.distrito = distrito
			doc.save(ignore_permissions=True)
			movidos += 1
	return {"movidos": movidos}


# ===================================================================== usuários
@frappe.whitelist()
def usuarios(cliente):
	cliente = _cliente_gerenciavel(cliente)
	nomes = dict(frappe.get_all("Distrito Cliente", filters={"cliente": cliente}, fields=["name", "nome_distrito"], as_list=True))
	saida = []
	for a in frappe.get_all(
		"Usuario Portal Cliente",
		filters={"cliente": cliente},
		fields=["name", "usuario", "nome_completo", "perfil", "ativo"],
		order_by="perfil, nome_completo",
	):
		ids = frappe.get_all("Usuario Portal Distrito", filters={"parent": a.name}, pluck="distrito")
		saida.append(
			{
				"id": a.name,
				"email": a.usuario,
				"nome": a.nome_completo,
				"perfil": a.perfil,
				"ativo": bool(a.ativo),
				"distritos": [{"id": d, "nome": nomes.get(d, d)} for d in ids],
				"ultimo_acesso": frappe.db.get_value("User", a.usuario, "last_login"),
				"eu": a.usuario == frappe.session.user,
			}
		)
	return saida


@frappe.whitelist(methods=["POST"])
def salvar_usuario(cliente, email, perfil, nome=None, distritos=None, ativo=1, id=None):
	"""Convida (cria o usuário do portal) ou atualiza perfil/distritos de um usuário do cliente."""
	cliente = _cliente_gerenciavel(cliente)
	email = (email or "").strip().lower()
	if perfil not in PERFIS:
		frappe.throw(_("Perfil inválido."))
	frappe.utils.validate_email_address(email, throw=True)

	if email == frappe.session.user and (perfil != GESTOR or not frappe.utils.cint(ativo)):
		frappe.throw(_("Você não pode remover o seu próprio acesso de gestor."))

	novo_usuario = not frappe.db.exists("User", email)
	if novo_usuario:
		partes = (nome or email.split("@")[0]).strip().split(" ", 1)
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": partes[0],
				"last_name": partes[1] if len(partes) > 1 else "",
				"user_type": "Website User",
				"send_welcome_email": 1,
				"roles": [{"role": "Customer"}],
			}
		).insert(ignore_permissions=True)
	elif frappe.db.get_value("User", email, "user_type") == "System User" and not frappe.db.exists(
		"Usuario Portal Cliente", {"usuario": email, "cliente": cliente}
	):
		frappe.throw(_("Este e-mail pertence a um usuário interno do sistema."))

	if id:
		acesso = frappe.get_doc("Usuario Portal Cliente", id)
		if acesso.cliente != cliente or acesso.usuario != email:
			raise frappe.PermissionError
	else:
		existente = frappe.db.exists("Usuario Portal Cliente", {"usuario": email, "cliente": cliente})
		acesso = frappe.get_doc("Usuario Portal Cliente", existente) if existente else frappe.new_doc("Usuario Portal Cliente")
		acesso.update({"usuario": email, "cliente": cliente})
	acesso.perfil = perfil
	acesso.ativo = frappe.utils.cint(ativo)
	acesso.set("distritos", [{"distrito": d} for d in _lista(distritos)] if perfil != GESTOR else [])
	acesso.save(ignore_permissions=True)
	return {"id": acesso.name, "convidado": novo_usuario}
