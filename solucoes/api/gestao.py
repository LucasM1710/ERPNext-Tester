"""Autoatendimento do GESTOR do cliente (controle por distritos): distritos e usuários.

Disponível só para clientes com Customer.usa_controle_distritos e usuários com perfil Gestor
(ou usuários internos). Distritos e acessos vivem neste app, independente do adapter.
"""

import json

import frappe
from frappe import _

from solucoes.portal import auditoria
from solucoes.portal.adapters import get_adapter
from solucoes.portal.sessao import GESTOR, PERFIS, USUARIO, resolver_clientes, usa_distritos


def _cliente_gerenciavel(cliente: str) -> str:
	escopo = resolver_clientes(cliente)
	if len(escopo) != 1 or not escopo.eh_gestor(escopo[0]):
		raise frappe.PermissionError(_("Apenas gestores podem administrar distritos e usuários."))
	if not usa_distritos(escopo[0]):
		frappe.throw(_("O controle por distritos não está ativado para este cliente."))
	return escopo[0]


def _lista(valor):
	if isinstance(valor, str):
		return json.loads(valor) if valor else []
	return valor or []


def _ranking_por_distrito(adapter, equipamentos):
	"""Números dos cartões de distrito. Na /consulta usam as mesmas faixas da visão
	operacional (status_calibracao), para nenhuma tela divergir da outra."""
	if not any("status_calibracao" in e for e in equipamentos):
		return {r["distrito"]: r for r in adapter.resumo_por_distrito(equipamentos)}
	grupos = {}
	for e in equipamentos:
		if not e.get("distrito"):
			continue
		g = grupos.setdefault(e["distrito"], {"total": 0, "Vencido": 0, "A Vencer": 0, "em_dia": 0, "sem": 0})
		g["total"] += 1
		s = e["status_calibracao"]
		g["Vencido"] += s == "Vencido"
		g["A Vencer"] += s in ("Crítico", "Alerta 60")
		g["em_dia"] += s in ("Calibrado", "Alerta 60", "Agendado")
		g["sem"] += s == "Sem calibração"
	for g in grupos.values():
		base = g["total"] - g["sem"]
		# Sem nenhuma calibração registrada não há o que medir: "—", não 0%.
		g["em_dia_pct"] = round(100 * g["em_dia"] / base, 1) if base else None
	return grupos


# ===================================================================== distritos
@frappe.whitelist()
def distritos(cliente):
	cliente = _cliente_gerenciavel(cliente)
	linhas = frappe.get_all(
		"Distrito Cliente",
		filters={"cliente": cliente},
		fields=["name as id", "nome_distrito as nome", "descricao", "ativo", "responsavel_nome", "responsavel_email", "uf", "cidade"],
		order_by="nome_distrito",
	)
	adapter = get_adapter()
	equipamentos_cliente = adapter.listar_equipamentos([cliente])
	ranking = _ranking_por_distrito(adapter, equipamentos_cliente)
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
	sem_distrito = sum(1 for e in equipamentos_cliente if not e.get("distrito"))
	return {"distritos": linhas, "equipamentos_sem_distrito": sem_distrito}


@frappe.whitelist(methods=["POST"])
def salvar_distrito(
	cliente, nome, id=None, descricao=None, ativo=1, responsavel_nome=None, responsavel_email=None, uf=None, cidade=None
):
	cliente = _cliente_gerenciavel(cliente)
	if id:
		doc = frappe.get_doc("Distrito Cliente", id)
		if doc.cliente != cliente:
			raise frappe.PermissionError
	else:
		doc = frappe.new_doc("Distrito Cliente")
		doc.cliente = cliente
	antes = {k: doc.get(k) for k in ("nome_distrito", "responsavel_nome", "responsavel_email", "uf", "cidade", "ativo")} if id else None
	doc.update(
		{
			"nome_distrito": nome,
			"descricao": descricao,
			"ativo": frappe.utils.cint(ativo),
			"responsavel_nome": responsavel_nome,
			"responsavel_email": (responsavel_email or "").strip().lower() or None,
			"uf": (uf or "").strip().upper()[:2] or None,
			"cidade": cidade,
		}
	)
	doc.save(ignore_permissions=True)
	auditoria.registrar("Edição de distrito" if id else "Cadastro de distrito", cliente, "Distrito Cliente", doc.name, antes=antes,
		depois={k: doc.get(k) for k in ("nome_distrito", "responsavel_nome", "responsavel_email", "uf", "cidade", "ativo")})
	return {"id": doc.name, "nome": doc.nome_distrito}


@frappe.whitelist(methods=["POST"])
def distribuir_equipamentos(cliente, distrito, equipamentos):
	"""Move equipamentos para um distrito (organização inicial ou transferência). Fica no histórico."""
	cliente = _cliente_gerenciavel(cliente)
	if frappe.db.get_value("Distrito Cliente", distrito, "cliente") != cliente:
		raise frappe.PermissionError
	movidos = get_adapter().atribuir_distrito(cliente, distrito, _lista(equipamentos))
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
				# perfil Usuário: equipamentos dos quais é dono (ERP e terceiros)
				"equipamentos": frappe.get_all("Distrito Equipamento", filters={"cliente": cliente, "dono": a.usuario}, pluck="equipamento")
				+ frappe.get_all("Equipamento Cliente", filters={"cliente": cliente, "dono": a.usuario}, pluck="name"),
				"ultimo_acesso": frappe.db.get_value("User", a.usuario, "last_login"),
				"eu": a.usuario == frappe.session.user,
			}
		)
	return saida


@frappe.whitelist(methods=["POST"])
def salvar_usuario(cliente, email, perfil, nome=None, distritos=None, ativo=1, id=None, equipamentos=None):
	"""Convida (cria o usuário do portal) ou atualiza perfil/distritos de um usuário do cliente."""
	cliente = _cliente_gerenciavel(cliente)
	email = (email or "").strip().lower()
	if perfil not in PERFIS:
		frappe.throw(_("Perfil inválido."))
	frappe.utils.validate_email_address(email, throw=True)

	if email == frappe.session.user and (perfil != GESTOR or not frappe.utils.cint(ativo)):
		frappe.throw(_("Você não pode remover o seu próprio acesso de gestor."))

	novo_usuario = not frappe.db.exists("User", email)

	if id:
		acesso = frappe.get_doc("Usuario Portal Cliente", id)
		if acesso.cliente != cliente or acesso.usuario != email:
			raise frappe.PermissionError
	else:
		existente = frappe.db.exists("Usuario Portal Cliente", {"usuario": email, "cliente": cliente})
		acesso = frappe.get_doc("Usuario Portal Cliente", existente) if existente else frappe.new_doc("Usuario Portal Cliente")
		acesso.update({"email": email, "cliente": cliente, "nome_completo": nome})
	acesso.perfil = perfil
	acesso.ativo = frappe.utils.cint(ativo)
	acesso.set("distritos", [{"distrito": d} for d in _lista(distritos)] if perfil != GESTOR else [])
	acesso.save(ignore_permissions=True)
	# Perfil Usuário: equipamentos sob a responsabilidade dele (os únicos que ele vê).
	if perfil == USUARIO or equipamentos is not None:
		get_adapter().definir_donos(cliente, acesso.usuario, _lista(equipamentos) if perfil == USUARIO else [])
	auditoria.registrar(
		"Convite de usuário" if novo_usuario else "Edição de acesso de usuário", cliente, "Usuario Portal Cliente", acesso.name,
		depois={"email": email, "perfil": perfil, "ativo": acesso.ativo, "distritos": _lista(distritos), "equipamentos": _lista(equipamentos)},
	)
	return {"id": acesso.name, "convidado": novo_usuario}
