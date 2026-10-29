"""Inventário de TI: equipamentos, manutenções/upgrades, estoque, compras (do ERPNext) e visão do gestor.

Compras: lidas das Notas de Compra (Purchase Invoice) lançadas, nos itens cujos Grupos de Item
estão ligados a um "Tipo Equipamento TI". Nada é gravado nos DocTypes do ERP.
"""

import json
from collections import Counter, defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, getdate, today
from frappe.utils.nestedset import get_descendants_of

from solucoes.central_ti.api.central import _exigir_tecnico, _nome, _usuario
from solucoes.central_ti.doctype.equipamento_ti.equipamento_ti import INATIVOS

CAMPOS_EDITAVEIS = (
	"nome", "tipo", "status", "marca", "modelo", "numero_serie", "patrimonio", "responsavel", "departamento",
	"localizacao", "data_termo", "processador", "memoria_ram", "armazenamento", "sistema_operacional",
	"endereco_ip", "endereco_mac", "firmware", "imei", "numero_linha", "operadora", "especificacoes",
	"data_compra", "valor_compra", "fornecedor", "garantia_ate", "observacoes",
)  # fmt: skip


def _json(valor, padrao=None):
	if isinstance(valor, str):
		return json.loads(valor) if valor else padrao
	return valor if valor is not None else padrao


def _tipos():
	return {t.name: t for t in frappe.get_all("Tipo Equipamento TI", fields=["name", "grupo", "icone", "vida_util_anos", "grupo_item_erp", "controla_estoque"])}


def _alertas(e, hoje=None):
	hoje = hoje or getdate(today())
	alertas = []
	if e.status in INATIVOS:
		return alertas
	if e.fim_vida_util and getdate(e.fim_vida_util) <= hoje:
		alertas.append("Vida útil vencida")
	elif e.fim_vida_util and date_diff(e.fim_vida_util, hoje) <= 180:
		alertas.append("Vida útil acaba em breve")
	if e.garantia_ate and getdate(e.garantia_ate) < hoje:
		alertas.append("Fora da garantia")
	elif e.garantia_ate and date_diff(e.garantia_ate, hoje) <= 60:
		alertas.append("Garantia vence em breve")
	return alertas


def _idade_anos(data_compra):
	return round(date_diff(today(), data_compra) / 365.25, 1) if data_compra else None


def _linha(e, tipos):
	t = tipos.get(e.tipo) or {}
	return {
		"id": e.name,
		"nome": e.name,
		"tipo": e.tipo,
		"grupo": t.get("grupo") or e.grupo,
		"icone": t.get("icone") or "package",
		"status": e.status,
		"marca": e.marca,
		"modelo": e.modelo,
		"numero_serie": e.numero_serie,
		"patrimonio": e.patrimonio,
		"responsavel": e.responsavel,
		"responsavel_nome": e.responsavel_nome,
		"departamento": e.departamento,
		"localizacao": e.localizacao,
		"resumo": " · ".join(x for x in (e.processador, e.memoria_ram, e.armazenamento) if x) or e.endereco_ip or e.numero_linha or "",
		"data_compra": str(e.data_compra) if e.data_compra else None,
		"idade_anos": _idade_anos(e.data_compra),
		"garantia_ate": str(e.garantia_ate) if e.garantia_ate else None,
		"fim_vida_util": str(e.fim_vida_util) if e.fim_vida_util else None,
		"valor_compra": flt(e.valor_compra),
		"custo_total": flt(e.custo_total),
		"qtd_chamados": cint(e.qtd_chamados),
		"qtd_manutencoes": cint(e.qtd_manutencoes),
		"alertas": _alertas(e),
	}


CAMPOS_LISTA = [
	"name", "tipo", "grupo", "status", "marca", "modelo", "numero_serie", "patrimonio", "responsavel", "responsavel_nome",
	"departamento", "localizacao", "processador", "memoria_ram", "armazenamento", "endereco_ip", "numero_linha",
	"data_compra", "garantia_ate", "fim_vida_util", "valor_compra", "custo_total", "qtd_chamados", "qtd_manutencoes",
]  # fmt: skip


# ===================================================================== equipamentos
@frappe.whitelist()
def tipos():
	_exigir_tecnico()
	contagem = Counter(frappe.get_all("Equipamento TI", filters={"status": ["not in", INATIVOS]}, pluck="tipo"))
	return [
		{"id": t.name, "grupo": t.grupo, "icone": t.icone, "vida_util_anos": t.vida_util_anos, "controla_estoque": bool(t.controla_estoque),
		 "grupo_item_erp": t.grupo_item_erp, "quantidade": contagem.get(t.name, 0)}
		for t in _tipos().values()
	]  # fmt: skip


@frappe.whitelist()
def inventario(busca=None, tipo=None, grupo=None, status=None, departamento=None, incluir_inativos=0):
	_exigir_tecnico()
	f = {}
	if not cint(incluir_inativos) and not status:
		f["status"] = ["not in", INATIVOS]
	for campo, valor in (("tipo", tipo), ("grupo", grupo), ("status", status), ("departamento", departamento)):
		if valor:
			f[campo] = valor
	ou = None
	if busca:
		like = f"%{busca}%"
		ou = {c: ["like", like] for c in ("name", "modelo", "numero_serie", "patrimonio", "responsavel_nome", "departamento", "endereco_ip")}
	tipos_ = _tipos()
	return [_linha(e, tipos_) for e in frappe.get_all("Equipamento TI", filters=f, or_filters=ou, fields=CAMPOS_LISTA, order_by="name asc", limit=2000)]


@frappe.whitelist()
def equipamento(id):
	_exigir_tecnico()
	if not frappe.db.exists("Equipamento TI", id):
		raise frappe.DoesNotExistError(_("Equipamento não encontrado."))
	e = frappe.get_doc("Equipamento TI", id)
	dados = _linha(e, _tipos())
	dados.update({c: e.get(c) for c in CAMPOS_EDITAVEIS if c not in dados})
	dados.update(
		{
			"custo_manutencoes": flt(e.custo_manutencoes),
			"nota_compra": e.nota_compra,
			"ativo_erp": e.ativo_erp,
			"tem_termo": bool(e.termo_responsabilidade),
			"historico_responsaveis": [
				{"data": str(h.data), "nome": h.responsavel_nome, "departamento": h.departamento, "por": _nome(h.registrado_por)}
				for h in reversed(e.historico_responsaveis)
			],
			"manutencoes": frappe.get_all(
				"Manutencao Equipamento TI",
				filters={"equipamento": id},
				fields=["name as id", "data", "tipo", "componente", "valor_anterior", "valor_novo", "descricao", "custo", "fornecedor", "executado_por", "chamado"],
				order_by="data desc, creation desc",
			),
			"chamados": frappe.get_all(
				"Chamado TI",
				filters={"equipamento": id},
				fields=["name as id", "assunto", "status", "aberto_em", "nome_solicitante", "prioridade"],
				order_by="aberto_em desc",
				limit=50,
			),
		}
	)
	for m in dados["manutencoes"]:
		m["executado_por_nome"] = _nome(m.pop("executado_por"))
		m["data"] = str(m["data"])
	for c in dados["chamados"]:
		c["aberto_em"] = str(c["aberto_em"])
	return dados


@frappe.whitelist(methods=["POST"])
def salvar_equipamento(dados, id=None):
	_exigir_tecnico()
	dados = _json(dados, {})
	doc = frappe.get_doc("Equipamento TI", id) if id else frappe.new_doc("Equipamento TI")
	doc.update({k: (v if v != "" else None) for k, v in dados.items() if k in CAMPOS_EDITAVEIS and (k != "nome" or not id)})
	doc.flags.ignore_permissions = True
	doc.save()
	return equipamento(doc.name)


@frappe.whitelist(methods=["POST"])
def registrar_manutencao(equipamento_id, dados):
	_exigir_tecnico()
	dados = _json(dados, {})
	frappe.get_doc(
		{
			"doctype": "Manutencao Equipamento TI",
			"equipamento": equipamento_id,
			"data": dados.get("data") or today(),
			"tipo": dados.get("tipo") or "Upgrade",
			"componente": dados.get("componente") or None,
			"valor_novo": dados.get("valor_novo"),
			"descricao": dados.get("descricao"),
			"custo": flt(dados.get("custo")),
			"fornecedor": dados.get("fornecedor"),
			"chamado": dados.get("chamado") or None,
			"executado_por": frappe.session.user,
		}
	).insert(ignore_permissions=True)
	return equipamento(equipamento_id)


@frappe.whitelist()
def buscar_equipamentos(texto=None, usuario=None):
	"""Para vincular ao chamado: técnico busca em todos; colaborador só vê os seus."""
	sessao = _usuario()
	from solucoes.central_ti.api.central import eh_tecnico

	f = {"status": ["not in", INATIVOS]}
	if not eh_tecnico(sessao):
		f["responsavel"] = sessao
	elif usuario:
		f["responsavel"] = usuario
	ou = None
	if texto:
		like = f"%{texto}%"
		ou = {"name": ["like", like], "modelo": ["like", like], "responsavel_nome": ["like", like]}
	tipos_ = _tipos()
	return [
		{"id": e.name, "tipo": e.tipo, "icone": (tipos_.get(e.tipo) or {}).get("icone") or "package", "modelo": e.modelo, "responsavel_nome": e.responsavel_nome}
		for e in frappe.get_all("Equipamento TI", filters=f, or_filters=ou, fields=["name", "tipo", "modelo", "responsavel_nome"], limit=20, order_by="name")
	]


@frappe.whitelist()
def meus_equipamentos():
	usuario = _usuario()
	tipos_ = _tipos()
	return [
		_linha(e, tipos_)
		for e in frappe.get_all("Equipamento TI", filters={"responsavel": usuario, "status": ["not in", INATIVOS]}, fields=CAMPOS_LISTA, order_by="name")
	]


# ===================================================================== estoque
@frappe.whitelist()
def estoque():
	_exigir_tecnico()
	itens = frappe.get_all("Item Estoque TI", filters={"ativo": 1}, fields=["name as id", "tipo", "quantidade", "minimo", "localizacao"], order_by="name")
	tipos_ = _tipos()
	for i in itens:
		i["icone"] = (tipos_.get(i["tipo"]) or {}).get("icone") or "package"
		i["abaixo_minimo"] = cint(i["quantidade"]) < cint(i["minimo"])
	movimentos = frappe.get_all(
		"Movimento Estoque TI",
		fields=["name as id", "item", "tipo", "quantidade", "data", "para_usuario", "chamado", "saldo_apos", "observacao", "owner"],
		order_by="data desc, creation desc",
		limit=40,
	)
	for m in movimentos:
		m["data"] = str(m["data"])
		m["para_nome"] = _nome(m["para_usuario"])
		m["por_nome"] = _nome(m.pop("owner"))
	return {"itens": itens, "movimentos": movimentos}


@frappe.whitelist(methods=["POST"])
def movimentar_estoque(item, tipo, quantidade, para_usuario=None, chamado=None, observacao=None):
	_exigir_tecnico()
	frappe.get_doc(
		{
			"doctype": "Movimento Estoque TI",
			"item": item,
			"tipo": tipo,
			"quantidade": cint(quantidade),
			"para_usuario": para_usuario or None,
			"chamado": chamado or None,
			"observacao": observacao,
		}
	).insert(ignore_permissions=True)
	return estoque()


@frappe.whitelist(methods=["POST"])
def salvar_item_estoque(nome, tipo=None, minimo=2, localizacao=None, quantidade_inicial=0):
	_exigir_tecnico()
	if frappe.db.exists("Item Estoque TI", nome):
		doc = frappe.get_doc("Item Estoque TI", nome)
		doc.update({"tipo": tipo or doc.tipo, "minimo": cint(minimo), "localizacao": localizacao})
		doc.save(ignore_permissions=True)
	else:
		frappe.get_doc({"doctype": "Item Estoque TI", "nome": nome, "tipo": tipo, "minimo": cint(minimo), "localizacao": localizacao}).insert(
			ignore_permissions=True
		)
		if cint(quantidade_inicial) > 0:
			frappe.get_doc(
				{"doctype": "Movimento Estoque TI", "item": nome, "tipo": "Entrada", "quantidade": cint(quantidade_inicial), "observacao": _("Saldo inicial")}
			).insert(ignore_permissions=True)
	return estoque()


# ===================================================================== compras (ERPNext)
def _grupos_mapeados():
	"""{Item Group (e descendentes): tipo TI}. O grupo mais específico prevalece."""
	mapa = {}
	tipos_ = [t for t in _tipos().values() if t.grupo_item_erp]
	largura = {}
	for t in tipos_:
		lft, rgt = frappe.db.get_value("Item Group", t.grupo_item_erp, ["lft", "rgt"]) or (0, 0)
		largura[t.name] = (rgt or 0) - (lft or 0)
	for t in sorted(tipos_, key=lambda t: -largura[t.name]):  # mais amplo primeiro; os específicos sobrescrevem
		for g in [t.grupo_item_erp, *get_descendants_of("Item Group", t.grupo_item_erp)]:
			mapa[g] = t.name
	return mapa


def _itens_comprados(grupos, ano=None):
	pi = frappe.qb.DocType("Purchase Invoice")
	pii = frappe.qb.DocType("Purchase Invoice Item")
	q = (
		frappe.qb.from_(pii)
		.join(pi)
		.on(pii.parent == pi.name)
		.select(
			pii.name.as_("linha"), pi.name.as_("nota"), pi.posting_date.as_("data"), pi.supplier_name.as_("fornecedor"),
			pii.item_code, pii.item_name, pii.item_group, pii.qty, pii.base_net_rate.as_("valor_unitario"),
			pii.base_net_amount.as_("valor_total"),
		)  # fmt: skip
		.where((pi.docstatus == 1) & (pi.is_return == 0) & (pii.item_group.isin(list(grupos) or [""])))
		.orderby(pi.posting_date, order=frappe.qb.desc)
	)
	if ano:
		q = q.where((pi.posting_date >= f"{ano}-01-01") & (pi.posting_date <= f"{ano}-12-31"))
	return q.run(as_dict=True)


@frappe.whitelist()
def compras(ano=None):
	_exigir_tecnico()
	mapa = _grupos_mapeados()
	if not mapa:
		return {"configurado": False, "anos": [], "itens": [], "resumo": {}}
	todos = _itens_comprados(mapa)
	anos = sorted({getdate(i.data).year for i in todos}, reverse=True) or [getdate(today()).year]
	ano = cint(ano) or anos[0]
	itens = [i for i in todos if getdate(i.data).year == ano]
	tipos_ = _tipos()

	linhas = [i.linha for i in itens]
	cadastrados = Counter(frappe.get_all("Equipamento TI", filters={"item_nota": ["in", linhas or [""]]}, pluck="item_nota"))
	for m in frappe.get_all("Movimento Estoque TI", filters={"item_nota": ["in", linhas or [""]]}, fields=["item_nota", "quantidade"]):
		cadastrados[m.item_nota] += cint(m.quantidade)

	saida = []
	for i in itens:
		tipo = mapa.get(i.item_group)
		qtd = cint(i.qty)
		saida.append(
			{
				**{k: (str(v) if k == "data" else v) for k, v in i.items()},
				"qtd": qtd,
				"tipo": tipo,
				"grupo": (tipos_.get(tipo) or {}).get("grupo"),
				"icone": (tipos_.get(tipo) or {}).get("icone") or "package",
				"controla_estoque": bool((tipos_.get(tipo) or {}).get("controla_estoque")),
				"cadastrados": min(cadastrados.get(i.linha, 0), qtd),
				"pendentes": max(qtd - cadastrados.get(i.linha, 0), 0),
			}
		)
	por_grupo, por_mes = defaultdict(float), defaultdict(float)
	for s in saida:
		por_grupo[s["grupo"] or "Outro"] += flt(s["valor_total"])
		por_mes[str(s["data"])[5:7]] += flt(s["valor_total"])
	return {
		"configurado": True,
		"ano": ano,
		"anos": anos,
		"itens": saida,
		"resumo": {
			"total": sum(flt(s["valor_total"]) for s in saida),
			"notas": len({s["nota"] for s in saida}),
			"pendentes": sum(s["pendentes"] for s in saida),
			"por_grupo": sorted(por_grupo.items(), key=lambda kv: -kv[1]),
			"por_mes": [round(por_mes.get(f"{m:02d}", 0), 2) for m in range(1, 13)],
		},
	}


@frappe.whitelist(methods=["POST"])
def cadastrar_da_compra(linha, nomes=None):
	"""Cria os equipamentos (ou a entrada no estoque) de uma linha de Nota de Compra."""
	_exigir_tecnico()
	mapa = _grupos_mapeados()
	item = next((i for i in _itens_comprados(mapa) if i.linha == linha), None)
	if not item:
		frappe.throw(_("Item de compra não encontrado ou não pertence a um grupo de TI."))
	tipo = mapa[item.item_group]
	tipo_doc = _tipos()[tipo]
	ja = frappe.db.count("Equipamento TI", {"item_nota": linha}) + sum(
		cint(q) for q in frappe.get_all("Movimento Estoque TI", filters={"item_nota": linha}, pluck="quantidade")
	)
	pendentes = cint(item.qty) - ja
	if pendentes <= 0:
		frappe.throw(_("Todos os itens desta compra já foram cadastrados."))

	if tipo_doc.controla_estoque:
		nome_item = item.item_name
		if not frappe.db.exists("Item Estoque TI", nome_item):
			frappe.get_doc({"doctype": "Item Estoque TI", "nome": nome_item, "tipo": tipo, "minimo": 2}).insert(ignore_permissions=True)
		frappe.get_doc(
			{"doctype": "Movimento Estoque TI", "item": nome_item, "tipo": "Entrada", "quantidade": pendentes,
			 "nota_compra": item.nota, "item_nota": linha, "observacao": _("Compra {0}").format(item.nota)}
		).insert(ignore_permissions=True)  # fmt: skip
		return {"estoque": nome_item, "quantidade": pendentes}

	nomes = [n.strip().upper() for n in _json(nomes, []) if n and n.strip()]
	if not nomes:
		frappe.throw(_("Informe o nome (hostname/identificação) de cada equipamento."))
	if len(nomes) > pendentes:
		frappe.throw(_("Esta compra só tem {0} item(ns) pendente(s).").format(pendentes))
	criados = []
	for nome in nomes:
		frappe.get_doc(
			{
				"doctype": "Equipamento TI", "nome": nome, "tipo": tipo, "status": "Em Estoque",
				"modelo": item.item_name, "data_compra": item.data, "valor_compra": flt(item.valor_unitario),
				"fornecedor": item.fornecedor, "nota_compra": item.nota, "item_nota": linha,
			}
		).insert(ignore_permissions=True)  # fmt: skip
		criados.append(nome)
	return {"equipamentos": criados}


# ===================================================================== visão do gestor
@frappe.whitelist()
def gestao():
	_exigir_tecnico()
	hoje = getdate(today())
	tipos_ = _tipos()
	todos = frappe.get_all("Equipamento TI", fields=CAMPOS_LISTA + ["custo_manutencoes"], limit_page_length=0)
	ativos = [e for e in todos if e.status not in INATIVOS]

	def ano_vida(e):
		return getdate(e.fim_vida_util).year if e.fim_vida_util else None

	idades = [_idade_anos(e.data_compra) for e in ativos if e.data_compra]
	vencidos_vida = [e for e in ativos if e.fim_vida_util and getdate(e.fim_vida_util) <= hoje]
	fora_garantia = [e for e in ativos if e.garantia_ate and getdate(e.garantia_ate) < hoje]

	# plano de renovação: o que vence a vida útil em cada ano, ao preço pago (estimativa de reposição)
	plano = {}
	for e in ativos:
		ano = ano_vida(e)
		if ano is None:
			continue
		chave = "Já vencidos" if getdate(e.fim_vida_util) <= hoje else str(ano)
		if chave != "Já vencidos" and ano > hoje.year + 3:
			continue
		p = plano.setdefault(chave, {"ano": chave, "quantidade": 0, "valor": 0.0, "por_tipo": Counter()})
		p["quantidade"] += 1
		p["valor"] += flt(e.valor_compra)
		p["por_tipo"][e.tipo] += 1
	ordem = ["Já vencidos"] + [str(a) for a in range(hoje.year, hoje.year + 4)]
	plano_lista = [{**plano[k], "por_tipo": dict(plano[k]["por_tipo"])} for k in ordem if k in plano]

	# gastos por ano: compras de TI (ERP) + manutenções
	mapa = _grupos_mapeados()
	gastos = defaultdict(lambda: {"compras": 0.0, "manutencoes": 0.0})
	for i in _itens_comprados(mapa) if mapa else []:
		ano = getdate(i.data).year
		if ano >= hoje.year - 4:
			gastos[ano]["compras"] += flt(i.valor_total)
	for m in frappe.get_all("Manutencao Equipamento TI", fields=["data", "custo"]):
		ano = getdate(m.data).year
		if ano >= hoje.year - 4:
			gastos[ano]["manutencoes"] += flt(m.custo)

	# confiabilidade por modelo: chamados + manutenções corretivas por unidade
	corretivas = Counter(
		frappe.get_all(
			"Manutencao Equipamento TI", filters={"tipo": ["in", ["Manutenção Corretiva", "Troca de Peça"]]}, pluck="equipamento"
		)
	)
	por_modelo = defaultdict(lambda: {"unidades": 0, "chamados": 0, "corretivas": 0, "custo_manutencao": 0.0})
	for e in todos:
		if not e.modelo:
			continue
		m = por_modelo[e.modelo]
		m["unidades"] += 1
		m["chamados"] += cint(e.qtd_chamados)
		m["corretivas"] += corretivas.get(e.name, 0)
		m["custo_manutencao"] += flt(e.custo_manutencoes)
	modelos = sorted(
		({"modelo": k, **v, "indice": round((v["chamados"] + v["corretivas"]) / v["unidades"], 1)} for k, v in por_modelo.items()),
		key=lambda m: (-m["indice"], -m["unidades"]),
	)[:8]

	estoque_baixo = [
		i for i in frappe.get_all("Item Estoque TI", filters={"ativo": 1}, fields=["name as id", "quantidade", "minimo"]) if cint(i.quantidade) < cint(i.minimo)
	]
	return {
		"kpis": {
			"equipamentos": len(ativos),
			"em_uso": sum(1 for e in ativos if e.status == "Em Uso"),
			"em_estoque": sum(1 for e in ativos if e.status == "Em Estoque"),
			"em_manutencao": sum(1 for e in ativos if e.status == "Em Manutenção"),
			"idade_media": round(sum(idades) / len(idades), 1) if idades else None,
			"vida_util_vencida": len(vencidos_vida),
			"fora_garantia": len(fora_garantia),
			"valor_parque": round(sum(flt(e.valor_compra) for e in ativos), 2),
			"custo_manutencao_12m": round(
				sum(flt(m.custo) for m in frappe.get_all("Manutencao Equipamento TI", filters={"data": [">=", add_days(hoje, -365)]}, fields=["custo"])), 2
			),
			"estoque_baixo": len(estoque_baixo),
			"sem_responsavel_em_uso": sum(1 for e in ativos if e.status == "Em Uso" and not e.responsavel),
		},
		"por_grupo": Counter((tipos_.get(e.tipo) or {}).get("grupo") or "Outro" for e in ativos).most_common(),
		"por_status": Counter(e.status for e in ativos).most_common(),
		"por_departamento": Counter(e.departamento or "Sem departamento" for e in ativos if e.status == "Em Uso").most_common(10),
		"idade_por_grupo": [
			{"grupo": g, "idade": round(sum(v) / len(v), 1)}
			for g, v in _agrupar(((tipos_.get(e.tipo) or {}).get("grupo") or "Outro", _idade_anos(e.data_compra)) for e in ativos if e.data_compra).items()
		],
		"plano_renovacao": plano_lista,
		"gastos_por_ano": [{"ano": a, **gastos[a]} for a in sorted(gastos)],
		"top_custo": [_linha(e, tipos_) for e in sorted(ativos, key=lambda e: -flt(e.custo_total))[:8]],
		"modelos": modelos,
		"vida_util_vencida": [_linha(e, tipos_) for e in sorted(vencidos_vida, key=lambda e: str(e.fim_vida_util))[:12]],
		"estoque_baixo": estoque_baixo,
		"orcamento": _orcado_realizado(gastos),
		"custo_por_colaborador": _custo_por_colaborador(gastos, hoje.year),
	}


def _orcado_realizado(gastos):
	"""Orçamento da configuração x realizado (compras do ERP e manutenções), por ano."""
	cfg = frappe.get_cached_doc("Configuracao Central TI")
	saida = []
	for o in sorted(cfg.orcamentos or [], key=lambda o: o.ano):
		real = gastos.get(cint(o.ano)) or {"compras": 0.0, "manutencoes": 0.0}
		orcado = flt(o.compras) + flt(o.manutencoes)
		realizado = flt(real["compras"]) + flt(real["manutencoes"])
		saida.append(
			{
				"ano": cint(o.ano),
				"orcado_compras": flt(o.compras),
				"orcado_manutencoes": flt(o.manutencoes),
				"realizado_compras": round(flt(real["compras"]), 2),
				"realizado_manutencoes": round(flt(real["manutencoes"]), 2),
				"orcado": orcado,
				"realizado": round(realizado, 2),
				"uso_pct": round(100 * realizado / orcado, 1) if orcado else None,
			}
		)
	return saida


def _numero_colaboradores():
	cfg = frappe.get_cached_doc("Configuracao Central TI")
	if cint(cfg.numero_colaboradores):
		return cint(cfg.numero_colaboradores), "configuração"
	if frappe.db.table_exists("Employee"):
		ativos = frappe.db.count("Employee", {"status": "Active"})
		if ativos:
			return ativos, "funcionários ativos do ERP"
	return None, None


def _custo_por_colaborador(gastos, ano):
	numero, origem = _numero_colaboradores()
	if not numero:
		return {"colaboradores": None, "origem": None, "anos": []}
	anos = [a for a in (ano - 1, ano) if a in gastos]
	return {
		"colaboradores": numero,
		"origem": origem,
		"anos": [{"ano": a, "valor": round((gastos[a]["compras"] + gastos[a]["manutencoes"]) / numero, 2)} for a in anos],
	}


def _agrupar(pares):
	saida = defaultdict(list)
	for chave, valor in pares:
		saida[chave].append(valor)
	return saida
