"""Demonstração do inventário de TI (NUNCA rodar na produção).

	bench --site <site> execute solucoes.central_ti.demo_inventario.criar
	bench --site <site> execute solucoes.central_ti.demo_inventario.apagar

Cria no ERPNext grupos de item "TI - …", itens, fornecedores e Notas de Compra LANÇADAS de
2021 a 2026; cadastra os equipamentos a partir das compras pelo mesmo caminho da tela
(Compras de TI → Cadastrar), entrega aos colaboradores, registra upgrades/manutenções, liga
chamados aos equipamentos e movimenta o estoque de periféricos. Rode depois de solucoes.central_ti.demo.criar.
"""

import random
from collections import defaultdict

import frappe
from frappe.utils import add_days, add_months, add_years, getdate, today

from solucoes.central_ti.demo import COLABORADORES, TECNICOS

RAIZ_GRUPO = "TI (Demonstração)"
FORNECEDORES = ["Dell Computadores do Brasil", "Lenovo Tecnologia Brasil", "Kalunga Empresas", "Ingram Micro", "Samsung Empresas"]
# código, nome, tipo, preço unitário, fornecedor, prefixo do nome, configuração (computadores)
CATALOGO = {
	"NB-LAT5410": ("Notebook Dell Latitude 5410", "Notebook", 5200, 0, "NB", ("Intel Core i5-10310U", "8 GB", "256 GB SSD", "Windows 10 Pro")),
	"NB-E14G2": ("Notebook Lenovo ThinkPad E14 Gen 2", "Notebook", 4800, 1, "NB", ("Intel Core i5-1135G7", "8 GB", "256 GB SSD", "Windows 11 Pro")),
	"NB-LAT5430": ("Notebook Dell Latitude 5430", "Notebook", 5600, 0, "NB", ("Intel Core i5-1245U", "16 GB", "512 GB SSD", "Windows 11 Pro")),
	"NB-LAT5440": ("Notebook Dell Latitude 5440", "Notebook", 5900, 0, "NB", ("Intel Core i5-1335U", "16 GB", "512 GB SSD", "Windows 11 Pro")),
	"NB-E14G5": ("Notebook Lenovo ThinkPad E14 Gen 5", "Notebook", 5400, 1, "NB", ("Intel Core i7-1355U", "16 GB", "512 GB SSD", "Windows 11 Pro")),
	"NB-LAT5450": ("Notebook Dell Latitude 5450", "Notebook", 6300, 0, "NB", ("Intel Core Ultra 5 125U", "16 GB", "512 GB SSD", "Windows 11 Pro")),
	"DT-OPT3080": ("Desktop Dell OptiPlex 3080", "Desktop", 3900, 0, "DT", ("Intel Core i5-10500", "8 GB", "256 GB SSD", "Windows 10 Pro")),
	"DT-OPT7010": ("Desktop Dell OptiPlex 7010", "Desktop", 4700, 0, "DT", ("Intel Core i7-13700", "16 GB", "512 GB SSD", "Windows 11 Pro")),
	"MN-LG24": ("Monitor LG 24MK430H 24\"", "Monitor", 850, 2, "MN", None),
	"IMP-M404": ("Impressora HP LaserJet Pro M404dw", "Impressora", 2300, 2, "IMP", None),
	"IMP-L5652": ("Multifuncional Brother DCP-L5652DN", "Impressora", 3100, 2, "IMP", None),
	"CEL-A52": ("Smartphone Samsung Galaxy A52", "Celular", 1900, 4, "CEL", None),
	"CEL-A54": ("Smartphone Samsung Galaxy A54", "Celular", 2100, 4, "CEL", None),
	"CEL-A55": ("Smartphone Samsung Galaxy A55", "Celular", 2300, 4, "CEL", None),
	"SW-USW24": ("Switch Ubiquiti UniFi USW-24-PoE", "Switch", 3400, 3, "SW", None),
	"FW-40F": ("Firewall Fortinet FortiGate 40F", "Firewall / Roteador", 4200, 3, "FW", None),
	"SRV-T140": ("Servidor Dell PowerEdge T140", "Servidor", 14500, 0, "SRV", None),
	"NBK-1500": ("Nobreak APC Smart-UPS 1500VA", "Nobreak", 3800, 3, "NBK", None),
	"PER-M90": ("Mouse USB Logitech M90", "Mouse", 45, 2, None, None),
	"PER-K120": ("Teclado USB Logitech K120", "Teclado", 75, 2, None, None),
}
GRUPO_DO_TIPO = {
	"Notebook": "TI - Notebooks", "Desktop": "TI - Desktops", "Monitor": "TI - Monitores", "Impressora": "TI - Impressoras",
	"Celular": "TI - Celulares", "Switch": "TI - Switches", "Firewall / Roteador": "TI - Firewalls", "Servidor": "TI - Servidores",
	"Nobreak": "TI - Nobreaks", "Mouse": "TI - Mouses", "Teclado": "TI - Teclados",
}  # fmt: skip
COMPRAS = {  # ano: [(mês, [(código, qtd), ...]), ...]
	2021: [(3, [("NB-LAT5410", 4), ("DT-OPT3080", 2)]), (6, [("IMP-M404", 1), ("SW-USW24", 1), ("NBK-1500", 1)])],
	2022: [(2, [("NB-E14G2", 3)]), (5, [("CEL-A52", 3)]), (9, [("SRV-T140", 1), ("FW-40F", 1)])],
	2023: [(3, [("NB-LAT5430", 4), ("MN-LG24", 3)]), (8, [("IMP-L5652", 1), ("PER-M90", 20), ("PER-K120", 15)])],
	2024: [(1, [("NB-LAT5440", 5)]), (4, [("DT-OPT7010", 2), ("CEL-A54", 3)]), (10, [("NBK-1500", 1), ("PER-M90", 10)])],
	2025: [(2, [("NB-E14G5", 3), ("MN-LG24", 2)]), (7, [("SW-USW24", 1), ("PER-K120", 10)])],
	2026: [(3, [("NB-LAT5450", 2), ("CEL-A55", 2)]), (8, [("PER-M90", 8)])],
}


def criar():
	if frappe.db.count("Equipamento TI"):
		print("O inventário de demonstração já existe (nada foi feito). Para recriar: solucoes.central_ti.demo_inventario.apagar e depois criar.")
		return
	random.seed(424)
	frappe.flags.mute_emails = True
	frappe.set_user("Administrator")
	empresa = frappe.defaults.get_global_default("company")
	_cadastros_erp(empresa)
	notas = _notas_de_compra(empresa)
	_equipamentos_das_compras()
	_entregar_e_configurar()
	_manutencoes()
	_ligar_chamados()
	_saidas_de_estoque()
	frappe.db.commit()
	configurar_orcamento()
	print(f"Inventário: {frappe.db.count('Equipamento TI')} equipamentos, {len(notas)} notas de compra lançadas, "
	      f"{frappe.db.count('Manutencao Equipamento TI')} manutenções/upgrades, {frappe.db.count('Item Estoque TI')} itens de estoque.")  # fmt: skip


def apagar():
	frappe.set_user("Administrator")
	for dt in ("Manutencao Equipamento TI", "Movimento Estoque TI"):
		frappe.db.delete(dt)
	frappe.db.sql("update `tabChamado TI` set equipamento=null")
	for nome in frappe.get_all("Equipamento TI", pluck="name"):
		frappe.delete_doc("Equipamento TI", nome, force=True, ignore_permissions=True)
	for nome in frappe.get_all("Item Estoque TI", pluck="name"):
		frappe.delete_doc("Item Estoque TI", nome, force=True, ignore_permissions=True)
	for nota in frappe.get_all("Purchase Invoice", filters={"supplier": ["in", FORNECEDORES], "docstatus": 1}, pluck="name"):
		doc = frappe.get_doc("Purchase Invoice", nota)
		doc.flags.ignore_links = True
		doc.cancel()
	for nota in frappe.get_all("Purchase Invoice", filters={"supplier": ["in", FORNECEDORES]}, pluck="name"):
		frappe.delete_doc("Purchase Invoice", nota, force=True, ignore_permissions=True)
	for t in frappe.get_all("Tipo Equipamento TI", pluck="name"):
		frappe.db.set_value("Tipo Equipamento TI", t, "grupo_item_erp", None)
	frappe.db.commit()
	print("Inventário de demonstração removido (itens, grupos e fornecedores do ERP mantidos).")


# ------------------------------------------------------------------ ERP
def _cadastros_erp(empresa):
	for ano in range(2021, 2027):
		if not frappe.db.exists("Fiscal Year", str(ano)):
			fy = frappe.get_doc({"doctype": "Fiscal Year", "year": str(ano), "year_start_date": f"{ano}-01-01", "year_end_date": f"{ano}-12-31"})
			fy.append("companies", {"company": empresa})
			fy.insert(ignore_permissions=True)
	if not frappe.db.exists("Item Group", RAIZ_GRUPO):
		frappe.get_doc({"doctype": "Item Group", "item_group_name": RAIZ_GRUPO, "parent_item_group": "All Item Groups", "is_group": 1}).insert()
	for tipo, grupo in GRUPO_DO_TIPO.items():
		if not frappe.db.exists("Item Group", grupo):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": grupo, "parent_item_group": RAIZ_GRUPO}).insert()
		frappe.db.set_value("Tipo Equipamento TI", tipo, "grupo_item_erp", grupo)
	for f in FORNECEDORES:
		if not frappe.db.exists("Supplier", f):
			frappe.get_doc({"doctype": "Supplier", "supplier_name": f, "supplier_group": "Local"}).insert()
	for codigo, (nome, tipo, *_resto) in CATALOGO.items():
		if not frappe.db.exists("Item", codigo):
			frappe.get_doc(
				{"doctype": "Item", "item_code": codigo, "item_name": nome, "item_group": GRUPO_DO_TIPO[tipo],
				 "stock_uom": "Unit", "is_stock_item": 0, "is_purchase_item": 1}
			).insert()  # fmt: skip


def _notas_de_compra(empresa):
	notas = []
	for ano, compras in COMPRAS.items():
		for mes, itens in compras:
			data = f"{ano}-{mes:02d}-{random.randint(3, 25):02d}"
			if getdate(data) > getdate(today()):
				continue
			por_fornecedor = defaultdict(list)
			for codigo, qtd in itens:
				por_fornecedor[FORNECEDORES[CATALOGO[codigo][3]]].append((codigo, qtd))
			for fornecedor, linhas in por_fornecedor.items():
				pi = frappe.get_doc(
					{
						"doctype": "Purchase Invoice", "supplier": fornecedor, "company": empresa, "set_posting_time": 1,
						"posting_date": data, "due_date": add_days(data, 30), "bill_no": f"NF-{random.randint(10000, 99999)}",
						"update_stock": 0,
						"items": [{"item_code": c, "qty": q, "rate": CATALOGO[c][2] * random.uniform(0.95, 1.05)} for c, q in linhas],
					}
				).insert(ignore_permissions=True)  # fmt: skip
				pi.submit()
				notas.append(pi.name)
	return notas


# ------------------------------------------------------------------ inventário
def _equipamentos_das_compras():
	"""Mesmo caminho da tela Compras de TI: cada linha de nota vira equipamentos (ou entrada no estoque)."""
	from solucoes.central_ti.api import inventario

	contador = defaultdict(int)
	for ano in COMPRAS:
		for item in inventario.compras(ano)["itens"]:
			if not item["pendentes"]:
				continue
			if item["controla_estoque"]:
				inventario.cadastrar_da_compra(item["linha"])
				continue
			prefixo = CATALOGO[item["item_code"]][4]
			nomes = []
			for _ in range(item["pendentes"]):
				contador[prefixo] += 1
				nomes.append(f"{prefixo}-{contador[prefixo]:03d}")
			inventario.cadastrar_da_compra(item["linha"], nomes)


def _entregar_e_configurar():
	pessoas = [(e, d) for e, _n, d in COLABORADORES] + [(e, "TI") for e, _n in TECNICOS]
	codigos = {v[0]: k for k, v in CATALOGO.items()}
	computadores = frappe.get_all("Equipamento TI", filters={"tipo": ["in", ["Notebook", "Desktop"]]}, fields=["name", "modelo", "data_compra"], order_by="data_compra desc")
	# os mais novos vão para as pessoas; os antigos ficam de reserva ou são descartados
	livres = list(pessoas)
	for e in computadores:
		doc = frappe.get_doc("Equipamento TI", e.name)
		cfg = CATALOGO[codigos[e.modelo]][5]
		doc.marca = e.modelo.split(" ")[1]
		doc.processador, doc.memoria_ram, doc.armazenamento, doc.sistema_operacional = cfg
		doc.numero_serie = f"SN{random.randint(1000000, 9999999)}"
		doc.patrimonio = f"PAT-{random.randint(1000, 9999)}"
		doc.garantia_ate = add_years(e.data_compra, 3 if "Latitude" in e.modelo else 1)
		if livres:
			email, depto = livres.pop(0)
			doc.responsavel, doc.departamento = email, depto
			doc.localizacao = depto
			doc.data_termo = add_days(e.data_compra, 5)
		elif e.name == "NB-001":
			doc.status = "Descartado"
			doc.observacoes = "Placa-mãe danificada; descartado com laudo."
		else:
			doc.localizacao = "Armário da TI (reserva)"
		doc.save(ignore_permissions=True)

	monitores = frappe.get_all("Equipamento TI", filters={"tipo": "Monitor"}, pluck="name")
	for i, nome in enumerate(monitores):
		email, depto = pessoas[i]
		_atualizar(nome, responsavel=email, departamento=depto, marca="LG", garantia_ate=None)
	celulares = frappe.get_all("Equipamento TI", filters={"tipo": "Celular"}, fields=["name", "data_compra"], order_by="data_compra desc")
	comerciais = [p for p in pessoas if p[1] in ("Comercial", "Logística", "TI", "Qualidade")]
	for i, c in enumerate(celulares):
		dados = {"marca": "Samsung", "imei": str(random.randint(10**14, 10**15 - 1)), "operadora": random.choice(["Vivo", "Claro"]),
		         "numero_linha": f"(11) 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}", "garantia_ate": add_years(c.data_compra, 1)}  # fmt: skip
		if i < len(comerciais):
			dados.update({"responsavel": comerciais[i][0], "departamento": comerciais[i][1]})
		_atualizar(c.name, **dados)
	locais = {"Impressora": ["Laboratório Físico-Químico", "Recepção / Administrativo"], "Switch": ["Rack - Sala de TI"], "Firewall / Roteador": ["Rack - Sala de TI"],
	          "Servidor": ["Rack - Sala de TI"], "Nobreak": ["Rack - Sala de TI"]}  # fmt: skip
	for tipo, lugares in locais.items():
		for i, nome in enumerate(frappe.get_all("Equipamento TI", filters={"tipo": tipo}, pluck="name", order_by="name")):
			extra = {"endereco_ip": f"192.168.10.{10 + i + 20 * list(locais).index(tipo)}", "endereco_mac": ":".join(f"{random.randint(0, 255):02X}" for _ in range(6))}
			if tipo == "Servidor":
				extra["especificacoes"] = "Xeon E-2224 · 32 GB ECC · 2x 2 TB RAID 1 · Windows Server 2022"
			_atualizar(nome, status="Em Uso", localizacao=lugares[i % len(lugares)], departamento="TI" if "Rack" in lugares[0] else lugares[i % len(lugares)],
			           marca=frappe.db.get_value("Equipamento TI", nome, "modelo").split(" ")[1 if tipo != "Impressora" else 1], **extra)  # fmt: skip


def _atualizar(nome, **campos):
	doc = frappe.get_doc("Equipamento TI", nome)
	doc.update(campos)
	doc.save(ignore_permissions=True)


def _manutencao(equipamento, data, tipo, descricao, custo=0, componente=None, valor_novo=None, fornecedor=None, chamado=None, tecnico=None):
	frappe.set_user(tecnico or random.choice(TECNICOS)[0])
	frappe.get_doc(
		{"doctype": "Manutencao Equipamento TI", "equipamento": equipamento, "data": data, "tipo": tipo, "descricao": descricao,
		 "custo": custo, "componente": componente, "valor_novo": valor_novo, "fornecedor": fornecedor, "chamado": chamado}
	).insert(ignore_permissions=True)  # fmt: skip
	frappe.set_user("Administrator")


def _manutencoes():
	antigos = frappe.get_all("Equipamento TI", filters={"modelo": ["like", "%5410%"], "status": ["!=", "Descartado"]}, pluck="name", order_by="name")
	antigos += frappe.get_all("Equipamento TI", filters={"modelo": ["like", "%E14 Gen 2%"]}, pluck="name", order_by="name")
	antigos += frappe.get_all("Equipamento TI", filters={"modelo": ["like", "%OptiPlex 3080%"]}, pluck="name", order_by="name")
	for i, nome in enumerate(antigos):
		base = add_months(frappe.db.get_value("Equipamento TI", nome, "data_compra"), 18 + i)
		_manutencao(nome, base, "Upgrade", "Upgrade de memória para melhorar desempenho no ERP e Teams.", custo=random.choice([260, 290, 320]),
		            componente="Memória RAM", valor_novo="16 GB", fornecedor="Kalunga Empresas")  # fmt: skip
		if i % 2 == 0:
			_manutencao(nome, add_months(base, 6), "Upgrade", "Troca do SSD por um de 512 GB (disco cheio).", custo=340,
			            componente="Armazenamento", valor_novo="512 GB SSD", fornecedor="Kalunga Empresas")  # fmt: skip
		if "5410" in (frappe.db.get_value("Equipamento TI", nome, "modelo") or ""):
			_manutencao(nome, add_months(base, 10), "Troca de Peça", "Bateria não segurava carga: substituída.", custo=410, fornecedor="Assistência Dell")
			_manutencao(nome, add_months(base, 14), "Manutenção Corretiva", "Dobradiça da tela quebrada.", custo=380, fornecedor="Assistência Dell")
		if frappe.db.get_value("Equipamento TI", nome, "sistema_operacional") == "Windows 10 Pro":
			_manutencao(nome, add_months(base, 3), "Formatação / Reinstalação", "Migração para o Windows 11 (fim do suporte do Windows 10).",
			            componente="Sistema Operacional", valor_novo="Windows 11 Pro")  # fmt: skip
	for nome in frappe.get_all("Equipamento TI", filters={"tipo": "Impressora"}, pluck="name"):
		_manutencao(nome, add_months(frappe.db.get_value("Equipamento TI", nome, "data_compra"), 20), "Manutenção Preventiva", "Limpeza e troca do kit de manutenção.", custo=450, fornecedor="HP Service")
		_manutencao(nome, add_months(frappe.db.get_value("Equipamento TI", nome, "data_compra"), 30), "Troca de Peça", "Fusor com defeito (manchas na impressão).", custo=680, fornecedor="HP Service")
	_manutencao("NBK-001", "2025-03-12", "Troca de Peça", "Troca das baterias internas do nobreak (autonomia caiu para 3 min).", custo=890, fornecedor="APC Service")
	_manutencao("SRV-001", "2025-09-02", "Manutenção Preventiva", "Atualização de firmware/BIOS e verificação do RAID.")


def _ligar_chamados():
	"""Chamados de computador/impressora apontam para o equipamento do solicitante (ou a impressora)."""
	impressoras = frappe.get_all("Equipamento TI", filters={"tipo": "Impressora"}, pluck="name")
	for c in frappe.get_all("Chamado TI", filters={"categoria": ["in", ["Computador e Notebook", "Impressora e Scanner"]]}, fields=["name", "categoria", "solicitante"]):
		if c.categoria == "Impressora e Scanner" and impressoras:
			eqp = random.choice(impressoras)
		else:
			eqp = frappe.db.get_value("Equipamento TI", {"responsavel": c.solicitante, "tipo": ["in", ["Notebook", "Desktop"]]})
		if eqp:
			frappe.db.set_value("Chamado TI", c.name, "equipamento", eqp, update_modified=False)
	from solucoes.central_ti.doctype.equipamento_ti.equipamento_ti import recalcular

	for nome in frappe.get_all("Equipamento TI", pluck="name"):
		recalcular(nome)


def _saidas_de_estoque():
	pessoas = [e for e, _n, _d in COLABORADORES]
	for item, saidas in (("Mouse USB Logitech M90", 24), ("Teclado USB Logitech K120", 24)):
		if not frappe.db.exists("Item Estoque TI", item):
			continue
		frappe.db.set_value("Item Estoque TI", item, {"minimo": 5, "localizacao": "Armário da TI"})
		for i in range(saidas):
			if frappe.db.get_value("Item Estoque TI", item, "quantidade") <= 0:
				break
			frappe.get_doc(
				{"doctype": "Movimento Estoque TI", "item": item, "tipo": "Saída", "quantidade": 1, "para_usuario": pessoas[i % len(pessoas)],
				 "data": f"{add_days(today(), -random.randint(1, 600))} 10:00:00", "observacao": "Substituição por desgaste"}
			).insert(ignore_permissions=True)  # fmt: skip


def configurar_orcamento():
	"""Orçamento de exemplo (2024–2026), 25 colaboradores e o link da TV."""
	cfg = frappe.get_doc("Configuracao Central TI")
	if not cfg.orcamentos:
		for ano, compras, manut in ((2024, 60000, 4000), (2025, 45000, 4500), (2026, 50000, 5000)):
			cfg.append("orcamentos", {"ano": ano, "compras": compras, "manutencoes": manut})
	cfg.numero_colaboradores = cfg.numero_colaboradores or 25
	cfg.flags.ignore_permissions = True
	cfg.save()
	if not cfg.tv_chave:
		import secrets

		frappe.db.set_single_value("Configuracao Central TI", {"tv_chave": secrets.token_urlsafe(24), "tv_ativo": 1})
	frappe.db.commit()
	print("Orçamento de exemplo e link da TV configurados.")
