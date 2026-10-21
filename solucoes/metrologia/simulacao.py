"""Simulação do processo completo, do zero, pelos mesmos caminhos do dia a dia.

	bench --site site1.local execute solucoes.metrologia.simulacao.rodar
	bench --site site1.local execute solucoes.metrologia.simulacao.apagar

1. ERP: cliente + contatos.                     4. ERP: equipamentos (ficha do Modelo).
2. Central: libera o portal (com distritos).    5. Central: distribui e define dono.
3. Central: distritos e acessos (com senha).    6. ERP: OS Interna/Externa até o certificado.
7. Central: liga a OS Externa que veio sem equipamento.
8. Portal (Líder): equipamento de terceiro + certificado.
9. Conferência do que cada perfil enxerga.

Senha de todos os acessos: Simula@123
"""

import frappe
from frappe.utils import add_days, today
from frappe.utils.pdf import get_pdf

CLIENTE = "Simulação Zero Ltda"
SENHA = "Simula@123"
CERTIFICADO_REAL = "/private/files/021962_01 - Bem Brasil Perdizes - 2100Q.pdf"  # PDF real da ER (rastreabilidade lida dele)
EQUIPAMENTOS = [  # tag, modelo (ficha), série, distrito
	("SZ-01", "2100Q", "SIM-0001", "Unidade Norte"),
	("SZ-02", "DR 3900", "SIM-0002", "Unidade Norte"),
	("SZ-03", "SevenCompact S220", "SIM-0003", "Unidade Sul"),
	("SZ-04", "Pocket Colorimeter II", "SIM-0004", "Unidade Sul"),
]


def _passo(n, texto):
	print(f"\n[{n}] {texto}")


def rodar():
	frappe.flags.mute_emails = True
	frappe.set_user("Administrator")
	from solucoes.api import central

	# 1 ------------------------------------------------------------------ ERP: cliente + contatos
	_passo(1, "ERP — cliente e contatos")
	if frappe.db.get_value("Customer", {"customer_name": CLIENTE}):
		print("   já existe: rode `apagar` antes.")
		return
	from solucoes.metrologia.demo import _cnpj_ficticio

	cnpj = _cnpj_ficticio(CLIENTE)
	cliente = frappe.get_doc(
		{
			"doctype": "Customer", "customer_name": CLIENTE, "customer_type": "Company",
			"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}) or "All Customer Groups",
			"territory": frappe.db.get_value("Territory", {"is_group": 0}) or "All Territories",
			"cnpj": cnpj, "tax_id": cnpj, "inscricao_estadual": "ISENTO",
		}
	).insert(ignore_permissions=True).name
	contatos = {}
	for nome, email in (("Helena Diretora", "helena@simulazero.com"), ("Rafael Norte", "rafael@simulazero.com"), ("Paula Sul", "paula@simulazero.com")):
		primeiro, ultimo = nome.split(" ", 1)
		contatos[email] = frappe.get_doc(
			{
				"doctype": "Contact", "first_name": primeiro, "last_name": ultimo,
				"email_ids": [{"email_id": email, "is_primary": 1}],
				"links": [{"link_doctype": "Customer", "link_name": cliente}],
			}
		).insert(ignore_permissions=True).name
	print(f"   cliente {cliente} (CNPJ {cnpj}) · {len(contatos)} contatos")

	# 2 ------------------------------------------------------------------ Central: portal
	_passo(2, "Central — liberar o portal com controle por distritos")
	central.liberar(cliente, 1)
	print("   pendências:", central.resumo(cliente)["pendencias"])

	# 3 ------------------------------------------------------------------ Central: distritos e acessos
	_passo(3, "Central — distritos (responsável vem dos contatos) e acessos com senha")
	norte = central.salvar_distrito(cliente, "Unidade Norte", responsavel_nome="Rafael Norte", responsavel_email="rafael@simulazero.com", uf="SP", cidade="Jundiaí")
	sul = central.salvar_distrito(cliente, "Unidade Sul", responsavel_nome="Paula Sul", responsavel_email="paula@simulazero.com", uf="SP", cidade="Campinas")
	distritos = {"Unidade Norte": norte, "Unidade Sul": sul}
	central.salvar_usuario(cliente, "helena@simulazero.com", "Gestor", nome="Helena Diretora", senha=SENHA)
	central.salvar_usuario(cliente, "rafael@simulazero.com", "Líder", nome="Rafael Norte", distritos=[norte], senha=SENHA)
	print(f"   distritos {norte}, {sul} · Gestor helena@ · Líder rafael@ (Norte)")

	# 4 ------------------------------------------------------------------ ERP: equipamentos
	_passo(4, "ERP — equipamentos (a ficha do Modelo preenche marca, grandeza, tipo, capacidade)")
	eqps = {}
	for tag, modelo, serie, _d in EQUIPAMENTOS:
		ficha = frappe.db.get_value("Modelo do Equipamento", modelo, ["equipamento", "tipo", "grandeza", "marca", "capacidade"], as_dict=True)
		d = frappe.get_doc(
			{
				"doctype": "Equipamentos", "naming_series": "EQUIPC-", "customer": cliente, "tag": tag,
				"modelo_equipamento": modelo, "descricao": ficha.equipamento, "numero_serie": serie,
				"grandeza": ficha.grandeza, "marca_equipamento": ficha.marca, "tipo_equipamento": ficha.tipo,
				"capacidade": ficha.capacidade, "contact_link": contatos["helena@simulazero.com"],
			}
		).insert(ignore_permissions=True)
		eqps[tag] = d
		print(f"   {d.name} {tag} · {d.descricao} · {d.marca_equipamento} {modelo}")

	# 5 ------------------------------------------------------------------ Central: distribuição e dono
	_passo(5, "Central — distribuir nos distritos e criar o Usuário dono do SZ-03")
	for nome, id in distritos.items():
		central.definir_distrito(cliente, [eqps[t].name for t, _m, _s, d in EQUIPAMENTOS if d == nome], id)
	central.salvar_usuario(cliente, "paula@simulazero.com", "Usuário", nome="Paula Sul", equipamentos=[eqps["SZ-03"].name], senha=SENHA)
	print("   SZ-01/02 → Norte · SZ-03/04 → Sul · Usuário paula@ dona do SZ-03")

	# 6 ------------------------------------------------------------------ ERP: OS do laboratório
	_passo(6, "ERP — OS: certificado real (vigente), crítico, vencido e uma OS em andamento")
	contato = contatos["helena@simulazero.com"]
	os1 = _os_interna(cliente, contato, eqps["SZ-01"], "Em Recebimento")
	print(f"   {os1.name} SZ-01 aberta (Em Recebimento) → portal: Agendado / Recebida")
	_encerrar(os1, dias=0, rbc=1, arquivo=CERTIFICADO_REAL)
	print(f"   {os1.name} encerrada hoje com o certificado real → rastreabilidade: {len(frappe.get_doc(os1.doctype, os1.name).rastreabilidade_padroes)} padrões")
	os2 = _os_interna(cliente, contato, eqps["SZ-02"], "Em Recebimento")
	_encerrar(os2, dias=340, rbc=0)
	print(f"   {os2.name} SZ-02 encerrada há 340 dias → Crítico")
	os3 = _os_interna(cliente, contato, eqps["SZ-02"], "Em Aprovação")
	print(f"   {os3.name} SZ-02 nova OS em aprovação → orçamento aguardando o cliente")

	# OS Externa do SZ-03 sem o equipamento ligado. O ERP não deixa digitar a série sem ligar o
	# equipamento; a OS fica sem vínculo quando a série não é preenchida (só a TAG, como em OS antigas).
	os4 = frappe.get_doc(
		{
			"doctype": "Ordem Servico Externa", "naming_series": "OS-", "company": frappe.defaults.get_global_default("company"),
			"created_by": "Administrator", "customer": cliente, "contact_link": contato, "status_order_service": "Em Conserto",
			"equipment_tag": "SZ-03", "equipment_description": eqps["SZ-03"].descricao,
		}
	).insert(ignore_permissions=True)
	print(f"   {os4.name} OS Externa do SZ-03 aberta SEM o equipamento ligado")

	# 7 ------------------------------------------------------------------ Central: ligar a OS
	_passo(7, "Central — etapa OS: sugestão automática pela série e ligar")
	r = central.resumo(cliente)
	pend = next(o for o in r["os_sem_vinculo"] if o["os"] == os4.name)
	print(f"   sugestão para {os4.name}: {pend['sugestao']}")
	central.vincular_os(pend["doctype"], pend["os"], pend["sugestao"]["id"])
	os4 = frappe.get_doc("Ordem Servico Externa", os4.name)
	os4.update({"status_order_service": "Encerrada", "data_cal": add_days(today(), -400), "repaired_date": add_days(today(), -399)})
	os4.save(ignore_permissions=True)
	_anexar_pdf_demo(os4)
	print(f"   {os4.name} ligada ao SZ-03 e encerrada há 400 dias → Vencido")

	# 8 ------------------------------------------------------------------ Portal: Líder cadastra terceiro
	_passo(8, "Portal (rafael@, Líder) — equipamento de terceiro e certificado")
	from solucoes.api import portal

	frappe.set_user("rafael@simulazero.com")
	frappe.form_dict.clear()
	frappe.form_dict.portal = "consulta"
	terceiro = portal.criar_equipamento(
		{"tag": "SZ-T1", "descricao": "Manômetro de Linha", "grandeza": "Pressão", "fabricante": "Wika", "modelo": "232.50",
		 "numero_serie": "EXT-SZ-T1", "fornecedor_externo": "Lab Pressão Ltda", "distrito": norte, "periodicidade_meses": 12},
		cliente=cliente,
	)
	frappe.set_user("Administrator")
	frappe.form_dict.portal = "consulta"
	from solucoes.portal.adapters.er import AdapterER
	from solucoes.portal.sessao import Escopo

	adapter = AdapterER()
	arquivo = frappe.get_doc(
		{"doctype": "File", "file_name": "Certificado terceiro SZ-T1 (simulação).pdf", "is_private": 1,
		 "content": get_pdf("<h2>Lab Pressão Ltda</h2><p><b>SIMULAÇÃO — SEM VALIDADE</b></p><p>Manômetro de Linha · SZ-T1</p>")}
	).insert(ignore_permissions=True)
	cert = adapter.criar_certificado_externo(
		Escopo([cliente], usuario="Administrator"),
		{"equipamento_id": terceiro["id"], "numero": "LP-2026-0099", "laboratorio": "Lab Pressão Ltda", "acreditado": 1,
		 "data_calibracao": add_days(today(), -60), "data_validade": add_days(today(), 305)},
		arquivo.file_url,
	)
	print(f"   terceiro {terceiro['id']} SZ-T1 + certificado {cert['id']}")

	frappe.db.commit()

	# 9 ------------------------------------------------------------------ Histórico de atendimento
	_passo(9, "Histórico de atendimento — notas de oportunidades liberadas para o Líder")
	historico()

	# 10 ----------------------------------------------------------------- Conferência
	_passo(10, "Conferência — o que cada perfil enxerga")
	conferir()
	print("\n   Central:", central.resumo(cliente)["pendencias"])
	print(f"\nPronto. Logins (senha {SENHA}): helena@simulazero.com (Gestor) · rafael@simulazero.com (Líder) · paula@simulazero.com (Usuário)")


def historico():
	"""Duas oportunidades do cliente: a atual (liberada para o Líder) e uma antiga (que NÃO aparece)."""
	frappe.flags.mute_emails = True
	frappe.set_user("Administrator")
	cliente = frappe.db.get_value("Customer", {"customer_name": CLIENTE})
	hoje = frappe.utils.now_datetime()
	atual = _oportunidade(cliente, f"{CLIENTE} - Rafael Norte", [
		(-2, "<p><strong>Contrato de calibração 2026 – Owner: Rafael Norte</strong></p><p>Equipamentos no contrato: 4</p>"
		 "<ul><li>SZ-01 – Turbidímetro – próx. calibração em novembro – AGENDADO</li><li>SZ-02 – Espectrofotômetro – AGENDADO</li></ul>"),
		(-1, "<p>Serviço realizado na Unidade Norte, acompanhado por Rafael.</p>"),
	], hoje, "rafael@simulazero.com")
	_oportunidade(cliente, f"{CLIENTE} - Orçamento antigo", [(-700, "<p>Nota interna antiga: negociação de desconto.</p>")], hoje, "helena@simulazero.com")
	_oportunidade(cliente, f"{CLIENTE} - Calibração Unidade Sul", [(-5, "<p>Proposta enviada para a Unidade Sul.</p>")], hoje, "helena@simulazero.com")
	acesso = frappe.get_doc("Usuario Portal Cliente", {"usuario": "rafael@simulazero.com", "cliente": cliente})
	acesso.ver_historico = 1
	acesso.set("oportunidades", [{"oportunidade": atual}])
	acesso.save(ignore_permissions=True)
	frappe.db.commit()
	print(f"   Histórico liberado para rafael@ (Líder): só {atual}; a oportunidade antiga fica de fora.")


def _oportunidade(cliente, titulo, notas, hoje, email=None):
	inicio = frappe.utils.add_days(hoje, min(d for d, _ in notas))
	opp = frappe.get_doc(
		{"doctype": "Opportunity", "opportunity_from": "Customer", "party_name": cliente, "title": titulo, "transaction_date": inicio.date(), "contact_email": email}
	)
	for dias, texto in notas:
		opp.append("notes", {"note": texto, "added_by": "Administrator", "added_on": frappe.utils.add_days(hoje, dias)})
	opp.flags.ignore_mandatory = True
	opp.insert(ignore_permissions=True)
	return opp.name


def conferir():
	from solucoes.api import portal

	for email, perfil in (("helena@simulazero.com", "Gestor"), ("rafael@simulazero.com", "Líder"), ("paula@simulazero.com", "Usuário")):
		frappe.set_user(email)
		frappe.form_dict.clear()
		frappe.form_dict.portal = "consulta"
		eqs = portal.equipamentos()
		certs = portal.certificados()
		print(
			f"   {perfil:8} {email:24} vê {[(e['tag'], e['status_calibracao']) for e in eqs]}"
			f" · {len(certs)} certificado(s) · {len(portal.ordens())} OS"
		)
	frappe.set_user("Administrator")


def _os_interna(cliente, contato, eqp, status):
	return frappe.get_doc(
		{
			"doctype": "Ordem Servico Interna", "naming_series": "OS-", "customer": cliente, "contact_link": contato,
			"status_order_service": status, "equipment_location": "Laboratório ER Analítica", "entry_date": today(),
			"informe_numero_serie": eqp.name, "serie_number": eqp.name, "equipment_description": eqp.descricao,
			"equipment_model": eqp.modelo_equipamento, "equipment_tag": eqp.tag, "marca_equipamento": eqp.marca_equipamento,
			"grandeza": eqp.grandeza,
		}
	).insert(ignore_permissions=True)


def _encerrar(os, dias, rbc, arquivo=None):
	os = frappe.get_doc(os.doctype, os.name)
	data_cal = add_days(today(), -dias)
	os.update(
		{
			"status_order_service": "Encerrada", "data_cal": data_cal, "cal_rbc": rbc, "cal_rastreavel": 0 if rbc else 1,
			"situacao_equipamento": "CONFORME", "repaired_date": data_cal, "data_saida": add_days(data_cal, 2),
			"custom_quantidade_certificados": "_01",
		}
	)
	if arquivo:
		os.anexo_certificado = arquivo  # salvar com o anexo dispara a leitura da rastreabilidade
	os.save(ignore_permissions=True)
	if not arquivo:
		_anexar_pdf_demo(os)


def _anexar_pdf_demo(os):
	arquivo = frappe.get_doc(
		{"doctype": "File", "file_name": f"Certificado {os.name} (simulação).pdf", "is_private": 1,
		 "attached_to_doctype": os.doctype, "attached_to_name": os.name, "attached_to_field": "anexo_certificado",
		 "content": get_pdf(f"<h2>CERTIFICADO DE CALIBRAÇÃO</h2><p><b>SIMULAÇÃO — SEM VALIDADE</b></p><p>{os.name}</p>")}
	).insert(ignore_permissions=True)
	frappe.db.set_value(os.doctype, os.name, "anexo_certificado", arquivo.file_url, update_modified=False)


def apagar():
	"""Remove tudo o que `rodar` criou."""
	frappe.flags.mute_emails = True
	frappe.set_user("Administrator")
	cliente = frappe.db.get_value("Customer", {"customer_name": CLIENTE})
	if not cliente:
		print("Nada a remover.")
		return
	for dt in ("Ordem Servico Interna", "Ordem Servico Externa"):
		for nome in frappe.get_all(dt, filters={"customer": cliente}, pluck="name"):
			for f in frappe.get_all("File", filters={"attached_to_doctype": dt, "attached_to_name": nome}, pluck="name"):
				frappe.delete_doc("File", f, force=True, ignore_permissions=True)
			frappe.delete_doc(dt, nome, force=True, ignore_permissions=True)
	for eqp in frappe.get_all("Equipamento Cliente", filters={"cliente": cliente}, pluck="name"):
		for cert in frappe.get_all("Certificado Calibracao", filters={"equipamento": eqp}, pluck="name"):
			frappe.delete_doc("Certificado Calibracao", cert, force=True, ignore_permissions=True)
		frappe.delete_doc("Equipamento Cliente", eqp, force=True, ignore_permissions=True)
	for dt in ("Distrito Equipamento", "Usuario Portal Cliente", "Equipamentos", "Distrito Cliente", "Cliente Portal", "Log Portal"):
		campo = "customer" if dt == "Equipamentos" else "cliente"
		for nome in frappe.get_all(dt, filters={campo: cliente}, pluck="name"):
			frappe.delete_doc(dt, nome, force=True, ignore_permissions=True)
	for email in ("helena@simulazero.com", "rafael@simulazero.com", "paula@simulazero.com"):
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)
	for c in frappe.get_all("Dynamic Link", filters={"parenttype": "Contact", "link_name": cliente}, pluck="parent"):
		frappe.delete_doc("Contact", c, force=True, ignore_permissions=True)
	for opp in frappe.get_all("Opportunity", filters={"opportunity_from": "Customer", "party_name": cliente}, pluck="name"):
		frappe.delete_doc("Opportunity", opp, force=True, ignore_permissions=True)
	frappe.delete_doc("Customer", cliente, force=True, ignore_permissions=True)
	frappe.db.commit()
	print(f"Simulação de {CLIENTE} removida.")
