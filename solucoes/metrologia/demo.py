"""Dados de demonstração do portal.

	bench --site erp.localhost execute solucoes.metrologia.demo.criar_dados_demo
	bench --site erp.localhost execute solucoes.metrologia.demo.apagar_dados_demo

Login no portal: cliente@demo.com / Demo@12345
"""

import random

import frappe
from frappe.utils import add_days, add_months, getdate, today

CLIENTES = ["Indústria Alfa Demo", "Metalúrgica Beta Demo"]
USUARIO = "cliente@demo.com"
SENHA = "Demo@12345"

MODELOS = [
	# grandeza, descrição, fabricante, modelo, faixa, resolução, unidade, tolerância, nominais
	("Dimensional", "Paquímetro Digital", "Mitutoyo", "500-196-30", "0 a 150 mm", "0,01 mm", "mm", 0.03, [0, 50, 100, 150]),
	("Dimensional", "Micrômetro Externo", "Mitutoyo", "103-137", "0 a 25 mm", "0,001 mm", "mm", 0.004, [0, 10, 20, 25]),
	("Dimensional", "Relógio Comparador", "Digimess", "121.304", "0 a 10 mm", "0,01 mm", "mm", 0.02, [0, 2, 5, 10]),
	("Pressão", "Manômetro Analógico", "Wika", "213.53", "0 a 10 bar", "0,2 bar", "bar", 0.16, [0, 2.5, 5, 7.5, 10]),
	("Pressão", "Transmissor de Pressão", "Endress+Hauser", "PMP51", "0 a 40 bar", "0,01 bar", "bar", 0.1, [0, 10, 20, 30, 40]),
	("Temperatura", "Termômetro Digital", "Instrutherm", "TH-1300", "-50 a 300 °C", "0,1 °C", "°C", 0.5, [0, 50, 100, 200]),
	("Temperatura", "Termopar Tipo K", "Ecil", "TK-01", "0 a 1000 °C", "1 °C", "°C", 2.2, [100, 300, 500, 800]),
	("Elétrica", "Multímetro Digital", "Fluke", "87V", "0 a 1000 V", "0,1 mV", "V", 0.05, [1, 10, 100, 500]),
	("Massa", "Balança de Precisão", "Shimadzu", "UX620H", "0 a 620 g", "0,001 g", "g", 0.005, [0, 100, 200, 500]),
	("Torque", "Torquímetro de Estalo", "Gedore", "TSN 200", "40 a 200 N·m", "1 N·m", "N·m", 8, [40, 100, 160, 200]),
	("Força", "Célula de Carga", "HBM", "U10M", "0 a 50 kN", "0,01 kN", "kN", 0.25, [10, 20, 30, 50]),
]
SETORES = ["Usinagem", "Qualidade", "Montagem", "Caldeiraria", "Laboratório", "Manutenção", "Expedição"]
LAB_EXTERNOS = ["Lab Cal Terceiro Ltda", "Metrocal Serviços"]


def criar_dados_demo():
	random.seed(42)
	frappe.flags.in_demo = True

	clientes = [_cliente(nome) for nome in CLIENTES]
	_usuario_portal(clientes)

	for cliente in clientes:
		_equipamentos(cliente, 28 if cliente == clientes[0] else 14)
		_ordens(cliente)

	criar_demo_distritos()
	criar_demo_padroes()
	criar_demo_verificacoes()
	frappe.db.commit()
	print(f"Dados de demonstração criados. Login: {USUARIO} / {SENHA}")


# ------------------------------------------------------------- padrões do laboratório
PADROES = [
	# código, descrição, grandeza, U, última calibração (dias atrás), status
	("BLC-001", "Jogo de blocos padrão classe 0", "Dimensional", 0.00012, 200, "Ativo"),
	("MAN-REF-01", "Manômetro padrão digital 0–100 bar", "Pressão", 0.02, 120, "Ativo"),
	("TERM-PT100", "Termômetro de resistência padrão Pt-100", "Temperatura", 0.05, 340, "Ativo"),  # vence em ~25 dias
	("MASSA-F1", "Conjunto de massas padrão classe F1", "Massa", 0.0005, 400, "Ativo"),  # vencido
	("MULT-8846", "Multímetro padrão 6½ dígitos", "Elétrica", 0.0002, 90, "Ativo"),
	("TORQ-REF", "Transdutor de torque padrão", "Torque", 0.4, 60, "Bloqueado"),  # danificado
	("CEL-REF", "Célula de carga padrão 100 kN", "Força", 0.05, 150, "Ativo"),
]


def criar_demo_padroes():
	"""Padrões com 4 anos de histórico e vínculo aos certificados internos já existentes."""
	for codigo, descricao, grandeza, incerteza, dias, status in PADROES:
		if frappe.db.exists("Padrao Metrologia", codigo):
			continue
		ultima = getdate(add_days(today(), -dias))
		frappe.get_doc(
			{
				"doctype": "Padrao Metrologia",
				"codigo": codigo,
				"descricao": descricao,
				"grandeza": grandeza,
				"status": status,
				"fabricante": random.choice(["Mitutoyo", "Fluke", "Fluke Calibration", "HBM", "Mettler Toledo"]),
				"numero_serie": f"P{random.randint(10000, 99999)}",
				"periodicidade_meses": 12,
				"incerteza_expandida": incerteza,
				"fator_k": 2,
				"calibracoes": [
					{
						"data_calibracao": add_months(ultima, -12 * k),
						"numero_certificado": f"RBC-{random.randint(10000, 99999)}/{str(add_months(ultima, -12 * k))[2:4]}",
						"laboratorio_calibrador": random.choice(["Lab Nacional de Metrologia", "Calibra RBC Ltda", "Metrocal Referência"]),
						"acreditado": 1,
						"incerteza_expandida": incerteza,
					}
					for k in range(4)
				],
			}
		).insert(ignore_permissions=True)

	# liga cada certificado interno a um padrão da mesma grandeza, se válido na data
	por_grandeza = {g: frappe.get_doc("Padrao Metrologia", c) for c, _, g, *_ in PADROES}
	vinculados = 0
	for cert in frappe.get_all(
		"Certificado Calibracao", filters={"origem": "Interno"}, fields=["name", "equipamento", "data_calibracao"]
	):
		grandeza = frappe.db.get_value("Equipamento Cliente", cert.equipamento, "grandeza")
		padrao = por_grandeza.get(grandeza)
		if not padrao or padrao.disponivel_em(cert.data_calibracao)[0]:
			continue
		doc = frappe.get_doc("Certificado Calibracao", cert.name)
		if not doc.padroes:
			doc.append("padroes", {"padrao": padrao.name})
			doc.save(ignore_permissions=True)
			vinculados += 1
	print(f"Padrões criados; {vinculados} certificados vinculados.")


def criar_demo_verificacoes():
	"""Verificações intermediárias mensais em parte do parque, com uma não conformidade."""
	random.seed(11)
	ja_verificados = set(frappe.get_all("Verificacao Intermediaria", pluck="equipamento"))
	equipamentos = [
		e
		for cliente in (_id_cliente(CLIENTES[0]), _id_cliente(CLIENTE_DISTRITOS))
		for e in frappe.get_all(
			"Equipamento Cliente",
			filters={"cliente": cliente, "tolerancia": [">", 0]},
			fields=["name", "tolerancia", "grandeza"],
			order_by="name",
			limit=7,
		)
		if e.name not in ja_verificados
	]
	for i, eqp in enumerate(equipamentos):
		frappe.db.set_value("Equipamento Cliente", eqp.name, "verificacao_intervalo_dias", 30)
		referencia = {"Dimensional": 50, "Pressão": 5, "Temperatura": 100, "Massa": 200}.get(eqp.grandeza, 10)
		ultima_ha = 45 if i % 5 == 0 else random.randint(3, 25)  # alguns atrasados
		for k, dias in enumerate((ultima_ha + 60, ultima_ha + 30, ultima_ha)):
			fora = i == 2 and k == 2  # uma não conformidade na verificação mais recente
			desvio = eqp.tolerancia * (1.6 if fora else random.uniform(-0.5, 0.5))
			frappe.get_doc(
				{
					"doctype": "Verificacao Intermediaria",
					"equipamento_doctype": "Equipamento Cliente",
					"equipamento": eqp.name,
					"data": f"{add_days(today(), -dias)} 09:30:00",
					"referencia_utilizada": f"Referência de {referencia} do cliente",
					"realizado_por": USUARIO,
					"pontos": [{"valor_referencia": referencia, "valor_lido": round(referencia + desvio, 6)}],
				}
			).insert(ignore_permissions=True)
	print(f"Verificações intermediárias criadas para {len(equipamentos)} equipamentos.")


# ------------------------------------------------------------- cliente com controle por distritos
CLIENTE_DISTRITOS = "Saneamento Gama Demo"
DISTRITOS = ["Distrito Norte", "Distrito Sul", "Distrito Leste", "Distrito Oeste"]
USUARIOS_DISTRITOS = [
	# e-mail, nome, perfil, distritos
	("gestor@demo.com", "Gabriela Gestora", "Gestor", []),
	("ana@demo.com", "Ana Norte", "Líder", ["Distrito Norte"]),
	("bruno@demo.com", "Bruno Sul-Leste", "Líder", ["Distrito Sul", "Distrito Leste"]),
	("auditor@demo.com", "Auditor Externo", "Usuário", []),
]


def criar_demo_distritos():
	"""Cliente com controle por distritos: 1 gestor, 2 responsáveis e 1 auditor (consulta)."""
	random.seed(7)
	cliente = _cliente(CLIENTE_DISTRITOS)
	if not frappe.db.exists("Cliente Portal", cliente):
		frappe.get_doc({"doctype": "Cliente Portal", "cliente": cliente}).insert(ignore_permissions=True)
	frappe.db.set_value("Cliente Portal", cliente, "usa_controle_distritos", 1)

	ids = {}
	for nome in DISTRITOS:
		ids[nome] = frappe.db.get_value("Distrito Cliente", {"cliente": cliente, "nome_distrito": nome}) or (
			frappe.get_doc({"doctype": "Distrito Cliente", "cliente": cliente, "nome_distrito": nome}).insert(ignore_permissions=True).name
		)

	# Norte bem cuidado, Oeste abandonado: o ranking do gestor fica interessante
	atraso = {"Distrito Norte": 0.3, "Distrito Sul": 1.0, "Distrito Leste": 1.2, "Distrito Oeste": 2.2}
	for nome, distrito in ids.items():
		_equipamentos(cliente, 9, distrito=distrito, prefixo=nome.split()[-1][:3].upper(), fator_atraso=atraso[nome])
	_ordens(cliente)

	for email, nome_completo, perfil, distritos in USUARIOS_DISTRITOS:
		_criar_usuario(email, nome_completo)
		frappe.get_doc(
			{
				"doctype": "Usuario Portal Cliente",
				"usuario": email,
				"cliente": cliente,
				"perfil": perfil,
				"distritos": [{"distrito": ids[d]} for d in distritos],
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()
	print(f"Cliente com distritos: {', '.join(u[0] for u in USUARIOS_DISTRITOS)} / {SENHA}")


def _equipamentos(cliente, quantidade, distrito=None, prefixo=None, fator_atraso=1.0):
	tecnicos = ["Carlos Souza", "Ana Ribeiro", "Marcos Lima"]
	prefixo = prefixo or "".join(p[0] for p in cliente.split()[:2]).upper()
	for i in range(1, quantidade + 1):
		grandeza, desc, fab, modelo, faixa, res, un, tol, nominais = random.choice(MODELOS)
		terceiro = random.random() < 0.2
		eqp = frappe.get_doc(
			{
				"doctype": "Equipamento Cliente",
				"cliente": cliente,
				"distrito": distrito,
				"tag": f"{prefixo}-{grandeza[:3].upper()}-{i:03d}",
				"descricao": desc,
				"grandeza": grandeza,
				"fabricante": fab,
				"modelo": modelo,
				"numero_serie": f"SN{random.randint(100000, 999999)}",
				"faixa_medicao": faixa,
				"resolucao": res,
				"unidade": un,
				"localizacao": random.choice(SETORES),
				"responsavel": random.choice(["João Pereira", "Fernanda Alves", "Ricardo Gomes"]),
				"calibrado_por": "Terceiro" if terceiro else "Nosso Laboratório",
				"fornecedor_externo": random.choice(LAB_EXTERNOS) if terceiro else None,
				"periodicidade_meses": random.choice([6, 12, 12, 12, 24]),
				"tolerancia": tol,
				"origem_cadastro": "Cliente" if terceiro else "Laboratório",
			}
		).insert(ignore_permissions=True)

		if random.random() < 0.06:
			continue  # alguns sem calibração alguma

		# 1 a 3 calibrações históricas; a última define a situação atual
		dias_atras = random.randint(5, int(30 * eqp.periodicidade_meses * min(fator_atraso, 1.0)) + int(60 * fator_atraso))
		ultima = getdate(add_days(today(), -dias_atras))
		datas = [add_months(ultima, -eqp.periodicidade_meses * k) for k in range(random.randint(1, 3))][::-1]
		for data in datas:
			deriva = random.uniform(-0.6, 0.6)
			if random.random() < 0.1:
				deriva = random.choice([-1.4, 1.4])  # reprovado
			frappe.get_doc(
				{
					"doctype": "Certificado Calibracao",
					"equipamento": eqp.name,
					"origem": "Externo" if terceiro else "Interno",
					"laboratorio_externo": eqp.fornecedor_externo,
					"numero_certificado": f"EXT-{random.randint(1000, 9999)}" if terceiro else None,
					"acreditado": 1,
					"data_calibracao": data,
					"tecnico": None if terceiro else random.choice(tecnicos),
					"padroes_utilizados": None if terceiro else "Bloco padrão classe 0 (Cert. RBC 12345/25)",
					"condicoes_ambientais": "20 ± 1 °C · 50 ± 10 %UR",
					"status_analise": "Pendente" if data == datas[-1] and random.random() < 0.35 else "Aprovado",
					"pontos": [
						{
							"valor_nominal": n,
							"valor_medido": round(n + tol * deriva * random.uniform(0.5, 1), 6),
							"incerteza": round(tol * 0.25, 6),
						}
						for n in nominais
					],
				}
			).insert(ignore_permissions=True)


def _criar_usuario(email, nome_completo):
	if frappe.db.exists("User", email):
		return
	primeiro, _, resto = nome_completo.partition(" ")
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": primeiro,
			"last_name": resto,
			"user_type": "Website User",
			"send_welcome_email": 0,
			"roles": [{"role": "Customer"}],
		}
	).insert(ignore_permissions=True)
	user.new_password = SENHA
	user.save(ignore_permissions=True)


def _cnpj_ficticio(nome):
	"""CNPJ válido (dígitos corretos), diferente para cada cliente de demonstração: 99.xxx.xxx/0001-dv."""
	base = [9, 9] + [int(c) for c in f"{int(frappe.generate_hash(nome, 6), 16) % 10**6:06d}"] + [0, 0, 0, 1]
	for pesos in ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]):
		resto = sum(d * p for d, p in zip(base, pesos)) % 11
		base.append(0 if resto < 2 else 11 - resto)
	n = "".join(map(str, base))
	return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}"


def _id_cliente(nome):
	return frappe.db.get_value("Customer", {"customer_name": nome}) or nome


def _cliente(nome):
	"""Cliente de demonstração. Procura pelo nome (o ID pode vir de série, ex.: CLIENTE-00001)
	e preenche os campos que o cadastro da empresa exige (CNPJ etc.) com valores fictícios."""
	existente = frappe.db.get_value("Customer", {"customer_name": nome})
	if existente:
		return existente
	doc = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": nome,
			"customer_type": "Company",
			"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}) or "All Customer Groups",
			"territory": frappe.db.get_value("Territory", {"is_group": 0}) or "All Territories",
		}
	)
	cnpj = _cnpj_ficticio(nome)
	ficticios = {"cnpj": cnpj, "tax_id": cnpj, "inscricao_estadual": "ISENTO"}
	meta = frappe.get_meta("Customer")
	doc.update({campo: valor for campo, valor in ficticios.items() if meta.has_field(campo)})
	doc.insert(ignore_permissions=True)
	return doc.name


def _usuario_portal(clientes):
	if not frappe.db.exists("User", USUARIO):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": USUARIO,
				"first_name": "Cliente",
				"last_name": "Demonstração",
				"user_type": "Website User",
				"send_welcome_email": 0,
				"roles": [{"role": "Customer"}],
			}
		).insert(ignore_permissions=True)
		user.new_password = SENHA
		user.save(ignore_permissions=True)

	# Acesso explícito (o portal só reconhece "Usuario Portal Cliente").
	for cliente in clientes:
		if not frappe.db.exists("Usuario Portal Cliente", {"usuario": USUARIO, "cliente": cliente}):
			frappe.get_doc(
				{"doctype": "Usuario Portal Cliente", "email": USUARIO, "cliente": cliente, "perfil": "Gestor", "ativo": 1}
			).insert(ignore_permissions=True)


def _ordens(cliente):
	equipamentos = frappe.get_all("Equipamento Cliente", filters={"cliente": cliente}, pluck="name")
	cenarios = [
		("Enviada", -60, "Calibração"),
		("Concluída", -25, "Calibração"),
		("Em Execução", -8, "Calibração"),
		("Aguardando Aprovação", -5, "Manutenção"),
		("Recebida", -2, "Calibração + Manutenção"),
		("Solicitada", 0, "Calibração"),
	]
	for status, dias, tipo in cenarios:
		os_doc = frappe.get_doc(
			{
				"doctype": "Ordem Servico Metrologia",
				"cliente": cliente,
				"tipo_servico": tipo,
				"data_solicitacao": add_days(today(), dias),
				"data_prevista": add_days(today(), dias + random.choice([4, 10, 15])),
				"itens": [{"equipamento": e, "servico": tipo} for e in random.sample(equipamentos, random.randint(1, 5))],
			}
		).insert(ignore_permissions=True)
		# percorre as etapas para gerar o histórico
		etapas = ["Recebida", "Em Análise", "Aguardando Aprovação", "Em Execução", "Concluída", "Enviada"]
		for etapa in etapas[: etapas.index(status) + 1] if status != "Solicitada" else []:
			os_doc.status = etapa
			if etapa == "Aguardando Aprovação":
				os_doc.status_orcamento = "Aguardando Cliente"
			elif etapa == "Em Execução":
				os_doc.status_orcamento = "Aprovado"
			if etapa in ("Concluída", "Enviada"):
				for item in os_doc.itens:
					item.status_item = "Concluído"
			os_doc.save(ignore_permissions=True)


def apagar_dados_demo():
	for cliente in [_id_cliente(n) for n in (*CLIENTES, CLIENTE_DISTRITOS)]:
		for dt in ("Ordem Servico Metrologia", "Certificado Calibracao", "Equipamento Cliente", "Usuario Portal Cliente", "Distrito Cliente", "Cliente Portal"):
			for name in frappe.get_all(dt, filters={"cliente": cliente}, pluck="name"):
				frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
	frappe.db.commit()
	print("Dados de demonstração removidos (clientes e usuário mantidos).")
