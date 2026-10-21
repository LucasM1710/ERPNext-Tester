"""Central do portal: a triagem do administrador (ER) para amarrar, num lugar só,
cliente → contatos → portal → distritos → usuários → equipamentos → OS.

Só para usuários internos. Cada lista já vem filtrada pelo cliente escolhido.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint

from solucoes.metrologia.doctype.usuario_portal_cliente.usuario_portal_cliente import criar_usuario_portal
from solucoes.portal import auditoria, historico
from solucoes.portal.adapters.er import EQP, EQP_CLIENTE, MAPA, AdapterER
from solucoes.portal.sessao import LIDER, PERFIS, USUARIO, Escopo, is_usuario_interno

OSI, OSE = "Ordem Servico Interna", "Ordem Servico Externa"


def _interno():
	if not is_usuario_interno():
		raise frappe.PermissionError(_("Apenas usuários da ER Analítica acessam a central do portal."))


def _lista(valor):
	if isinstance(valor, str):
		return json.loads(valor) if valor else []
	return valor or []


def _norm(valor):
	return "".join(str(valor or "").upper().split())


# ===================================================================== consulta
@frappe.whitelist()
def clientes(busca=None):
	_interno()
	f = {"disabled": 0}
	or_f = {"name": ["like", f"%{busca}%"], "customer_name": ["like", f"%{busca}%"]} if busca else None
	linhas = frappe.get_all("Customer", filters=f, or_filters=or_f, fields=["name", "customer_name"], order_by="customer_name", limit=30)
	com_portal = set(frappe.get_all("Cliente Portal", filters={"cliente": ["in", [c.name for c in linhas] or [""]]}, pluck="cliente"))
	for c in linhas:
		c.portal = c.name in com_portal
	return linhas


@frappe.whitelist()
def resumo(cliente):
	"""Tudo o que está amarrado (ou falta amarrar) para um cliente."""
	_interno()
	if not frappe.db.exists("Customer", cliente):
		raise frappe.DoesNotExistError(_("Cliente não encontrado."))
	portal = frappe.db.get_value("Cliente Portal", cliente, ["name", "usa_controle_distritos"], as_dict=True)

	contatos = []
	for nome in frappe.get_all("Dynamic Link", filters={"parenttype": "Contact", "link_doctype": "Customer", "link_name": cliente}, pluck="parent"):
		c = frappe.db.get_value("Contact", nome, ["name", "first_name", "last_name", "email_id", "mobile_no", "phone", "user"], as_dict=True)
		if c:
			c.nome = " ".join(filter(None, [c.first_name, c.last_name]))
			contatos.append(c)

	distritos = frappe.get_all(
		"Distrito Cliente",
		filters={"cliente": cliente},
		fields=["name as id", "nome_distrito as nome", "responsavel_nome", "responsavel_email", "uf", "cidade", "ativo"],
		order_by="nome_distrito",
	)

	usuarios = []
	for a in frappe.get_all("Usuario Portal Cliente", filters={"cliente": cliente}, fields=["name", "usuario", "nome_completo", "perfil", "ativo", "ver_historico"], order_by="perfil, nome_completo"):
		a.distritos = frappe.get_all("Usuario Portal Distrito", filters={"parent": a.name}, pluck="distrito")
		a.oportunidades = frappe.get_all("Usuario Portal Oportunidade", filters={"parent": a.name, "parenttype": "Usuario Portal Cliente"}, pluck="oportunidade")
		a.ultimo_acesso = frappe.db.get_value("User", a.usuario, "last_login")
		usuarios.append(a)

	frappe.form_dict.portal = "consulta"
	equipamentos = AdapterER()._equipamentos(Escopo([cliente], usuario=frappe.session.user))
	equipamentos.sort(key=lambda e: (e["origem"] != "laboratorio", e.get("tag") or ""))
	n_os = {}
	for dt in (OSI, OSE):
		for o in frappe.get_all(dt, filters={"customer": cliente, "informe_numero_serie": ["is", "set"]}, fields=["informe_numero_serie"]):
			n_os[o.informe_numero_serie] = n_os.get(o.informe_numero_serie, 0) + 1
	for e in equipamentos:
		e["qtd_os"] = n_os.get(e["id"], 0)

	# OS do cliente sem o equipamento ligado: não entram no histórico nem na situação do portal.
	por_serie = {_norm(e["numero_serie"]): e for e in equipamentos if e["origem"] == "laboratorio" and e.get("numero_serie")}
	por_tag = {_norm(e["tag"]): e for e in equipamentos if e["origem"] == "laboratorio" and e.get("tag")}
	sem_vinculo = []
	for dt in (OSI, OSE):
		for o in frappe.get_all(
			dt,
			filters={"customer": cliente, "informe_numero_serie": ["is", "not set"]},
			fields=["name", "status_order_service", "serie_number", "equipment_tag", "equipment_description", "creation"],
			order_by="creation desc",
			limit=200,
		):
			sugestao = por_serie.get(_norm(o.serie_number)) or por_tag.get(_norm(o.equipment_tag))
			sem_vinculo.append(
				{
					"doctype": dt,
					"os": o.name,
					"tipo": "Interna" if dt == OSI else "Externa",
					"status": o.status_order_service,
					"serie": o.serie_number,
					"tag": o.equipment_tag,
					"descricao": o.equipment_description,
					"sugestao": {"id": sugestao["id"], "tag": sugestao["tag"], "descricao": sugestao["descricao"]} if sugestao else None,
				}
			)
	sem_certificado = []
	for dt in (OSI, OSE):
		for o in frappe.get_all(
			dt,
			filters={"customer": cliente, "status_order_service": "Encerrada", "informe_numero_serie": ["is", "set"], "anexo_certificado": ["is", "not set"]},
			fields=["name", "informe_numero_serie", "equipment_tag", "data_cal"],
			limit=200,
		):
			sem_certificado.append({"doctype": dt, "os": o.name, "equipamento": o.informe_numero_serie, "tag": o.equipment_tag, "data_cal": str(o.data_cal or "")})

	usa_distritos = bool(portal and portal.usa_controle_distritos)
	enderecos = [
		frappe.db.get_value("Address", nome, ["name", "address_title", "address_type", "city", "state", "address_line1"], as_dict=True)
		for nome in frappe.get_all("Dynamic Link", filters={"parenttype": "Address", "link_doctype": "Customer", "link_name": cliente}, pluck="parent")
	]
	return {
		"cliente": {"id": cliente, "nome": frappe.db.get_value("Customer", cliente, "customer_name")},
		"portal": {"liberado": bool(portal), "usa_distritos": usa_distritos},
		"contatos": contatos,
		"enderecos": [e for e in enderecos if e],
		"distritos": distritos,
		"usuarios": usuarios,
		"equipamentos": equipamentos,
		"os_sem_vinculo": sem_vinculo,
		"os_sem_certificado": sem_certificado,
		# para o histórico de atendimento (escolhidas por acesso)
		"oportunidades": historico.oportunidades_do_cliente(cliente),
		"pendencias": {
			"contatos": 0 if contatos else 1,
			"portal": 0 if portal else 1,
			"distritos": (1 if usa_distritos and not distritos else 0) + sum(1 for d in distritos if not d.responsavel_nome),
			"usuarios": 0 if any(u.perfil == "Gestor" and u.ativo for u in usuarios) else 1,
			"equipamentos": (sum(1 for e in equipamentos if not e.get("distrito")) if usa_distritos else 0)
			+ (0 if equipamentos else 1),
			"os": len(sem_vinculo) + len(sem_certificado),
		},
		"perfis": PERFIS,
	}


# ===================================================================== ações
@frappe.whitelist(methods=["POST"])
def liberar(cliente, usa_distritos=0):
	_interno()
	doc = frappe.get_doc("Cliente Portal", cliente) if frappe.db.exists("Cliente Portal", cliente) else frappe.new_doc("Cliente Portal")
	doc.cliente = cliente
	doc.usa_controle_distritos = cint(usa_distritos)
	doc.save(ignore_permissions=True)
	auditoria.registrar("Portal liberado/configurado", cliente, "Cliente Portal", cliente, depois={"usa_controle_distritos": doc.usa_controle_distritos})
	return True


@frappe.whitelist(methods=["POST"])
def distritos_dos_enderecos(cliente):
	"""Um distrito para cada endereço do cliente (nome do endereço, cidade e UF). Não duplica."""
	_interno()
	existentes = {(n or "").strip().lower() for n in frappe.get_all("Distrito Cliente", filters={"cliente": cliente}, pluck="nome_distrito")}
	criados = []
	for nome in frappe.get_all("Dynamic Link", filters={"parenttype": "Address", "link_doctype": "Customer", "link_name": cliente}, pluck="parent"):
		e = frappe.db.get_value("Address", nome, ["address_title", "city", "state"], as_dict=True)
		titulo = (e.address_title or e.city or nome).strip()
		if titulo.lower() in existentes:
			continue
		criados.append(salvar_distrito(cliente, titulo, uf=e.state, cidade=e.city))
		existentes.add(titulo.lower())
	return criados


@frappe.whitelist(methods=["POST"])
def salvar_distrito(cliente, nome, id=None, responsavel_nome=None, responsavel_email=None, uf=None, cidade=None, ativo=1):
	_interno()
	doc = frappe.get_doc("Distrito Cliente", id) if id else frappe.new_doc("Distrito Cliente")
	if id and doc.cliente != cliente:
		raise frappe.PermissionError
	doc.update(
		{
			"cliente": cliente,
			"nome_distrito": nome,
			"responsavel_nome": responsavel_nome,
			"responsavel_email": (responsavel_email or "").strip().lower() or None,
			"uf": (uf or "").strip().upper()[:2] or None,
			"cidade": cidade,
			"ativo": cint(ativo),
		}
	)
	doc.save(ignore_permissions=True)
	auditoria.registrar("Distrito (central)", cliente, "Distrito Cliente", doc.name, depois=doc.as_dict(no_default_fields=True))
	return doc.name


@frappe.whitelist(methods=["POST"])
def salvar_usuario(cliente, email, perfil, nome=None, distritos=None, equipamentos=None, senha=None, ativo=1, id=None, ver_historico=0, oportunidades=None):
	"""Cria/atualiza o acesso. Distritos (Líder), equipamentos (Usuário) e oportunidades do
	histórico de atendimento (Gestor/Líder) só deste cliente."""
	_interno()
	if perfil not in PERFIS:
		frappe.throw(_("Perfil inválido."))
	if not frappe.db.exists("Cliente Portal", cliente):
		# Primeiro acesso do cliente: o portal é liberado junto (distritos podem ser ligados depois).
		liberar(cliente, 1 if frappe.db.count("Distrito Cliente", {"cliente": cliente}) else 0)
	email = (email or "").strip().lower()
	acesso = frappe.get_doc("Usuario Portal Cliente", id) if id else frappe.new_doc("Usuario Portal Cliente")
	if id and acesso.cliente != cliente:
		raise frappe.PermissionError
	distritos = [d for d in _lista(distritos) if frappe.db.get_value("Distrito Cliente", d, "cliente") == cliente]
	novo = not frappe.db.exists("User", email)
	if senha and not novo and frappe.db.get_value("User", email, "user_type") != "Website User":
		frappe.throw(_("A senha só pode ser definida aqui para usuários do portal."))
	if novo and senha:
		# Com senha definida aqui, não precisa do e-mail de boas-vindas.
		criar_usuario_portal(email, nome, boas_vindas=False)
	acesso.update({"email": email, "cliente": cliente, "perfil": perfil, "nome_completo": nome, "ativo": cint(ativo)})
	acesso.set("distritos", [{"distrito": d} for d in distritos] if perfil == LIDER else [])
	acesso.ver_historico = cint(ver_historico) if perfil != USUARIO else 0
	acesso.set("oportunidades", [{"oportunidade": o} for o in _lista(oportunidades)] if acesso.ver_historico else [])
	acesso.save(ignore_permissions=True)
	if senha:
		from frappe.utils.password import update_password

		update_password(acesso.usuario, senha)
		if novo:
			# Avisa que o acesso existe e onde entrar (a senha nunca vai por e-mail).
			from solucoes.portal.emails import enviar_acesso_liberado

			enviar_acesso_liberado(acesso.usuario, cliente, perfil)
	if perfil == USUARIO or equipamentos is not None:
		frappe.form_dict.portal = "consulta"
		AdapterER().definir_donos(cliente, acesso.usuario, _lista(equipamentos) if perfil == USUARIO else [])
	auditoria.registrar(
		"Usuário (central)", cliente, "Usuario Portal Cliente", acesso.name,
		depois={
			"email": email, "perfil": perfil, "distritos": distritos, "equipamentos": _lista(equipamentos), "senha_definida": bool(senha),
			"ver_historico": acesso.ver_historico, "oportunidades": [o.oportunidade for o in acesso.oportunidades],
		},
	)
	return {"id": acesso.name, "convidado": novo and not senha}


@frappe.whitelist(methods=["POST"])
def definir_distrito(cliente, equipamentos, distrito=None):
	"""Distrito de vários equipamentos de uma vez (vazio = tira do distrito)."""
	_interno()
	if distrito and frappe.db.get_value("Distrito Cliente", distrito, "cliente") != cliente:
		raise frappe.PermissionError
	for id in _lista(equipamentos):
		if frappe.db.exists(EQP_CLIENTE, id):
			if frappe.db.get_value(EQP_CLIENTE, id, "cliente") != cliente:
				raise frappe.PermissionError
			frappe.db.set_value(EQP_CLIENTE, id, "distrito", distrito or None)
			continue
		if frappe.db.get_value(EQP, id, "customer") != cliente:
			raise frappe.PermissionError
		nome = frappe.db.get_value(MAPA, {"equipamento_doctype": EQP, "equipamento": id})
		doc = frappe.get_doc(MAPA, nome) if nome else frappe.new_doc(MAPA)
		doc.update({"equipamento_doctype": EQP, "equipamento": id, "cliente": cliente, "distrito": distrito or None})
		doc.save(ignore_permissions=True)
	auditoria.registrar("Distribuição de equipamentos (central)", cliente, "Distrito Cliente", distrito, depois={"equipamentos": _lista(equipamentos)})
	return True


@frappe.whitelist(methods=["POST"])
def definir_dono(cliente, equipamentos, usuario=None):
	"""Dono (perfil Usuário) de vários equipamentos de uma vez (vazio = sem dono)."""
	_interno()
	if usuario and not frappe.db.exists("Usuario Portal Cliente", {"usuario": usuario, "cliente": cliente}):
		frappe.throw(_("Este usuário não tem acesso a este cliente."))
	for id in _lista(equipamentos):
		if frappe.db.exists(EQP_CLIENTE, id):
			if frappe.db.get_value(EQP_CLIENTE, id, "cliente") != cliente:
				raise frappe.PermissionError
			frappe.db.set_value(EQP_CLIENTE, id, "dono", usuario or None)
			continue
		if frappe.db.get_value(EQP, id, "customer") != cliente:
			raise frappe.PermissionError
		nome = frappe.db.get_value(MAPA, {"equipamento_doctype": EQP, "equipamento": id})
		doc = frappe.get_doc(MAPA, nome) if nome else frappe.new_doc(MAPA)
		doc.update({"equipamento_doctype": EQP, "equipamento": id, "cliente": cliente, "dono": usuario or None})
		doc.save(ignore_permissions=True)
	auditoria.registrar("Dono de equipamentos (central)", cliente, None, None, depois={"usuario": usuario, "equipamentos": _lista(equipamentos)})
	return True


@frappe.whitelist(methods=["POST"])
def vincular_os(doctype, os, equipamento):
	"""Liga a OS ao equipamento (campo "Digite o número de série do equipamento")."""
	_interno()
	if doctype not in (OSI, OSE):
		raise frappe.PermissionError
	cliente = frappe.db.get_value(doctype, os, "customer")
	if frappe.db.get_value(EQP, equipamento, "customer") != cliente:
		frappe.throw(_("O equipamento não é do mesmo cliente da OS."))
	frappe.db.set_value(doctype, os, "informe_numero_serie", equipamento)
	frappe.get_doc(doctype, os).add_comment("Comment", _("Equipamento {0} vinculado pela central do portal.").format(equipamento))
	auditoria.registrar("OS vinculada ao equipamento (central)", cliente, doctype, os, depois={"equipamento": equipamento})
	return True


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def usuarios_do_cliente(doctype, txt, searchfield, start, page_len, filters):
	"""Busca do campo "Dono": só usuários do portal com acesso ao cliente do registro."""
	cliente = (filters or {}).get("cliente")
	return frappe.db.sql(
		"""select usuario, nome_completo from `tabUsuario Portal Cliente`
		where cliente = %(cliente)s and ativo = 1 and (usuario like %(txt)s or nome_completo like %(txt)s)
		order by nome_completo limit %(start)s, %(len)s""",
		{"cliente": cliente or "", "txt": f"%{txt}%", "start": int(start), "len": int(page_len)},
	)


@frappe.whitelist()
def previa_email(modelo):
	"""Prévia de um modelo de e-mail do portal (manual, parte da ER), com dados de exemplo."""
	_interno()
	from solucoes.portal import emails

	if modelo not in ("convite", "acesso_liberado", "recuperar_senha", "resumo_semanal"):
		raise frappe.PermissionError
	exemplo = {
		"email": "maria@cliente.com.br", "nome": "Maria", "cliente": "Cliente Exemplo Ltda", "perfil": "Gestor",
		"descricao_perfil": emails.DESCRICAO_PERFIL["Gestor"], "link": "#",
		"vencidos": [{"tag": "LAB-08", "descricao": "Analisador de Cloro Online", "distrito_nome": "Filial Campinas", "owner": "Patrícia Lima", "proxima_calibracao": "2026-10-05"}],
		"criticos": [{"tag": "LAB-01", "descricao": "Espectrofotômetro", "distrito_nome": "Fábrica Matriz", "owner": "Carlos Mendes", "proxima_calibracao": "2026-11-02"}],
	}
	html = emails.montar(modelo, **exemplo)
	return html.replace('embed="/assets/solucoes/img/er-analitica.png"', 'src="/assets/solucoes/img/er-analitica.png"')


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def oportunidades_query(doctype, txt, searchfield, start, page_len, filters):
	"""Busca de oportunidades no cadastro do acesso: só as do cliente, por código, título, contato ou e-mail."""
	_interno()
	busca = f"%{txt}%"
	return frappe.db.sql(
		"""select name, title, contact_email from `tabOpportunity`
		where opportunity_from = 'Customer' and party_name = %(cliente)s
			and (name like %(t)s or title like %(t)s or contact_email like %(t)s or contact_display like %(t)s)
		order by creation desc limit %(start)s, %(len)s""",
		{"cliente": (filters or {}).get("cliente") or "", "t": busca, "start": start, "len": page_len},
	)
