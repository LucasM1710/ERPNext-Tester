"""API do módulo Fiscal (página /fiscal).

Acesso: papéis Accounts User, Accounts Manager ou System Manager. A configuração (aba Configuração do ERP)
é editada no Desk por Accounts Manager/System Manager.
"""

import json

import frappe
from frappe import _
from frappe.utils import flt, get_first_day, get_url, getdate, today

from solucoes.fiscal import documentos, emissao, regras, util
from solucoes.fiscal.regras import config

PAPEIS = ("Accounts User", "Accounts Manager", "System Manager")
PAPEIS_CONFIG = ("Accounts Manager", "System Manager")
ABERTOS = ["Em aberto", "Vencido"]


def _exigir_acesso():
	if frappe.session.user == "Guest":
		raise frappe.PermissionError(_("Faça login para acessar a emissão de notas."))
	if not set(frappe.get_roles()) & set(PAPEIS):
		raise frappe.PermissionError(_("Área do financeiro: peça acesso ao administrador do ERP."))


def _json(valor, padrao=None):
	if isinstance(valor, str):
		return json.loads(valor) if valor else padrao
	return valor if valor is not None else padrao


# ===================================================================== sessão e painel
@frappe.whitelist()
def contexto():
	_exigir_acesso()
	cfg = config()
	usuario = frappe.db.get_value("User", frappe.session.user, ["full_name", "user_image", "email"], as_dict=True)
	return {
		"usuario": {"nome": usuario.full_name or frappe.session.user, "imagem": usuario.user_image, "email": usuario.email},
		"empresa": cfg.nome_fantasia or cfg.razao_social or cfg.empresa or "",
		"ambiente": cfg.ambiente,
		"simulacao": cfg.ambiente == "Simulação",
		"pode_configurar": bool(set(frappe.get_roles()) & set(PAPEIS_CONFIG)),
		"contadores": _contadores(),
	}


def _contadores():
	return {
		"rejeitadas": frappe.db.count("Nota Fiscal", {"status": "Rejeitada"}),
		"boletos_vencidos": frappe.db.count("Boleto Cobranca", {"status": "Vencido"}),
		"remessas_atrasadas": frappe.db.count("Nota Fiscal", {"situacao_remessa": "Em aberto", "prazo_retorno": ["<", today()]}),
	}


@frappe.whitelist()
def para_emitir():
	"""Faturas confirmadas que ainda precisam de nota e/ou boleto, já conferidas, e os números do dia."""
	_exigir_acesso()
	cfg = config()
	filtros = {"docstatus": 1, "is_return": 0}
	if cfg.empresa:
		filtros["company"] = cfg.empresa
	if cfg.data_inicio:
		filtros["posting_date"] = [">=", cfg.data_inicio]
	com_boleto = set(frappe.get_all("Boleto Cobranca", filters={"status": ["!=", "Cancelado"]}, pluck="fatura"))
	faturas = [f for f in frappe.get_all("Sales Invoice", filters=filtros, pluck="name", order_by="posting_date desc, name desc", limit=300) if f not in com_boleto]
	planos = [p for p in (regras.planejar_fatura(f) for f in faturas) if p["pendente"]]
	rejeitadas = [_linha_nota(n) for n in frappe.get_all("Nota Fiscal", filters={"status": "Rejeitada"}, fields=CAMPOS_NOTA, order_by="modified desc")]
	return {"faturas": planos, "rejeitadas": rejeitadas, "kpis": _kpis(planos)}


def _kpis(planos):
	inicio = get_first_day(today())
	notas_mes = frappe.get_all("Nota Fiscal", filters={"status": "Autorizada", "data_emissao": [">=", inicio]}, fields=["valor_total"])
	abertos = frappe.get_all("Boleto Cobranca", filters={"status": ["in", ABERTOS]}, fields=["valor", "status"])
	pagos = frappe.get_all("Boleto Cobranca", filters={"status": "Pago", "pago_em": [">=", inicio]}, fields=["valor_pago"])
	return {
		"a_emitir": len(planos), "a_emitir_valor": sum(p["valor"] for p in planos),
		"prontas": sum(1 for p in planos if p["pode_emitir"]),
		"emitidas_mes": len(notas_mes), "emitidas_mes_valor": sum(flt(n.valor_total) for n in notas_mes),
		"boletos_abertos": len(abertos), "boletos_abertos_valor": sum(flt(b.valor) for b in abertos),
		"vencidos": sum(1 for b in abertos if b.status == "Vencido"), "vencidos_valor": sum(flt(b.valor) for b in abertos if b.status == "Vencido"),
		"recebido_mes": sum(flt(b.valor_pago) for b in pagos),
		"remessas_abertas": frappe.db.count("Nota Fiscal", {"situacao_remessa": "Em aberto"}),
	}  # fmt: skip


@frappe.whitelist()
def conferir(fatura):
	_exigir_acesso()
	return regras.planejar_fatura(fatura)


@frappe.whitelist()
def emitir(fatura):
	_exigir_acesso()
	return emissao.emitir_fatura(fatura)


@frappe.whitelist()
def emitir_lote(faturas):
	"""Emite várias faturas prontas; uma com problema não impede as outras."""
	_exigir_acesso()
	resultado = []
	for f in _json(faturas, []):
		try:
			r = emissao.emitir_fatura(f)
			frappe.db.commit()
			resultado.append({"fatura": f, "ok": all(n["status"] == "Autorizada" for n in r["notas"]), **r})
		except Exception as e:
			frappe.db.rollback()
			frappe.clear_messages()
			resultado.append({"fatura": f, "ok": False, "erro": str(e), "notas": [], "boleto": None})
	return resultado


# ===================================================================== cadastro fiscal (cliente / fornecedor)
@frappe.whitelist()
def dados_fiscais(tipo_parte, parte):
	_exigir_acesso()
	df = regras.dados_parte(tipo_parte, parte)
	if df:
		return {"existe": True, **{c.fieldname: df.get(c.fieldname) for c in df.meta.fields if c.fieldtype not in ("Section Break", "Column Break")}}
	return {"existe": False, **regras.sugestao_dados_parte(tipo_parte, parte)}


@frappe.whitelist()
def salvar_dados_fiscais(dados):
	_exigir_acesso()
	dados = frappe._dict(_json(dados, {}))
	if dados.tipo_parte not in ("Customer", "Supplier") or not frappe.db.exists(dados.tipo_parte, dados.parte):
		frappe.throw("Cliente ou fornecedor não encontrado.")
	if dados.cnpj_cpf and not util.documento_valido(dados.cnpj_cpf):
		frappe.throw(f"O CNPJ/CPF {dados.cnpj_cpf} não é válido. Confira os números.")
	nome = frappe.db.get_value("Dados Fiscais Parte", {"tipo_parte": dados.tipo_parte, "parte": dados.parte}, "name")
	doc = frappe.get_doc("Dados Fiscais Parte", nome) if nome else frappe.new_doc("Dados Fiscais Parte")
	campos = [c.fieldname for c in doc.meta.fields if c.fieldtype not in ("Section Break", "Column Break")]
	doc.update({c: dados.get(c) for c in campos if c in dados})
	doc.cnpj_cpf = util.formatar_documento(doc.cnpj_cpf)
	doc.cep = util.formatar_cep(doc.cep)
	doc.uf = (doc.uf or "").upper()
	doc.codigo_municipio = util.so_digitos(doc.codigo_municipio)
	doc.save(ignore_permissions=True)
	# o CNPJ também vai para o cadastro do ERP, se lá estiver vazio
	if doc.cnpj_cpf and not frappe.db.get_value(doc.tipo_parte, doc.parte, "tax_id"):
		frappe.db.set_value(doc.tipo_parte, doc.parte, "tax_id", doc.cnpj_cpf)
	return {"ok": True}


@frappe.whitelist()
def buscar_partes(tipo_parte, texto=""):
	_exigir_acesso()
	campo = "customer_name" if tipo_parte == "Customer" else "supplier_name"
	filtros = {"disabled": 0}
	ou = [[campo, "like", f"%{texto}%"], ["name", "like", f"%{texto}%"], ["tax_id", "like", f"%{texto}%"]] if texto else None
	linhas = frappe.get_all(tipo_parte, filters=filtros, or_filters=ou, fields=["name", f"{campo} as nome", "tax_id"], limit=12, order_by=f"{campo} asc")
	return linhas


@frappe.whitelist()
def equipamentos(tipo_parte, parte=None):
	"""Sugestões de itens para remessa/retorno: equipamentos do cliente (retorno) ou nossos padrões (remessa)."""
	_exigir_acesso()
	if tipo_parte == "Customer" and parte and frappe.db.table_exists("Equipamento Cliente"):
		linhas = frappe.get_all("Equipamento Cliente", filters={"cliente": parte}, fields=["name", "tag", "descricao", "fabricante", "modelo", "numero_serie", "status"],
		                        order_by="descricao asc", limit=200)  # fmt: skip
		linhas.sort(key=lambda e: e.status != "Em Calibração")  # os que estão no laboratório primeiro
	elif frappe.db.table_exists("Padrao Metrologia"):
		linhas = frappe.get_all("Padrao Metrologia", fields=["name", "codigo as tag", "descricao", "fabricante", "modelo", "numero_serie", "status"], order_by="descricao asc", limit=200)
	else:
		linhas = []
	for e in linhas:
		e["texto"] = " ".join(p for p in (e.descricao, e.fabricante, e.modelo) if p) + (f" — {e.tag}" if e.tag else "")
	return linhas


# ===================================================================== notas
CAMPOS_NOTA = ["name", "tipo_documento", "status", "numero", "serie", "nome_parte", "documento_parte", "valor_total", "valor_liquido", "data_emissao",
               "fatura", "natureza", "boleto", "chave_acesso", "situacao_remessa", "prazo_retorno", "retorno_data", "mensagem_retorno", "orientacao",
               "codigo_retorno", "creation", "parte", "tipo_parte", "uf_destino"]  # fmt: skip


def _linha_nota(n):
	n = dict(n)
	n["id"] = n.pop("name")
	n["chave_formatada"] = util.formatar_chave(n.get("chave_acesso"))
	if n.get("situacao_remessa") == "Em aberto":
		n["dias_fora"] = (getdate(today()) - getdate(n.get("data_emissao") or n.get("creation"))).days
		n["atrasada"] = bool(n.get("prazo_retorno") and getdate(n["prazo_retorno"]) < getdate(today()))
	return n


@frappe.whitelist()
def notas(tipo=None, status=None, busca=None, periodo=None):
	_exigir_acesso()
	filtros = {"status": ["!=", "Substituída"]}
	if tipo:
		filtros["tipo_documento"] = tipo
	if status:
		filtros["status"] = status
	if periodo:  # AAAA-MM
		inicio = getdate(periodo + "-01")
		filtros["creation"] = ["between", [inicio, frappe.utils.get_last_day(inicio)]]
	ou = [["nome_parte", "like", f"%{busca}%"], ["numero", "like", f"%{busca}%"], ["fatura", "like", f"%{busca}%"], ["documento_parte", "like", f"%{busca}%"]] if busca else None
	linhas = frappe.get_all("Nota Fiscal", filters=filtros, or_filters=ou, fields=CAMPOS_NOTA, order_by="creation desc", limit=500)
	return [_linha_nota(n) for n in linhas]


@frappe.whitelist()
def nota(id):
	_exigir_acesso()
	doc = frappe.get_doc("Nota Fiscal", id)
	r = _linha_nota({c: doc.get(c) for c in CAMPOS_NOTA})
	r.update({
		"itens": [{c: i.get(c) for c in ("item_code", "descricao", "ncm", "cfop", "unidade", "quantidade", "valor_unitario", "valor_total", "numero_serie")} for i in doc.itens],
		"eventos": [{"data": str(e.data), "evento": e.evento, "detalhe": e.detalhe} for e in reversed(doc.eventos)],
		"valores": {c: flt(doc.get(c)) for c in ("valor_total", "base_icms", "aliquota_icms", "valor_icms", "aliquota_iss", "valor_iss", "valor_pis_retido",
		                                         "valor_cofins_retido", "valor_csll_retido", "valor_ir_retido", "valor_retencoes", "valor_liquido", "valor_cbs", "valor_ibs")},
		"iss_retido": doc.iss_retido, "cfop": doc.cfop, "discriminacao": doc.discriminacao, "informacoes_complementares": doc.informacoes_complementares,
		"nf_referenciada": util.formatar_chave(doc.nf_referenciada), "retorno_chave": util.formatar_chave(doc.retorno_chave),
		"destinatario": json.loads(doc.destinatario_json or "{}"), "protocolo": doc.protocolo, "email_enviado_em": str(doc.email_enviado_em or ""),
		"motivo_cancelamento": doc.motivo_cancelamento, "ambiente": doc.ambiente, "xml": bool(doc.xml),
		"pode_cancelar": doc.status == "Autorizada", "boleto_detalhe": _linha_boleto(frappe.get_doc("Boleto Cobranca", doc.boleto)) if doc.boleto else None,
	})  # fmt: skip
	return r


@frappe.whitelist()
def tentar_de_novo(id):
	_exigir_acesso()
	return emissao.tentar_de_novo(id)


@frappe.whitelist()
def cancelar_nota(id, motivo):
	_exigir_acesso()
	return emissao.cancelar_nota(id, motivo)


@frappe.whitelist()
def reenviar_email(id):
	_exigir_acesso()
	doc = frappe.get_doc("Nota Fiscal", id)
	if doc.status != "Autorizada":
		frappe.throw("Só notas autorizadas podem ser enviadas.")
	df = regras.dados_parte(doc.tipo_parte, doc.parte)
	if df and df.email_nota:  # e-mail corrigido no cadastro depois da emissão
		dados = json.loads(doc.destinatario_json or "{}")
		dados["email_nota"] = df.email_nota
		doc.destinatario_json = json.dumps(dados, ensure_ascii=False)
	emissao.enviar_nota(doc)
	return {"ok": True, "simulacao": config().ambiente == "Simulação"}


# ===================================================================== boletos
CAMPOS_BOLETO = ["name", "status", "cliente", "nome_cliente", "documento_cliente", "email_cliente", "fatura", "nota_fiscal", "valor", "emissao",
                 "vencimento", "nosso_numero", "linha_digitavel", "pix_copia_cola", "pago_em", "valor_pago", "pagamento", "ultimo_lembrete"]  # fmt: skip


def _linha_boleto(b):
	r = {c: b.get(c) for c in CAMPOS_BOLETO}
	r["id"] = r.pop("name")
	dias = (getdate(b.vencimento) - getdate(today())).days
	r["dias_para_vencer"] = dias
	if b.status in ABERTOS and dias < 0:
		cfg = config()
		atraso = -dias
		r["valor_atualizado"] = flt(flt(b.valor) * (1 + flt(b.multa_percentual) / 100 + flt(b.juros_mes_percentual) / 100 / 30 * atraso), 2)
		r["atraso_dias"] = atraso
		r["aviso_multa"] = f"Com multa de {flt(b.multa_percentual):g}% e juros de {flt(b.juros_mes_percentual):g}% ao mês" if cfg else ""
	if not isinstance(b, dict):  # documento completo (detalhe): inclui o histórico
		r["eventos"] = [{"data": str(e.data), "evento": e.evento, "detalhe": e.detalhe} for e in reversed(b.eventos)]
	return r


@frappe.whitelist()
def boletos(status=None, busca=None):
	_exigir_acesso()
	filtros = {}
	if status == "abertos":
		filtros["status"] = ["in", ABERTOS]
	elif status:
		filtros["status"] = status
	ou = [["nome_cliente", "like", f"%{busca}%"], ["fatura", "like", f"%{busca}%"], ["nosso_numero", "like", f"%{busca}%"]] if busca else None
	linhas = frappe.get_all("Boleto Cobranca", filters=filtros, or_filters=ou, fields=CAMPOS_BOLETO + ["multa_percentual", "juros_mes_percentual"],
	                        order_by="vencimento asc", limit=500)  # fmt: skip
	ordem = {"Vencido": 0, "Em aberto": 1, "Pago": 2, "Cancelado": 3}
	linhas.sort(key=lambda b: ordem.get(b.status, 9))  # vencidos primeiro, depois os a vencer (a ordenação é estável)
	return [_linha_boleto(frappe._dict(b)) for b in linhas]


@frappe.whitelist()
def boleto(id):
	_exigir_acesso()
	return _linha_boleto(frappe.get_doc("Boleto Cobranca", id))


@frappe.whitelist()
def simular_pagamento(id, valor=None, data=None):
	_exigir_acesso()
	if config().ambiente != "Simulação":
		frappe.throw("Simular pagamento só existe no modo simulação. Em produção, o banco avisa sozinho.")
	return emissao.registrar_pagamento(id, valor, data, origem="pagamento simulado")


@frappe.whitelist()
def marcar_como_pago(id, valor=None, data=None):
	"""Baixa manual (cliente pagou por transferência ou em dinheiro, fora do boleto)."""
	_exigir_acesso()
	return emissao.registrar_pagamento(id, valor, data, origem=f"baixa manual por {frappe.session.user}")


@frappe.whitelist()
def cancelar_boleto(id, motivo):
	_exigir_acesso()
	if len((motivo or "").strip()) < 5:
		frappe.throw("Escreva o motivo do cancelamento.")
	return emissao.cancelar_boleto(id, motivo.strip())


@frappe.whitelist()
def prorrogar_boleto(id, vencimento):
	"""Novo boleto com outro vencimento (o antigo é cancelado) — segunda via com nova data."""
	_exigir_acesso()
	antigo = frappe.get_doc("Boleto Cobranca", id)
	if antigo.status not in ABERTOS:
		frappe.throw("Só boletos em aberto ou vencidos podem ser prorrogados.")
	if getdate(vencimento) < getdate(today()):
		frappe.throw("O novo vencimento precisa ser hoje ou depois.")
	emissao.cancelar_boleto(antigo.name, f"Prorrogado para {getdate(vencimento).strftime('%d/%m/%Y')}")
	si = frappe.get_doc("Sales Invoice", antigo.fatura)
	novo = emissao.criar_boleto(si, {"valor": flt(antigo.valor), "vencimento": str(getdate(vencimento))}, nota=antigo.nota_fiscal)
	emissao.evento(novo, "Segunda via", f"Substitui o boleto {antigo.name}")
	novo.save(ignore_permissions=True)
	return _linha_boleto(novo)


# ===================================================================== remessa e retorno
@frappe.whitelist()
def remessas():
	_exigir_acesso()
	abertas = frappe.get_all("Nota Fiscal", filters={"situacao_remessa": "Em aberto", "status": "Autorizada"}, fields=CAMPOS_NOTA, order_by="prazo_retorno asc")
	nat_avulsas = frappe.get_all("Natureza Operacao Fiscal", filters={"tipo": ["in", ["Remessa", "Retorno"]], "ativo": 1}, pluck="name")
	recentes = frappe.get_all("Nota Fiscal", filters={"natureza": ["in", nat_avulsas or [""]], "status": ["!=", "Substituída"]}, fields=CAMPOS_NOTA,
	                          order_by="creation desc", limit=50)  # fmt: skip
	return {"abertas": [_linha_nota(n) for n in abertas], "recentes": [_linha_nota(n) for n in recentes]}


@frappe.whitelist()
def naturezas_avulsas():
	_exigir_acesso()
	return frappe.get_all("Natureza Operacao Fiscal", filters={"tipo": ["in", ["Remessa", "Retorno"]], "ativo": 1},
	                      fields=["name", "tipo", "explicacao", "exige_nf_referenciada", "controla_retorno", "cfop_dentro_estado", "cfop_fora_estado"],
	                      order_by="tipo desc, creation asc")  # fmt: skip


@frappe.whitelist()
def conferir_avulsa(dados):
	_exigir_acesso()
	return regras.planejar_avulsa(dados)


@frappe.whitelist()
def emitir_avulsa(dados):
	_exigir_acesso()
	return emissao.emitir_avulsa(dados)


@frappe.whitelist()
def registrar_retorno(id, chave=None, data=None):
	_exigir_acesso()
	return emissao.registrar_retorno(id, chave, data)


@frappe.whitelist()
def decodificar_chave(chave):
	_exigir_acesso()
	return util.decodificar_chave_nfe(chave)


# ===================================================================== prontidão para produção
@frappe.whitelist()
def prontidao():
	"""O que falta para sair da simulação — em linguagem simples, para o gestor."""
	_exigir_acesso()
	cfg = config()
	ok = lambda cond, texto, dica=None: {"ok": bool(cond), "texto": texto, "dica": dica}  # noqa: E731
	emitente = regras.conferir_emitente(cfg, nfe=True, nfse=True)
	return {
		"ambiente": cfg.ambiente,
		"passos": [
			ok(not [c for c in emitente if c["nivel"] == "erro"], "Dados da empresa completos (CNPJ, IE, IM, endereço, código do serviço e ISS)",
			   "Configuração fiscal no ERP. O contador confirma código do serviço, alíquota de ISS e regime."),
			ok(frappe.db.count("Natureza Operacao Fiscal", {"ativo": 1}) >= 3, "Naturezas de operação revisadas pelo contador",
			   "CFOP e CSOSN/CST de venda, remessa e retorno (já vêm sugeridos)."),
			ok(cfg.certificado_a1 and cfg.certificado_validade and getdate(cfg.certificado_validade) > getdate(today()),
			   "Certificado digital A1 da empresa (e-CNPJ) válido", "Comprado em uma certificadora (Serasa, Certisign, Valid...). Validade de 1 ano."),
			ok(cfg.provedor_notas != "Simulador" and cfg.get_password("provedor_token", raise_exception=False),
			   "Provedor de notas contratado e token informado", "Ex.: Focus NFe, PlugNotas, Nuvem Fiscal ou NFE.io. Eles transmitem à SEFAZ e à NFS-e Nacional."),
			ok(cfg.provedor_boleto != "Simulador" and cfg.get_password("boleto_credencial", raise_exception=False),
			   "Cobrança registrada no banco (ou gateway) e credencial da API", "Convênio de boleto com Pix no banco da empresa."),
			ok(cfg.chave_pix, "Chave Pix da empresa informada", "Para o QR Code no boleto."),
			ok(cfg.conta_recebimento, "Conta do banco no ERP para lançar os recebimentos", "Sem ela o recebimento cai na conta padrão da empresa."),
			ok(cfg.conta_retencoes, "Conta para impostos retidos pelos clientes", "Necessária se algum cliente retém ISS ou impostos federais."),
			ok(frappe.db.get_value("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}), "E-mail de saída configurado", "Para enviar nota e boleto ao cliente."),
			ok(cfg.ambiente != "Simulação", "Testes em homologação concluídos", "Emitir algumas notas e boletos de teste no provedor antes de virar para Produção."),
		],
		"url_config": get_url("/app/configuracao-fiscal"),
	}


# ===================================================================== documentos (PDF / XML)
@frappe.whitelist()
def documento(tipo, id, formato="pdf"):
	"""tipo: nota | boleto | xml. Abre o PDF no navegador (ou o HTML para imprimir, se não houver gerador de PDF)."""
	_exigir_acesso()
	if tipo == "xml":
		nota_doc = frappe.get_doc("Nota Fiscal", id)
		if nota_doc.status not in ("Autorizada", "Cancelada"):
			frappe.throw("A nota ainda não foi autorizada.")
		frappe.local.response.update({"type": "download", "filename": f"{nota_doc.tipo_documento.replace('-', '')}-{nota_doc.chave_acesso}.xml",
		                              "filecontent": documentos.xml_nota(nota_doc).encode(), "content_type": "application/xml"})  # fmt: skip
		return
	if tipo == "nota":
		doc = frappe.get_doc("Nota Fiscal", id)
		if doc.status not in ("Autorizada", "Cancelada"):
			frappe.throw("A nota ainda não foi autorizada.")
		html, nome = documentos.html_nota(doc), f"{doc.tipo_documento}-{doc.numero}"
	else:
		doc = frappe.get_doc("Boleto Cobranca", id)
		html, nome = documentos.html_boleto(doc), f"boleto-{doc.name}"
	conteudo = documentos.pdf(html) if formato == "pdf" else None
	if conteudo:
		frappe.local.response.update({"type": "pdf", "filename": nome + ".pdf", "filecontent": conteudo})
	else:
		html = html.replace("</body>", "<script>window.onload=()=>window.print()</script></body>") if formato == "pdf" else html
		frappe.local.response.update({"type": "download", "filename": nome + ".html", "filecontent": html.encode(), "content_type": "text/html",
		                              "display_content_as": "inline"})  # fmt: skip

