"""Regras fiscais: o que emitir a partir de uma fatura (ou de uma remessa) e a conferência em linguagem simples.

Cada conferência devolve itens no formato
	{"nivel": "ok" | "info" | "aviso" | "erro", "texto": ..., "dica": ..., "acao": "cadastro" | "config" | "item:<código>" | None}
"erro" impede a emissão; "aviso" só alerta. As alíquotas e CFOPs vêm da configuração e das naturezas,
que o contador valida — nada de imposto fica escrito no código.
"""

import json

import frappe
from frappe.utils import add_days, flt, getdate, today

from solucoes.fiscal import util

CONFIG = "Configuracao Fiscal"
CAMPOS_ENDERECO = (("logradouro", "rua"), ("numero", "número"), ("bairro", "bairro"), ("cep", "CEP"),
                   ("municipio", "município"), ("codigo_municipio", "código IBGE do município"), ("uf", "UF"))  # fmt: skip


def config():
	return frappe.get_cached_doc(CONFIG)


def item(nivel, texto, dica=None, acao=None):
	return {"nivel": nivel, "texto": texto, "dica": dica, "acao": acao}


def simulacao(cfg=None):
	return (cfg or config()).ambiente == "Simulação"


# ===================================================================== cadastros
def dados_parte(tipo_parte, parte):
	nome = frappe.db.get_value("Dados Fiscais Parte", {"tipo_parte": tipo_parte, "parte": parte}, "name")
	return frappe.get_doc("Dados Fiscais Parte", nome) if nome else None


def sugestao_dados_parte(tipo_parte, parte):
	"""Pré-preenche o cadastro fiscal com o que o ERP já sabe (CNPJ, endereço principal, e-mail)."""
	campo_nome = "customer_name" if tipo_parte == "Customer" else "supplier_name"
	base = frappe.db.get_value(tipo_parte, parte, [campo_nome, "tax_id"], as_dict=True) or {}
	dados = {"tipo_parte": tipo_parte, "parte": parte, "razao_social": base.get(campo_nome) or parte, "cnpj_cpf": base.get("tax_id") or ""}
	dados["tipo_pessoa"] = "Física" if len(util.limpar_documento(dados["cnpj_cpf"])) == 11 else "Jurídica"
	link = frappe.qb.DocType("Dynamic Link")
	endereco = frappe.qb.DocType("Address")
	linhas = (
		frappe.qb.from_(endereco).join(link).on(link.parent == endereco.name)
		.select(endereco.address_line1, endereco.address_line2, endereco.city, endereco.state, endereco.pincode, endereco.email_id)
		.where((link.link_doctype == tipo_parte) & (link.link_name == parte) & (link.parenttype == "Address"))
		.orderby(endereco.is_primary_address, order=frappe.qb.desc).limit(1).run(as_dict=True)
	)  # fmt: skip
	if linhas:
		e = linhas[0]
		dados.update({"logradouro": e.address_line1, "complemento": e.address_line2, "municipio": e.city, "cep": e.pincode,
		              "email_nota": e.email_id, "uf": (e.state or "").upper() if len(e.state or "") == 2 else ""})  # fmt: skip
	return dados


def conferir_emitente(cfg, nfe=False, nfse=False):
	r = []
	faltando = [rotulo for campo, rotulo in (("razao_social", "razão social"), ("cnpj", "CNPJ"), *CAMPOS_ENDERECO) if not cfg.get(campo)]
	if faltando:
		r.append(item("erro", "Os dados da nossa empresa estão incompletos: falta " + ", ".join(faltando) + ".",
		              "Quem cuida da configuração fiscal precisa completar.", "config"))  # fmt: skip
	elif not util.cnpj_valido(cfg.cnpj):
		r.append(item("erro", "O CNPJ da nossa empresa na configuração não é válido.", None, "config"))
	if nfse and not (cfg.codigo_servico_nacional and flt(cfg.aliquota_iss) > 0):
		r.append(item("erro", "Falta o código do serviço ou a alíquota de ISS na configuração.", "O contador informa esses dois dados.", "config"))
	if nfe and not cfg.inscricao_estadual:
		r.append(item("erro", "Falta a inscrição estadual da nossa empresa (exigida na NF-e).", None, "config"))
	return r


def conferir_parte(df, rotulo, nfe=False):
	"""Confere o cadastro fiscal do cliente/fornecedor. `df` é o Dados Fiscais Parte (ou None)."""
	if not df:
		return [item("erro", f"O {rotulo} ainda não tem cadastro fiscal.", "Clique em Completar cadastro: os dados que o ERP já tem vêm preenchidos.", "cadastro")]
	r = []
	if not df.cnpj_cpf:
		r.append(item("erro", f"Falta o CNPJ/CPF do {rotulo}.", None, "cadastro"))
	elif not util.documento_valido(df.cnpj_cpf):
		r.append(item("erro", f"O CNPJ/CPF do {rotulo} ({df.cnpj_cpf}) não é válido.", "Confira os números com o cartão CNPJ ou com o cliente.", "cadastro"))
	else:
		r.append(item("ok", f"{'CNPJ' if len(util.limpar_documento(df.cnpj_cpf)) == 14 else 'CPF'} {util.formatar_documento(df.cnpj_cpf)} válido."))
	faltando = [rotulo_c for campo, rotulo_c in CAMPOS_ENDERECO if not df.get(campo)]
	if faltando:
		r.append(item("erro", "Endereço incompleto: falta " + ", ".join(faltando) + ".", None, "cadastro"))
	else:
		problemas = []
		if len(util.so_digitos(df.cep)) != 8:
			problemas.append("o CEP precisa ter 8 dígitos")
		if len(util.so_digitos(df.codigo_municipio)) != 7:
			problemas.append("o código IBGE do município precisa ter 7 dígitos")
		if (df.uf or "").upper() not in util.UF_CODIGO:
			problemas.append("a UF não existe")
		if problemas:
			r.append(item("erro", "Endereço com problema: " + "; ".join(problemas) + ".", None, "cadastro"))
		else:
			r.append(item("ok", f"Endereço completo ({df.municipio}/{df.uf.upper()})."))
	if nfe and df.contribuinte_icms == "Contribuinte" and not df.inscricao_estadual:
		r.append(item("erro", f"O {rotulo} é contribuinte de ICMS, mas está sem inscrição estadual.", "Sem IE a SEFAZ rejeita a NF-e. Se ele não tem IE, marque como Não contribuinte.", "cadastro"))
	if not df.email_nota:
		r.append(item("aviso", f"O {rotulo} não tem e-mail para notas: a nota e o boleto não serão enviados automaticamente.", None, "cadastro"))
	return r


# ===================================================================== cálculos
def calcular_servico(valor, cfg, df):
	aliq = flt(cfg.aliquota_iss)
	iss = flt(valor * aliq / 100, 2)
	iss_retido = bool(df and df.iss_retido)
	ret = {"pis": 0, "cofins": 0, "csll": 0, "ir": 0}
	if df and df.retem_impostos_federais and cfg.regime_tributario != "Simples Nacional":
		ret = {c: flt(valor * flt(cfg.get("aliquota_" + c)) / 100, 2) for c in ret}
		if ret["pis"] + ret["cofins"] + ret["csll"] < 10:  # dispensa de valores pequenos — validar com o contador
			ret.update(pis=0, cofins=0, csll=0)
		if ret["ir"] < 10:
			ret["ir"] = 0
	retencoes = flt((iss if iss_retido else 0) + sum(ret.values()), 2)
	v = {
		"valor_total": flt(valor, 2), "aliquota_iss": aliq, "valor_iss": iss, "iss_retido": int(iss_retido),
		"valor_pis_retido": ret["pis"], "valor_cofins_retido": ret["cofins"], "valor_csll_retido": ret["csll"], "valor_ir_retido": ret["ir"],
		"valor_retencoes": retencoes, "valor_liquido": flt(valor - retencoes, 2),
	}  # fmt: skip
	v.update(_reforma(valor, cfg))
	return v


def calcular_mercadoria(itens, cfg, df, natureza):
	total = flt(sum(flt(i["valor_total"]) for i in itens), 2)
	dentro = _mesmo_estado(cfg, df)
	cfop = natureza.cfop_dentro_estado if dentro else natureza.cfop_fora_estado
	v = {"valor_total": total, "cfop": cfop, "base_icms": 0, "aliquota_icms": 0, "valor_icms": 0, "valor_retencoes": 0, "valor_liquido": total}
	if natureza.icms_tributado and cfg.regime_tributario != "Simples Nacional":
		aliq = flt(cfg.aliquota_icms_interna if dentro else cfg.aliquota_icms_interestadual)
		v.update(base_icms=total, aliquota_icms=aliq, valor_icms=flt(total * aliq / 100, 2))
	if natureza.tipo == "Venda":
		v.update(_reforma(total, cfg))
	return v


def _reforma(valor, cfg):
	if not cfg.destacar_ibs_cbs:
		return {"valor_cbs": 0, "valor_ibs": 0}
	return {"valor_cbs": flt(valor * flt(cfg.aliquota_cbs) / 100, 2), "valor_ibs": flt(valor * flt(cfg.aliquota_ibs) / 100, 2)}


def _mesmo_estado(cfg, df):
	return not df or not df.uf or (df.uf or "").upper() == (cfg.uf or "").upper()


def natureza_por_tipo(tipo):
	nome = frappe.db.get_value("Natureza Operacao Fiscal", {"tipo": tipo, "ativo": 1}, "name", order_by="creation asc")
	return frappe.get_cached_doc("Natureza Operacao Fiscal", nome) if nome else None


# ===================================================================== fatura -> documentos
def eh_produto(item_code):
	"""Item com NCM (Tarifa Aduaneira) ou controlado em estoque = mercadoria (NF-e); o resto é serviço (NFS-e)."""
	i = frappe.get_cached_value("Item", item_code, ["customs_tariff_number", "is_stock_item"], as_dict=True) or {}
	return bool(i.get("customs_tariff_number") or i.get("is_stock_item"))


def planejar_fatura(fatura):
	"""Tudo o que a fatura vai gerar e a conferência — é o que a tela "Para emitir" mostra."""
	cfg = config()
	si = frappe.get_doc("Sales Invoice", fatura) if isinstance(fatura, str) else fatura
	df = dados_parte("Customer", si.customer)
	servicos, produtos = [], []
	for linha in si.items:
		destino = produtos if eh_produto(linha.item_code) else servicos
		destino.append({
			"item_code": linha.item_code, "descricao": linha.description and frappe.utils.strip_html_tags(linha.description) or linha.item_name,
			"ncm": util.so_digitos(frappe.get_cached_value("Item", linha.item_code, "customs_tariff_number")),
			"unidade": (linha.uom or "UN")[:6], "quantidade": flt(linha.qty), "valor_unitario": flt(linha.net_rate or linha.rate, 2),
			"valor_total": flt(linha.net_amount or linha.amount, 2), "referencia": linha.name,
		})  # fmt: skip
	ja = {n.tipo_documento: n for n in _notas_da_fatura(si.name) if n.status == "Autorizada"}
	documentos, checagens = [], []
	checagens += conferir_emitente(cfg, nfe=bool(produtos) and "NF-e" not in ja, nfse=bool(servicos) and "NFS-e" not in ja)
	checagens += conferir_parte(df, "cliente", nfe=bool(produtos))

	if servicos:
		nat = natureza_por_tipo("Serviço")
		valores = calcular_servico(sum(i["valor_total"] for i in servicos), cfg, df)
		discr = (cfg.descricao_padrao_servico or "").replace("{fatura}", si.name)
		discr = discr + "\n" + "\n".join(f"- {i['descricao']} ({_qtd(i['quantidade'])} x {util.moeda(i['valor_unitario'])})" for i in servicos)
		documentos.append({"tipo": "NFS-e", "natureza": nat and nat.name, "itens": servicos, "valores": valores, "discriminacao": discr.strip(),
		                   "ja_emitida": _resumo_nota(ja.get("NFS-e")), "resumo": _texto_servico(valores, cfg, df)})  # fmt: skip
		if not nat:
			checagens.append(item("erro", "Não há natureza de operação de serviço ativa.", None, "config"))
	if produtos:
		nat = natureza_por_tipo("Venda")
		if nat:
			for i in produtos:
				i["cfop"] = nat.cfop_dentro_estado if _mesmo_estado(cfg, df) else nat.cfop_fora_estado
			valores = calcular_mercadoria(produtos, cfg, df, nat)
			documentos.append({"tipo": "NF-e", "natureza": nat.name, "itens": produtos, "valores": valores,
			                   "ja_emitida": _resumo_nota(ja.get("NF-e")), "resumo": _texto_mercadoria(valores, cfg, df, nat)})  # fmt: skip
		else:
			checagens.append(item("erro", "Não há natureza de operação de venda ativa.", None, "config"))
		for i in produtos:
			if len(i["ncm"]) != 8:
				checagens.append(item("erro", f"O produto {i['item_code']} está sem NCM válido (8 dígitos).",
				                      "Abra o item no ERP e preencha o campo Tarifa Aduaneira (NCM).", "item:" + i["item_code"]))  # fmt: skip
	if servicos and produtos:
		checagens.append(item("info", "A fatura tem serviço e produto: vão sair duas notas (uma NFS-e e uma NF-e) e um boleto só."))
	if flt(si.grand_total) <= 0:
		checagens.append(item("erro", "A fatura está com valor zero."))

	boleto = _planejar_boleto(si, documentos, cfg)
	if not boleto and flt(si.outstanding_amount) <= 0:
		checagens.append(item("info", "A fatura já está paga no ERP: não vamos gerar boleto."))

	if simulacao(cfg):
		checagens.append(item("info", "Modo simulação: a nota e o boleto são de teste, sem valor fiscal."))
	pendentes = [d for d in documentos if not d["ja_emitida"]]
	return {
		"fatura": si.name, "cliente": si.customer, "nome": si.customer_name, "data": str(si.posting_date),
		"valor": flt(si.grand_total), "em_aberto": flt(si.outstanding_amount),
		"documento_cliente": util.formatar_documento(df.cnpj_cpf) if df else "",
		"documentos": documentos, "boleto": boleto, "checagens": _ordenar(checagens),
		"pendente": bool(pendentes) or bool(boleto and not boleto.get("ja_emitido")),
		"pode_emitir": not any(c["nivel"] == "erro" for c in checagens) and (bool(pendentes) or bool(boleto and not boleto.get("ja_emitido"))),
	}  # fmt: skip


def _planejar_boleto(si, documentos, cfg):
	ativo = frappe.db.get_value("Boleto Cobranca", {"fatura": si.name, "status": ["in", ["Em aberto", "Vencido", "Pago"]]},
	                            ["name", "valor", "vencimento", "status"], as_dict=True)  # fmt: skip
	if ativo:
		return {"ja_emitido": ativo, "valor": flt(ativo.valor), "vencimento": str(ativo.vencimento), "resumo": f"Boleto {ativo.name} já emitido."}
	if flt(si.outstanding_amount) <= 0 or not documentos:
		return None
	geram = [d for d in documentos if d["natureza"] and frappe.get_cached_value("Natureza Operacao Fiscal", d["natureza"], "gera_boleto")]
	if not geram:
		return None
	retencoes = flt(sum(d["valores"].get("valor_retencoes") or 0 for d in documentos), 2)
	valor = flt(flt(si.outstanding_amount) - retencoes, 2)
	if valor <= 0:
		return None
	venc = getdate(si.due_date) if si.due_date and getdate(si.due_date) > getdate(today()) else getdate(add_days(today(), cfg.dias_vencimento or 10))
	texto = f"Boleto de {util.moeda(valor)} com vencimento em {venc.strftime('%d/%m/%Y')}"
	if retencoes:
		texto += f" (fatura de {util.moeda(si.outstanding_amount)} menos {util.moeda(retencoes)} que o cliente retém e recolhe)"
	texto += ", com Pix no mesmo boleto." if cfg.chave_pix or simulacao(cfg) else "."
	return {"valor": valor, "vencimento": str(venc), "retencoes": retencoes, "resumo": texto, "ja_emitido": None}


def _texto_servico(v, cfg, df):
	t = f"NFS-e de {util.moeda(v['valor_total'])}. ISS de {_pct(v['aliquota_iss'])} = {util.moeda(v['valor_iss'])}"
	t += ", retido e recolhido pelo cliente." if v["iss_retido"] else ", recolhido por nós."
	fed = v["valor_pis_retido"] + v["valor_cofins_retido"] + v["valor_csll_retido"] + v["valor_ir_retido"]
	if fed:
		t += f" O cliente também retém {util.moeda(fed)} de PIS/COFINS/CSLL/IR."
	if v.get("valor_cbs") or v.get("valor_ibs"):
		t += f" CBS {util.moeda(v['valor_cbs'])} e IBS {util.moeda(v['valor_ibs'])} só informativos (2026)."
	return t


def _texto_mercadoria(v, cfg, df, nat):
	dentro = "dentro do estado" if _mesmo_estado(cfg, df) else f"para outro estado ({(df.uf or '').upper()})"
	t = f"NF-e de {util.moeda(v['valor_total'])} — {nat.name.lower()} {dentro}, CFOP {v['cfop']}."
	if v["valor_icms"]:
		t += f" ICMS {_pct(v['aliquota_icms'])} = {util.moeda(v['valor_icms'])}."
	elif cfg.regime_tributario == "Simples Nacional":
		t += " Simples Nacional: ICMS sem destaque na nota."
	return t


def _ordenar(checagens):
	ordem = {"erro": 0, "aviso": 1, "info": 2, "ok": 3}
	return sorted(checagens, key=lambda c: ordem[c["nivel"]])


def _pct(v):
	return f"{flt(v):g}%".replace(".", ",")


def _qtd(v):
	return f"{flt(v):g}".replace(".", ",")


def _notas_da_fatura(fatura):
	return frappe.get_all("Nota Fiscal", filters={"fatura": fatura}, fields=["name", "tipo_documento", "status", "numero"], order_by="creation asc")


def _resumo_nota(n):
	return {"id": n.name, "numero": n.numero} if n else None


# ===================================================================== remessa e retorno (sem fatura)
def planejar_avulsa(dados):
	"""dados: natureza, tipo_parte, parte, itens[{descricao, ncm, quantidade, valor_unitario, numero_serie, referencia}],
	nf_referenciada, prazo_retorno, observacao."""
	dados = frappe._dict(json.loads(dados) if isinstance(dados, str) else dados)
	cfg = config()
	checagens = []
	if not dados.natureza or not frappe.db.exists("Natureza Operacao Fiscal", dados.natureza):
		return {"checagens": [item("erro", "Escolha o tipo da operação.")], "pode_emitir": False}
	nat = frappe.get_cached_doc("Natureza Operacao Fiscal", dados.natureza)
	rotulo = "cliente" if dados.tipo_parte == "Customer" else "fornecedor"
	df = dados_parte(dados.tipo_parte, dados.parte) if dados.parte else None
	if not dados.parte:
		checagens.append(item("erro", f"Escolha o {rotulo}."))
	checagens += conferir_emitente(cfg, nfe=True)
	if dados.parte:
		checagens += conferir_parte(df, rotulo, nfe=True)

	itens = []
	dentro = _mesmo_estado(cfg, df)
	for i in dados.itens or []:
		i = frappe._dict(i)
		qtd, unit = flt(i.quantidade) or 1, flt(i.valor_unitario, 2)
		itens.append({"descricao": (i.descricao or "").strip(), "ncm": util.so_digitos(i.ncm), "quantidade": qtd, "valor_unitario": unit,
		              "valor_total": flt(qtd * unit, 2), "numero_serie": i.numero_serie, "referencia": i.referencia, "unidade": "UN",
		              "cfop": nat.cfop_dentro_estado if dentro else nat.cfop_fora_estado})  # fmt: skip
	if not itens:
		checagens.append(item("erro", "Adicione pelo menos um equipamento ou item."))
	for n, i in enumerate(itens, 1):
		if not i["descricao"]:
			checagens.append(item("erro", f"O item {n} está sem descrição."))
		if len(i["ncm"]) != 8:
			checagens.append(item("erro", f"O item {n} ({i['descricao'] or 'sem descrição'}) está sem NCM de 8 dígitos.", "Na remessa e no retorno use o mesmo NCM da nota de origem."))
		if i["valor_unitario"] <= 0:
			checagens.append(item("erro", f"O item {n} está sem valor.", "Use o valor declarado na nota de origem (remessa e retorno não são cobrança)."))

	origem = None
	if nat.exige_nf_referenciada:
		origem = util.decodificar_chave_nfe(dados.nf_referenciada) if dados.nf_referenciada else None
		if not origem:
			checagens.append(item("erro", "Informe a chave de acesso da nota com que o equipamento chegou (44 dígitos, fica no DANFE)."))
		elif not origem["valida"]:
			checagens.append(item("erro", "Chave da nota de origem: " + origem["motivo"]))
		else:
			checagens.append(item("ok", f"Chave da nota de origem confere: NF-e {origem['numero']} série {origem['serie']}, emitida em {origem['ano_mes']} ({origem['uf']})."))
			if df and df.cnpj_cpf and util.limpar_documento(df.cnpj_cpf) != origem["cnpj_emitente"]:
				checagens.append(item("aviso", f"A nota de origem foi emitida pelo CNPJ {util.formatar_documento(origem['cnpj_emitente'])}, que não é o do {rotulo} escolhido.",
				                      "Confira se escolheu o cliente certo ou se a nota é de outra unidade dele."))  # fmt: skip
	prazo = None
	if nat.controla_retorno:
		prazo = getdate(dados.prazo_retorno) if dados.prazo_retorno else getdate(add_days(today(), cfg.prazo_retorno_remessa_dias or 180))
		checagens.append(item("info", f"Vamos acompanhar o retorno: previsto até {prazo.strftime('%d/%m/%Y')}."))
	valores = calcular_mercadoria(itens, cfg, df, nat) if itens else {"valor_total": 0}
	texto = (nat.texto_complementar or "").replace("{nf_referenciada}", util.formatar_chave(dados.nf_referenciada or "")).replace(
		"{prazo}", prazo.strftime("%d/%m/%Y") if prazo else ""
	)
	if dados.observacao:
		texto = (texto + " " + dados.observacao).strip()
	if simulacao(cfg):
		checagens.append(item("info", "Modo simulação: a nota é de teste, sem valor fiscal."))
	resumo = f"NF-e de {nat.name.lower()} para {df.razao_social if df else 'o ' + rotulo}, {len(itens)} item(ns), valor declarado {util.moeda(valores['valor_total'])}"
	resumo += f", CFOP {valores.get('cfop')}. Não gera boleto nem cobrança." if itens else "."
	return {
		"natureza": nat.name, "explicacao": nat.explicacao, "tipo": nat.tipo, "itens": itens, "valores": valores, "texto_complementar": texto,
		"nf_referenciada": origem and origem.get("valida") and origem["chave"], "prazo_retorno": str(prazo) if prazo else None,
		"resumo": resumo, "checagens": _ordenar(checagens), "pode_emitir": not any(c["nivel"] == "erro" for c in checagens),
	}  # fmt: skip
