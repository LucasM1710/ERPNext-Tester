"""Demonstração da página /consulta com os DocTypes REAIS da empresa.

	bench --site site1.local execute solucoes.metrologia.demo_consulta.criar
	bench --site site1.local execute solucoes.metrologia.demo_consulta.completar
	bench --site site1.local execute solucoes.metrologia.demo_consulta.apagar

Cria um cliente fictício com equipamentos (Equipamentos) e OS Interna/Externa em
situações variadas — em dia, a vencer, vencido, sem calibração, OS em andamento —,
certificados em PDF com rastreabilidade de padrões, dois distritos e três usuários
(Gestor, Responsável e Consulta). Tudo pelo caminho normal dos documentos, com as
validações da empresa. Nenhum e-mail é enviado.

Login: gestor.delta@demo.com / responsavel.delta@demo.com / consulta.delta@demo.com
Senha: Demo@12345
"""

import frappe
from frappe.utils import add_days, getdate, today
from frappe.utils.pdf import get_pdf

CLIENTE = "Laticínios Delta Demo"
SENHA = "Demo@12345"
DISTRITOS = ["Fábrica Matriz", "Filial Campinas"]
# responsável (owner), e-mail, UF e cidade de cada distrito
INFO_DISTRITOS = {
	"Fábrica Matriz": ("Carlos Mendes", "carlos.mendes@demo.com", "SP", "Jundiaí"),
	"Filial Campinas": ("Patrícia Lima", "patricia.lima@demo.com", "SP", "Campinas"),
}
# equipamentos calibrados por OUTROS laboratórios, cadastrados pelo cliente no portal
# tag, descrição, grandeza, fabricante, modelo, laboratório, distrito, dias atrás do certificado (None = sem certificado)
TERCEIROS = [
	("TERC-01", "Manômetro de Processo", "Pressão", "Wika", "232.50", "Lab Pressão Ltda", "Fábrica Matriz", 150),
	("TERC-02", "Termopar da Autoclave", "Temperatura", "Ecil", "TK-01", "Metrocal Serviços", "Filial Campinas", None),
]
USUARIOS = [
	("gestor.delta@demo.com", "Gestora Delta", "Gestor", []),
	("responsavel.delta@demo.com", "Líder Matriz", "Líder", ["Fábrica Matriz"]),
	("consulta.delta@demo.com", "Usuário Filial", "Usuário", []),
]
TIPOS = ["Bancada", "Portátil", "Processo"]

# nome, marca, modelo, grandeza, tipo, capacidade, distrito (None = sem distrito), histórico
# histórico: lista de OS (doctype, status, dias atrás da calibração, situação, RBC)
EQUIPAMENTOS = [
	("Espectrofotômetro", "Hach", "DR 3900", "Óptica", "Bancada", "320 a 1100 nm", 0,
		[("I", "Encerrada", 725, "CONFORME", 0), ("I", "Encerrada", 360, "CONFORME", 0)]),
	("Turbidímetro Portátil", "Hach", "2100Q", "Óptica", "Portátil", "0 a 1000 NTU", 0,
		[("E", "Encerrada", 120, None, 0)]),
	("pHmetro de Bancada", "Mettler Toledo", "SevenCompact S220", "Físico-química", "Bancada", "0 a 14 pH", 0,
		[("I", "Encerrada", 400, "CONFORME", 0), ("I", "Em Aprovação", None, None, 0)]),
	("Condutivímetro", "Mettler Toledo", "SevenGo Pro", "Físico-química", "Portátil", "0 a 500 mS/cm", 0,
		[("I", "Encerrada", 60, "CONFORME COM RESTRIÇÃO", 0)]),
	("Balança Semi-Analítica", "Sartorius", "Entris II 224", "Massa", "Bancada", "0 a 220 g", 0,
		[("I", "Encerrada", 340, "CONFORME", 1)]),
	("Termômetro Digital", "Incoterm", "TD-200", "Temperatura", "Portátil", "-50 a 300 °C", 0,
		[("I", "Em Conserto", None, None, 0)]),
	("Colorímetro de Cloro", "Hach", "Pocket Colorimeter II", "Óptica", "Portátil", "0 a 8 mg/L", 1,
		[("E", "Encerrada", 200, None, 0), ("E", "Em Conserto", None, None, 0)]),
	("Analisador de Cloro Online", "Hach", "CL17sc", "Físico-química", "Processo", "0 a 10 mg/L", 1,
		[("E", "Encerrada", 380, None, 0)]),
	("Micropipeta", "Eppendorf", "Research Plus 100", "Volumes", "Bancada", "10 a 100 µL", 1,
		[("I", "Aguardando Retirada", 8, "CONFORME", 0)]),
	("Oxímetro", "YSI", "ProODO", "Físico-química", "Portátil", "0 a 50 mg/L", 1,
		[("I", "Em Recebimento", None, None, 0)]),
	("Incubadora DBO", "Tecnal", "TE-391", "Temperatura", "Bancada", "5 a 50 °C", None, []),
	("Fotômetro Multiparâmetro", "Hanna", "HI83399", "Óptica", "Portátil", "Multiparâmetro", 1,
		[("I", "Encerrada", 30, "CONFORME", 1)]),
]


def criar():
	frappe.flags.mute_emails = True
	cliente = _cliente()
	contato = _contato(cliente)
	_auxiliares()
	distritos = _portal(cliente)
	padroes = _padroes_de_exemplo()

	for i, (nome, marca, modelo, grandeza, tipo, capacidade, distrito, historico) in enumerate(EQUIPAMENTOS, 1):
		eqp = _equipamento(cliente, i, nome, marca, modelo, grandeza, tipo, capacidade)
		if distrito is not None:
			_distrito_do_equipamento(cliente, eqp, distritos[distrito])
		for doctype, status, dias, situacao, rbc in historico:
			_os(cliente, contato, eqp, doctype, status, dias, situacao, rbc, padroes)

	completar(commit=False)
	frappe.db.commit()
	print(f"Demonstração criada para {CLIENTE} ({cliente}).")
	print("Página: /consulta  ·  Usuários: " + ", ".join(u[0] for u in USUARIOS) + f"  ·  Senha: {SENHA}")


# ------------------------------------------------------------------ cadastro base
def _cliente():
	existente = frappe.db.get_value("Customer", {"customer_name": CLIENTE})
	if existente:
		return existente
	from solucoes.metrologia.demo import _cnpj_ficticio

	cnpj = _cnpj_ficticio(CLIENTE)
	doc = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": CLIENTE,
			"customer_type": "Company",
			"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}) or "All Customer Groups",
			"territory": frappe.db.get_value("Territory", {"is_group": 0}) or "All Territories",
		}
	)
	meta = frappe.get_meta("Customer")
	doc.update({c: v for c, v in {"cnpj": cnpj, "tax_id": cnpj, "inscricao_estadual": "ISENTO"}.items() if meta.has_field(c)})
	return doc.insert(ignore_permissions=True).name


def _contato(cliente):
	existente = frappe.db.get_value("Dynamic Link", {"parenttype": "Contact", "link_doctype": "Customer", "link_name": cliente}, "parent")
	if existente:
		return existente
	return (
		frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Marina",
				"last_name": "Qualidade (Demo)",
				"email_ids": [{"email_id": "qualidade.delta@demo.com", "is_primary": 1}],
				"links": [{"link_doctype": "Customer", "link_name": cliente}],
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def _auxiliares():
	"""Nomes, marcas, tipos, grandezas e fichas de Modelo usados pela demonstração."""
	for tipo in TIPOS:
		_garantir("Tipo do Equipamento", "tipo", tipo)
	for nome, marca, modelo, grandeza, tipo, capacidade, *_ in EQUIPAMENTOS:
		_garantir("Nome Equipamento", "nome_equipamento", nome)
		_garantir("Marca do Equipamento", "marca", marca)
		_garantir("Grandeza", "grandeza", grandeza)
		if not frappe.db.exists("Modelo do Equipamento", modelo):
			frappe.get_doc(
				{
					"doctype": "Modelo do Equipamento",
					"modelo": modelo,
					"equipamento": nome,
					"tipo": tipo,
					"grandeza": grandeza,
					"marca": marca,
					"capacidade": capacidade,
				}
			).insert(ignore_permissions=True)


def _garantir(doctype, campo, valor):
	if not frappe.db.exists(doctype, valor):
		frappe.get_doc({"doctype": doctype, campo: valor}).insert(ignore_permissions=True)


def _portal(cliente):
	"""Cliente com controle por distritos, os distritos e os três usuários."""
	if not frappe.db.exists("Cliente Portal", cliente):
		frappe.get_doc({"doctype": "Cliente Portal", "cliente": cliente, "usa_controle_distritos": 1}).insert(
			ignore_permissions=True
		)
	ids = []
	for nome in DISTRITOS:
		id = frappe.db.get_value("Distrito Cliente", {"cliente": cliente, "nome_distrito": nome})
		if not id:
			id = frappe.get_doc({"doctype": "Distrito Cliente", "cliente": cliente, "nome_distrito": nome, "ativo": 1}).insert(
				ignore_permissions=True
			).name
		ids.append(id)
	por_nome = dict(zip(DISTRITOS, ids))

	for email, nome, perfil, distritos in USUARIOS:
		if not frappe.db.exists("User", email):
			# Criado aqui, com senha e sem e-mail de boas-vindas.
			partes = nome.split(" ", 1)
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": partes[0],
					"last_name": partes[1] if len(partes) > 1 else "",
					"user_type": "Website User",
					"send_welcome_email": 0,
					"roles": [{"role": "Customer"}],
				}
			).insert(ignore_permissions=True)
			user.new_password = SENHA
			user.save(ignore_permissions=True)
		if not frappe.db.exists("Usuario Portal Cliente", {"usuario": email, "cliente": cliente}):
			frappe.get_doc(
				{
					"doctype": "Usuario Portal Cliente",
					"email": email,
					"nome_completo": nome,
					"cliente": cliente,
					"perfil": perfil,
					"ativo": 1,
					"distritos": [{"distrito": por_nome[d]} for d in distritos],
				}
			).insert(ignore_permissions=True)
	return ids


def _padroes_de_exemplo():
	"""Linhas de rastreabilidade já vinculadas (copiadas de OS reais), para os certificados."""
	return frappe.get_all(
		"Rastreabilidade Padrao OS",
		filters={"status": "Vinculado"},
		fields=["codigo", "descricao", "certificado_padrao", "validade", "padrao", "arquivo_padrao", "status"],
		group_by="codigo",
		limit=4,
	)


# ------------------------------------------------------------------ equipamentos e OS
def _equipamento(cliente, i, nome, marca, modelo, grandeza, tipo, capacidade):
	serie = f"DEMO-DELTA-{i:03d}"
	existente = frappe.db.get_value("Equipamentos", {"numero_serie": serie, "customer": cliente})
	if existente:
		return frappe.get_doc("Equipamentos", existente)
	return frappe.get_doc(
		{
			"doctype": "Equipamentos",
			"naming_series": "EQUIPC-",
			"customer": cliente,
			"modelo_equipamento": modelo,
			"descricao": nome,
			"numero_serie": serie,
			"tag": f"LAB-{i:02d}",
			"grandeza": grandeza,
			"marca_equipamento": marca,
			"tipo_equipamento": tipo,
			"capacidade": capacidade,
		}
	).insert(ignore_permissions=True)


def _distrito_do_equipamento(cliente, eqp, distrito):
	if not frappe.db.exists("Distrito Equipamento", {"equipamento_doctype": "Equipamentos", "equipamento": eqp.name}):
		frappe.get_doc(
			{
				"doctype": "Distrito Equipamento",
				"equipamento_doctype": "Equipamentos",
				"equipamento": eqp.name,
				"cliente": cliente,
				"distrito": distrito,
			}
		).insert(ignore_permissions=True)


def _os(cliente, contato, eqp, tipo, status, dias, situacao, rbc, padroes):
	doctype = "Ordem Servico Interna" if tipo == "I" else "Ordem Servico Externa"
	data_cal = add_days(today(), -dias) if dias is not None else None
	entrada = add_days(data_cal or today(), -12)
	dados = {
		"doctype": doctype,
		"naming_series": "OS-",
		"customer": cliente,
		"contact_link": contato,
		"status_order_service": status,
		"informe_numero_serie": eqp.name,
		"serie_number": eqp.numero_serie,
		"equipment_description": eqp.descricao,
		"equipment_model": eqp.modelo_equipamento,
		"equipment_tag": eqp.tag,
		"marca_equipamento": eqp.marca_equipamento,
		"tipo_equipamento": eqp.tipo_equipamento,
		"capacidade_equipamento": eqp.capacidade,
		"data_cal": data_cal,
		"cal_rbc": rbc,
		"cal_rastreavel": 0 if rbc else (1 if data_cal else 0),
	}
	if status in ("Encerrada", "Aguardando Retirada"):
		dados["repaired_date"] = add_days(data_cal, 1)
	if tipo == "I":
		dados.update(
			{
				"equipment_location": "Laboratório ER Analítica",
				"entry_date": entrada,
				"grandeza": eqp.grandeza,
				"situacao_equipamento": situacao,
			}
		)
		if status == "Encerrada":
			dados["data_saida"] = add_days(data_cal, 3)
	else:
		dados.update({"company": frappe.defaults.get_global_default("company"), "created_by": "Administrator"})
	if status == "Encerrada" and padroes:
		dados["rastreabilidade_padroes"] = [dict(p) for p in padroes[:3]]

	doc = frappe.get_doc(dados).insert(ignore_permissions=True)
	if status == "Encerrada":
		_anexar_certificado(doc, eqp, situacao, rbc)
	return doc


def _anexar_certificado(doc, eqp, situacao, rbc):
	"""PDF de demonstração, privado, gravado direto no campo (sem re-salvar a OS)."""
	html = f"""
		<div style="font-family: Arial, sans-serif; padding: 40px;">
			<h2 style="margin:0">CERTIFICADO DE CALIBRAÇÃO {"RBC" if rbc else "RASTREÁVEL"}</h2>
			<p style="color:#b91c1c"><b>DOCUMENTO DE DEMONSTRAÇÃO — SEM VALIDADE</b></p>
			<table cellpadding="6" style="border-collapse: collapse; margin-top: 20px;">
				<tr><td><b>Certificado</b></td><td>{doc.name}</td></tr>
				<tr><td><b>Cliente</b></td><td>{CLIENTE}</td></tr>
				<tr><td><b>Equipamento</b></td><td>{eqp.descricao} · {eqp.marca_equipamento} {eqp.modelo_equipamento}</td></tr>
				<tr><td><b>Nº de série / TAG</b></td><td>{eqp.numero_serie} / {eqp.tag}</td></tr>
				<tr><td><b>Data da calibração</b></td><td>{frappe.utils.formatdate(doc.data_cal, "dd/MM/yyyy")}</td></tr>
				<tr><td><b>Próxima calibração</b></td><td>{frappe.utils.formatdate(doc.data_cal_recomendada, "dd/MM/yyyy")}</td></tr>
				<tr><td><b>Resultado</b></td><td>{situacao or "Calibração realizada"}</td></tr>
			</table>
		</div>"""
	arquivo = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"Certificado {doc.name} (demonstração).pdf",
			"content": get_pdf(html),
			"is_private": 1,
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
			"attached_to_field": "anexo_certificado",
		}
	).insert(ignore_permissions=True)
	frappe.db.set_value(doc.doctype, doc.name, "anexo_certificado", arquivo.file_url, update_modified=False)


def completar(commit=True):
	"""Responsável/UF/cidade dos distritos e os equipamentos de terceiros (pode rodar de novo)."""
	frappe.flags.mute_emails = True
	cliente = frappe.db.get_value("Customer", {"customer_name": CLIENTE})
	ids = {}
	for nome, (resp, email, uf, cidade) in INFO_DISTRITOS.items():
		id = frappe.db.get_value("Distrito Cliente", {"cliente": cliente, "nome_distrito": nome})
		frappe.db.set_value("Distrito Cliente", id, {"responsavel_nome": resp, "responsavel_email": email, "uf": uf, "cidade": cidade})
		ids[nome] = id
	for tag, desc, grandeza, fab, modelo, lab, distrito, dias in TERCEIROS:
		if frappe.db.exists("Equipamento Cliente", {"cliente": cliente, "tag": tag}):
			continue
		eqp = frappe.get_doc(
			{
				"doctype": "Equipamento Cliente",
				"cliente": cliente,
				"tag": tag,
				"descricao": desc,
				"grandeza": grandeza,
				"fabricante": fab,
				"modelo": modelo,
				"numero_serie": f"EXT-{tag}",
				"distrito": ids[distrito],
				"status": "Ativo",
				"calibrado_por": "Terceiro",
				"fornecedor_externo": lab,
				"periodicidade_meses": 12,
				"origem_cadastro": "Cliente",
			}
		).insert(ignore_permissions=True)
		if dias is None:
			continue
		data_cal = add_days(today(), -dias)
		cert = frappe.get_doc(
			{
				"doctype": "Certificado Calibracao",
				"equipamento": eqp.name,
				"origem": "Externo",
				"numero_certificado": f"{lab.split()[0].upper()}-{getdate(data_cal).year}-0417",
				"laboratorio_externo": lab,
				"acreditado": 1,
				"data_calibracao": data_cal,
				"data_validade": add_days(data_cal, 365),
			}
		).insert(ignore_permissions=True)
		html = f"<div style='font-family:Arial;padding:40px'><h2>{lab}</h2><h3>Certificado de calibração {cert.numero_certificado}</h3><p style='color:#b91c1c'><b>DOCUMENTO DE DEMONSTRAÇÃO — SEM VALIDADE</b></p><p>{desc} · {fab} {modelo} · TAG {tag}</p></div>"
		arquivo = frappe.get_doc(
			{"doctype": "File", "file_name": f"{cert.numero_certificado} (demonstração).pdf", "content": get_pdf(html), "is_private": 1,
			 "attached_to_doctype": "Certificado Calibracao", "attached_to_name": cert.name}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Certificado Calibracao", cert.name, "arquivo", arquivo.file_url)
	# Perfil Usuário: dono de alguns equipamentos da Filial (só vê esses)
	from solucoes.portal.adapters.er import AdapterER

	donos = [frappe.db.get_value("Equipamentos", {"customer": cliente, "tag": t}) for t in ("LAB-07", "LAB-08")]
	donos += [frappe.db.get_value("Equipamento Cliente", {"cliente": cliente, "tag": "TERC-02"})]
	AdapterER().definir_donos(cliente, "consulta.delta@demo.com", [d for d in donos if d])
	if commit:
		frappe.db.commit()
	print("Distritos completados, equipamentos de terceiros criados e donos definidos.")


# ------------------------------------------------------------------ remoção
def apagar():
	"""Remove tudo o que `criar` gerou (cadastros auxiliares como marcas e modelos ficam)."""
	frappe.flags.mute_emails = True
	cliente = frappe.db.get_value("Customer", {"customer_name": CLIENTE})
	if not cliente:
		print("Nada a remover.")
		return
	for doctype in ("Ordem Servico Interna", "Ordem Servico Externa"):
		for nome in frappe.get_all(doctype, filters={"customer": cliente}, pluck="name"):
			for arquivo in frappe.get_all("File", filters={"attached_to_doctype": doctype, "attached_to_name": nome}, pluck="name"):
				frappe.delete_doc("File", arquivo, force=True, ignore_permissions=True)
			frappe.delete_doc(doctype, nome, force=True, ignore_permissions=True)
	for eqp in frappe.get_all("Equipamento Cliente", filters={"cliente": cliente}, pluck="name"):
		for cert in frappe.get_all("Certificado Calibracao", filters={"equipamento": eqp}, pluck="name"):
			frappe.delete_doc("Certificado Calibracao", cert, force=True, ignore_permissions=True)
		frappe.delete_doc("Equipamento Cliente", eqp, force=True, ignore_permissions=True)
	for doctype in ("Distrito Equipamento", "Usuario Portal Cliente", "Equipamentos", "Distrito Cliente", "Cliente Portal"):
		campo = "customer" if doctype == "Equipamentos" else "cliente"
		for nome in frappe.get_all(doctype, filters={campo: cliente}, pluck="name"):
			frappe.delete_doc(doctype, nome, force=True, ignore_permissions=True)
	for email, *_ in USUARIOS:
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)
	for contato in frappe.get_all("Dynamic Link", filters={"parenttype": "Contact", "link_name": cliente}, pluck="parent"):
		frappe.delete_doc("Contact", contato, force=True, ignore_permissions=True)
	frappe.delete_doc("Customer", cliente, force=True, ignore_permissions=True)
	frappe.db.commit()
	print(f"Demonstração de {CLIENTE} removida.")
