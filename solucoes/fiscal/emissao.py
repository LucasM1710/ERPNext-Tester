"""Emissão: fatura -> nota(s) -> boleto -> e-mail -> baixa do pagamento no ERP.

Usado pela API (tela /fiscal), pelo gancho da fatura (emissão automática) e pelo job diário.
"""

import json

import frappe
from frappe.utils import flt, getdate, now_datetime, today

from solucoes.fiscal import documentos, regras, util
from solucoes.fiscal.provedores import provedor_boleto, provedor_notas
from solucoes.fiscal.regras import config


def evento(doc, titulo, detalhe=None):
	doc.append("eventos", {"data": now_datetime(), "evento": titulo, "detalhe": detalhe, "usuario": frappe.session.user})


# ===================================================================== fatura
def emitir_fatura(fatura):
	"""Emite o que falta da fatura (NFS-e e/ou NF-e) e, com tudo autorizado, o boleto. Devolve um resumo para a tela."""
	plano = regras.planejar_fatura(fatura)
	if not plano["pode_emitir"]:
		erros = [c["texto"] for c in plano["checagens"] if c["nivel"] == "erro"]
		frappe.throw("Ainda não dá para emitir:\n• " + "\n• ".join(erros) if erros else "Não há nada a emitir nesta fatura.")
	si = frappe.get_doc("Sales Invoice", fatura)
	df = regras.dados_parte("Customer", si.customer)
	resultado = {"notas": [], "boleto": None, "boletos": []}
	for doc in plano["documentos"]:
		if doc["ja_emitida"]:
			continue
		nota = criar_nota(doc["tipo"], doc["natureza"], "Customer", si.customer, df, doc["itens"], doc["valores"],
		                  fatura=si.name, discriminacao=doc.get("discriminacao"))  # fmt: skip
		transmitir(nota)
		resultado["notas"].append(resumo_nota(nota))
	frappe.db.commit()  # nota autorizada fica gravada mesmo se o boleto falhar depois

	todas = frappe.get_all("Nota Fiscal", filters={"fatura": si.name, "status": "Autorizada"}, pluck="name")
	plano = regras.planejar_fatura(si.name)
	if plano["boleto"] and not plano["boleto"].get("ja_emitido") and all(d["ja_emitida"] for d in plano["documentos"]):
		for parcela in plano["boleto"]["parcelas"]:  # um boleto por parcela (ou um só)
			bol = criar_boleto(si, parcela, nota=todas[0] if todas else None)
			resultado["boletos"].append(resumo_boleto(bol))
		resultado["boleto"] = resultado["boletos"][0]
	if all(n["status"] == "Autorizada" for n in resultado["notas"]):
		enviar_ao_cliente(si.name)
	return resultado


def emitir_automatico(fatura):
	"""Gancho da fatura confirmada (job): só emite se a conferência estiver toda verde."""
	frappe.set_user("Administrator")
	plano = regras.planejar_fatura(fatura)
	if not plano["pode_emitir"]:
		erros = [c["texto"] for c in plano["checagens"] if c["nivel"] == "erro"]
		if erros:
			frappe.get_doc("Sales Invoice", fatura).add_comment("Comment", "Nota fiscal não emitida automaticamente: " + " ".join(erros))
		return
	emitir_fatura(fatura)


def ao_confirmar_fatura(doc, method=None):
	cfg = config()
	if not cfg.emitir_ao_confirmar_fatura or doc.is_return or (cfg.empresa and doc.company != cfg.empresa):
		return
	frappe.enqueue("solucoes.fiscal.emissao.emitir_automatico", fatura=doc.name, enqueue_after_commit=True, queue="short")


# ===================================================================== nota
def criar_nota(tipo, natureza, tipo_parte, parte, df, itens, valores, fatura=None, discriminacao=None,
               nf_referenciada=None, prazo_retorno=None, texto_complementar=None):  # fmt: skip
	cfg = config()
	nat = frappe.get_cached_doc("Natureza Operacao Fiscal", natureza)
	destinatario = {k: df.get(k) for k in ("razao_social", "cnpj_cpf", "tipo_pessoa", "contribuinte_icms", "inscricao_estadual", "inscricao_municipal",
	                                       "email_nota", "logradouro", "numero", "complemento", "bairro", "cep", "municipio", "codigo_municipio", "uf")}  # fmt: skip
	complementar = " ".join(t for t in (texto_complementar, cfg.informacoes_complementares if tipo == "NF-e" else None) if t)
	nota = frappe.get_doc({
		"doctype": "Nota Fiscal", "tipo_documento": tipo, "natureza": natureza, "status": "Rascunho", "ambiente": cfg.ambiente,
		"fatura": fatura, "tipo_parte": tipo_parte, "parte": parte, "nome_parte": df.razao_social,
		"documento_parte": util.formatar_documento(df.cnpj_cpf), "uf_destino": (df.uf or "").upper(),
		"discriminacao": discriminacao, "informacoes_complementares": complementar or None,
		"nf_referenciada": nf_referenciada, "prazo_retorno": prazo_retorno,
		"situacao_remessa": "Em aberto" if nat.controla_retorno else None,
		"destinatario_json": json.dumps(destinatario, ensure_ascii=False),
		"itens": [{k: i.get(k) for k in ("item_code", "descricao", "ncm", "cfop", "unidade", "quantidade", "valor_unitario", "valor_total", "numero_serie", "referencia")} for i in itens],
		**{k: v for k, v in valores.items() if k != "cfop"}, "cfop": valores.get("cfop"),
	})  # fmt: skip
	evento(nota, "Nota preparada", f"{tipo} · {natureza}")
	nota.insert(ignore_permissions=True)
	return nota


def transmitir(nota):
	nota.status = "Processando"
	try:
		r = provedor_notas().emitir(nota)
	except Exception as e:
		frappe.log_error(title=f"Fiscal: falha ao transmitir {nota.name}")
		r = {"status": "Rejeitada", "codigo": "", "mensagem": f"Falha de comunicação: {e}", "orientacao": "Tente de novo em alguns minutos. Se repetir, avise a TI."}
	nota.codigo_retorno = r.get("codigo")
	nota.mensagem_retorno = r.get("mensagem")
	if r["status"] == "Autorizada":
		nota.update({"status": "Autorizada", "numero": r["numero"], "serie": r["serie"], "chave_acesso": r["chave"], "protocolo": r["protocolo"],
		             "data_emissao": r["data"], "orientacao": None})  # fmt: skip
		evento(nota, f"{nota.tipo_documento} {r['numero']} autorizada", f"{r['mensagem']} Protocolo {r['protocolo']}.")
		nota.save(ignore_permissions=True)
		_anexar_xml(nota)
	else:
		nota.status = "Rejeitada"
		nota.orientacao = r.get("orientacao")
		evento(nota, "Rejeitada" + (f" ({r['codigo']})" if r.get("codigo") else ""), f"{r['mensagem']} {r.get('orientacao') or ''}".strip())
		nota.save(ignore_permissions=True)
	return nota


def _anexar_xml(nota):
	nome = f"{nota.tipo_documento.replace('-', '')}-{nota.chave_acesso}.xml"
	arq = frappe.get_doc({"doctype": "File", "file_name": nome, "attached_to_doctype": "Nota Fiscal", "attached_to_name": nota.name,
	                      "attached_to_field": "xml", "is_private": 1, "content": documentos.xml_nota(nota)})  # fmt: skip
	arq.save(ignore_permissions=True)
	nota.db_set("xml", arq.file_url)


def tentar_de_novo(nota_id):
	"""Reenvia uma nota rejeitada com os dados atuais do cadastro (o cliente pode ter sido corrigido)."""
	nota = frappe.get_doc("Nota Fiscal", nota_id)
	if nota.status != "Rejeitada":
		frappe.throw("Só notas rejeitadas podem ser reenviadas.")
	if nota.fatura:
		nota.status = "Substituída"  # a rejeitada fica no histórico; a fatura gera uma nova
		evento(nota, "Substituída por novo envio")
		nota.save(ignore_permissions=True)
		return emitir_fatura(nota.fatura)
	df = regras.dados_parte(nota.tipo_parte, nota.parte)
	if df:
		nota.destinatario_json = json.dumps({k: df.get(k) for k in json.loads(nota.destinatario_json or "{}")}, ensure_ascii=False)
	evento(nota, "Novo envio")
	transmitir(nota)
	return {"notas": [resumo_nota(nota)], "boleto": None}


def cancelar_nota(nota_id, motivo):
	nota = frappe.get_doc("Nota Fiscal", nota_id)
	if nota.status != "Autorizada":
		frappe.throw("Só notas autorizadas podem ser canceladas.")
	if len((motivo or "").strip()) < 15:
		frappe.throw("Escreva o motivo do cancelamento com pelo menos 15 caracteres (regra da SEFAZ e da prefeitura).")
	filtro = {"fatura": nota.fatura} if nota.fatura else {"nota_fiscal": nota.name}
	boletos = frappe.get_all("Boleto Cobranca", filters={**filtro, "status": ["!=", "Cancelado"]}, fields=["name", "status", "parcela"])
	pagos = [b for b in boletos if b.status == "Pago"]
	if pagos:
		qual = "Uma parcela" if any(b.parcela for b in pagos) else "O boleto"
		frappe.throw(f"{qual} desta nota já foi paga. Antes de cancelar, o financeiro precisa devolver o valor ou combinar com o cliente.")
	r = provedor_notas().cancelar(nota, motivo)
	if not r["ok"]:
		frappe.throw(r["mensagem"])
	nota.update({"status": "Cancelada", "motivo_cancelamento": motivo.strip(), "cancelada_em": now_datetime()})
	evento(nota, "Cancelada", f"{r['mensagem']} Protocolo {r.get('protocolo')}. Motivo: {motivo.strip()}")
	if nota.situacao_remessa == "Em aberto":
		nota.situacao_remessa = None
	nota.save(ignore_permissions=True)
	for b in boletos:  # todos os boletos (parcelas) em aberto da nota
		cancelar_boleto(b.name, "Nota fiscal cancelada")
	return resumo_nota(nota)


def registrar_retorno(nota_id, chave=None, data=None):
	"""Remessa nossa que voltou (o fornecedor emite a nota de retorno; aqui só registramos)."""
	nota = frappe.get_doc("Nota Fiscal", nota_id)
	if nota.situacao_remessa != "Em aberto":
		frappe.throw("Esta remessa não está em aberto.")
	if chave:
		info = util.decodificar_chave_nfe(chave)
		if not info["valida"]:
			frappe.throw("Chave da nota de retorno: " + info["motivo"])
		chave = info["chave"]
	nota.update({"situacao_remessa": "Retornada", "retorno_chave": chave, "retorno_data": getdate(data or today())})
	evento(nota, "Retorno registrado", f"Chave {util.formatar_chave(chave)}" if chave else "Sem chave informada")
	nota.save(ignore_permissions=True)
	return resumo_nota(nota)


def emitir_avulsa(dados):
	"""Remessa ou retorno (NF-e sem fatura)."""
	plano = regras.planejar_avulsa(dados)
	if not plano["pode_emitir"]:
		frappe.throw("Ainda não dá para emitir:\n• " + "\n• ".join(c["texto"] for c in plano["checagens"] if c["nivel"] == "erro"))
	dados = frappe._dict(frappe.parse_json(dados) if isinstance(dados, str) else dados)
	df = regras.dados_parte(dados.tipo_parte, dados.parte)
	nota = criar_nota("NF-e", plano["natureza"], dados.tipo_parte, dados.parte, df, plano["itens"], plano["valores"],
	                  nf_referenciada=plano["nf_referenciada"], prazo_retorno=plano["prazo_retorno"], texto_complementar=plano["texto_complementar"])  # fmt: skip
	transmitir(nota)
	if nota.status == "Autorizada":
		enviar_nota(nota)
	return {"notas": [resumo_nota(nota)], "boleto": None}


# ===================================================================== boleto
def criar_boleto(si, parcela, nota=None):
	"""`parcela`: valor, vencimento e, se parcelada, parcela ("2/3"), payment_term e valor_retencao."""
	cfg = config()
	df = regras.dados_parte("Customer", si.customer)
	bol = frappe.get_doc({
		"doctype": "Boleto Cobranca", "status": "Em aberto", "cliente": si.customer, "nome_cliente": df.razao_social if df else si.customer_name,
		"documento_cliente": df.cnpj_cpf if df else None, "email_cliente": df.email_nota if df else None, "fatura": si.name, "nota_fiscal": nota,
		"ambiente": cfg.ambiente, "valor": parcela["valor"], "emissao": today(), "vencimento": parcela["vencimento"],
		"parcela": parcela.get("parcela"), "payment_term": parcela.get("payment_term"), "valor_retencao": flt(parcela.get("valor_retencao")),
		"multa_percentual": cfg.multa_percentual, "juros_mes_percentual": cfg.juros_mes_percentual, "instrucoes": cfg.instrucoes_boleto,
		"banco": f"{cfg.banco_codigo} {cfg.banco_nome}",
	})  # fmt: skip
	bol.insert(ignore_permissions=True)
	r = provedor_boleto().registrar(bol)
	bol.update({"nosso_numero": r["nosso_numero"], "codigo_barras": r["codigo_barras"], "linha_digitavel": r["linha_digitavel"], "pix_copia_cola": r.get("pix")})
	evento(bol, "Boleto registrado", (f"Parcela {bol.parcela} · " if bol.parcela else "")
	       + f"{util.moeda(bol.valor)} · vence {getdate(bol.vencimento).strftime('%d/%m/%Y')} · nosso número {bol.nosso_numero}")  # fmt: skip
	bol.save(ignore_permissions=True)
	if nota and not frappe.db.get_value("Nota Fiscal", nota, "boleto"):  # a nota aponta para o 1º boleto
		frappe.db.set_value("Nota Fiscal", nota, "boleto", bol.name)
	return bol


def cancelar_boleto(boleto_id, motivo):
	bol = frappe.get_doc("Boleto Cobranca", boleto_id)
	if bol.status in ("Pago", "Cancelado"):
		frappe.throw(f"O boleto já está {bol.status.lower()}.")
	r = provedor_boleto().cancelar(bol)
	bol.update({"status": "Cancelado", "motivo_cancelamento": motivo})
	evento(bol, "Cancelado", f"{r['mensagem']} Motivo: {motivo}")
	bol.save(ignore_permissions=True)
	return resumo_boleto(bol)


def registrar_pagamento(boleto_id, valor=None, data=None, origem="Banco"):
	"""Pagamento confirmado (aviso do banco ou simulação): marca o boleto e lança o recebimento na fatura."""
	bol = frappe.get_doc("Boleto Cobranca", boleto_id)
	if bol.status in ("Pago", "Cancelado"):
		frappe.throw(f"O boleto já está {bol.status.lower()}.")
	valor = flt(valor, 2) or flt(bol.valor)
	if valor <= 0:
		frappe.throw("Informe o valor pago.")
	data = getdate(data or today())
	pe = _lancar_recebimento(bol, valor, data)
	diferenca = flt(valor - flt(bol.valor), 2)
	detalhe = f"{util.moeda(valor)} em {data.strftime('%d/%m/%Y')} ({origem})."
	if diferenca < -0.009:
		detalhe += f" Pago {util.moeda(-diferenca)} a menos que o boleto: essa diferença continua em aberto na fatura."
	elif diferenca > 0.009:
		detalhe += f" Pago {util.moeda(diferenca)} a mais (multa/juros): fica como crédito do cliente no ERP, para o financeiro classificar."
	detalhe += f" Recebimento lançado no ERP: {pe}." if pe else " Lance o recebimento no ERP manualmente."
	bol.update({"status": "Pago", "pago_em": data, "valor_pago": valor, "pagamento": pe})
	evento(bol, "Pago", detalhe)
	bol.save(ignore_permissions=True)
	return resumo_boleto(bol)


def _lancar_recebimento(bol, valor, data):
	if not bol.fatura:
		return None
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	cfg = config()
	si = frappe.get_doc("Sales Invoice", bol.fatura)
	if flt(si.outstanding_amount) <= 0:
		return None
	try:
		pe = get_payment_entry("Sales Invoice", si.name)
		pe.posting_date = data
		pe.reference_no = f"Boleto {bol.name} / {bol.nosso_numero}"
		pe.reference_date = data
		if cfg.conta_recebimento:
			pe.paid_to = cfg.conta_recebimento
			pe.paid_to_account_currency = frappe.get_cached_value("Account", cfg.conta_recebimento, "account_currency")
		# só a retenção prevista para este boleto vai para a conta de retidos; o que faltar fica em aberto na fatura
		previsto = flt(bol.valor_retencao) if bol.valor_retencao is not None else max(flt(flt(si.outstanding_amount) - flt(bol.valor), 2), 0)
		retido = previsto if cfg.conta_retencoes else 0
		if len(pe.references) > 1:  # fatura parcelada: lança na parcela deste boleto
			ref = next((r for r in pe.references if bol.payment_term and r.get("payment_term") == bol.payment_term), pe.references[0])
			pe.set("references", [ref])
		pe.paid_amount = pe.received_amount = valor
		pe.base_paid_amount = pe.base_received_amount = valor
		if retido > 0.009:
			centro = frappe.get_cached_value("Company", si.company, "cost_center")
			pe.append("deductions", {"account": cfg.conta_retencoes, "cost_center": centro, "amount": retido})
		pe.references[0].allocated_amount = min(flt(valor + retido, 2), flt(pe.references[0].outstanding_amount or si.outstanding_amount))
		pe.set_amounts()
		pe.insert(ignore_permissions=True)
		pe.submit()
		return pe.name
	except Exception:
		frappe.log_error(title=f"Fiscal: não foi possível lançar o recebimento do boleto {bol.name}")
		frappe.clear_messages()
		return None


def atualizar_boletos():
	"""Job diário: marca vencidos e registra lembretes/cobranças (e-mail só fora da simulação)."""
	cfg = config()
	hoje = getdate(today())
	for b in frappe.get_all("Boleto Cobranca", filters={"status": ["in", ["Em aberto", "Vencido"]]}, fields=["name", "vencimento", "status", "ultimo_lembrete"]):
		bol = None
		venc = getdate(b.vencimento)
		if b.status == "Em aberto" and venc < hoje:
			bol = frappe.get_doc("Boleto Cobranca", b.name)
			bol.status = "Vencido"
			evento(bol, "Venceu sem pagamento")
		lembrar = (venc - hoje).days == (cfg.lembrete_dias_antes or 0) or (hoje - venc).days == (cfg.cobranca_dias_depois or 0)
		if lembrar and getdate(b.ultimo_lembrete or "1900-01-01") < hoje:
			bol = bol or frappe.get_doc("Boleto Cobranca", b.name)
			antes = venc >= hoje
			_avisar(bol, "Lembrete de vencimento" if antes else "Cobrança de boleto vencido")
			bol.ultimo_lembrete = hoje
		if bol:
			bol.save(ignore_permissions=True)
	frappe.db.commit()


# ===================================================================== e-mail
def enviar_ao_cliente(fatura):
	for n in frappe.get_all("Nota Fiscal", filters={"fatura": fatura, "status": "Autorizada", "email_enviado_em": ["is", "not set"]}, pluck="name"):
		enviar_nota(frappe.get_doc("Nota Fiscal", n))


def enviar_nota(nota):
	cfg = config()
	if not cfg.enviar_email_cliente:
		return
	d = frappe._dict(json.loads(nota.destinatario_json or "{}"))
	if not d.email_nota:
		evento(nota, "E-mail não enviado", "O cliente não tem e-mail para notas no cadastro fiscal.")
		nota.save(ignore_permissions=True)
		return
	bol = frappe.get_doc("Boleto Cobranca", nota.boleto) if nota.boleto else None
	parcelas = frappe.get_all("Boleto Cobranca", filters={"fatura": nota.fatura, "status": ["!=", "Cancelado"]}, pluck="name", order_by="vencimento asc") if nota.fatura else []
	assunto = f"{nota.tipo_documento} nº {nota.numero} — {cfg.nome_fantasia or cfg.razao_social}"
	anexos = [f"{nota.tipo_documento} {nota.numero} (PDF)", "XML"] + ([f"{len(parcelas)} boletos (PDF)" if len(parcelas) > 1 else "Boleto (PDF)"] if bol else [])
	if cfg.ambiente == "Simulação":
		evento(nota, "E-mail (simulado)", f"Para {d.email_nota} · {assunto} · anexos: {', '.join(anexos)}")
	else:
		arquivos = [{"fname": f"{nota.tipo_documento}-{nota.numero}.pdf", "fcontent": documentos.pdf(documentos.html_nota(nota)) or documentos.html_nota(nota)},
		            {"fname": f"{nota.tipo_documento}-{nota.chave_acesso}.xml", "fcontent": documentos.xml_nota(nota)}]  # fmt: skip
		for nome in parcelas or ([bol.name] if bol else []):
			b = frappe.get_doc("Boleto Cobranca", nome)
			arquivos.append({"fname": f"boleto-{b.name}.pdf", "fcontent": documentos.pdf(documentos.html_boleto(b)) or documentos.html_boleto(b)})
		frappe.sendmail(recipients=[d.email_nota], subject=assunto, message=_corpo_email(nota, parcelas, cfg), attachments=arquivos,
		                reference_doctype="Nota Fiscal", reference_name=nota.name)  # fmt: skip
		evento(nota, "E-mail enviado", f"Para {d.email_nota}")
	nota.email_enviado_em = now_datetime()
	nota.save(ignore_permissions=True)


def _corpo_email(nota, parcelas, cfg):
	t = f"<p>Olá,</p><p>Segue a {nota.tipo_documento} nº {nota.numero}, no valor de {util.moeda(nota.valor_total)}.</p>"
	boletos = [frappe.get_doc("Boleto Cobranca", n) for n in parcelas]
	if boletos:
		t += "<p>Boletos (você também pode pagar pelo Pix com o QR Code de cada boleto):</p><ul>"
		for b in boletos:
			rotulo = f"Parcela {b.parcela}: " if b.parcela else ""
			t += f"<li>{rotulo}{util.moeda(b.valor)}, vence em {getdate(b.vencimento).strftime('%d/%m/%Y')} — linha digitável <b>{b.linha_digitavel}</b></li>"
		t += "</ul>"
	return t + f"<p>Obrigado,<br>{cfg.nome_fantasia or cfg.razao_social}</p>"


def _avisar(bol, titulo):
	cfg = config()
	if cfg.ambiente == "Simulação" or not bol.email_cliente:
		evento(bol, titulo + (" (simulado)" if cfg.ambiente == "Simulação" else " não enviado: cliente sem e-mail"), f"Para {bol.email_cliente or '—'}")
		return
	frappe.sendmail(recipients=[bol.email_cliente], subject=f"{titulo} — {util.moeda(bol.valor)} — {cfg.nome_fantasia or cfg.razao_social}",
	                message=f"<p>Olá,</p><p>{titulo}: boleto de {util.moeda(bol.valor)} com vencimento em {getdate(bol.vencimento).strftime('%d/%m/%Y')}.</p>"
	                f"<p>Linha digitável: <b>{bol.linha_digitavel}</b></p>", reference_doctype="Boleto Cobranca", reference_name=bol.name)  # fmt: skip
	evento(bol, titulo, f"Para {bol.email_cliente}")


# ===================================================================== resumos para a tela
def resumo_nota(nota):
	return {
		"id": nota.name, "tipo": nota.tipo_documento, "status": nota.status, "numero": nota.numero, "natureza": nota.natureza,
		"nome": nota.nome_parte, "valor": flt(nota.valor_total), "mensagem": nota.mensagem_retorno, "orientacao": nota.orientacao,
		"codigo": nota.codigo_retorno, "fatura": nota.fatura,
	}  # fmt: skip


def resumo_boleto(bol):
	return {"id": bol.name, "status": bol.status, "valor": flt(bol.valor), "vencimento": str(bol.vencimento), "linha_digitavel": bol.linha_digitavel, "parcela": bol.parcela}


def prazo_vencido(nota):
	return nota.prazo_retorno and getdate(nota.prazo_retorno) < getdate(today())


def dias_fora(nota):
	return (getdate(today()) - getdate(nota.data_emissao or nota.creation)).days

