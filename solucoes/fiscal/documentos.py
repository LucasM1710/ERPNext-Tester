"""XML e versões para imprimir (DANFE, DANFSe e boleto).

Na simulação o XML segue a estrutura da NF-e 4.00 / DPS da NFS-e Nacional, mas não é assinado e traz
tpAmb=2 (homologação). Os PDFs saem pelo WeasyPrint quando disponível; senão, a mesma página em HTML
(o navegador imprime em PDF).
"""

import json
from xml.sax.saxutils import escape

import frappe
from frappe.utils import flt, format_datetime, getdate

from solucoes.fiscal import util
from solucoes.fiscal.regras import config, simulacao


def _x(tag, valor):
	return f"<{tag}>{escape(str(valor))}</{tag}>" if valor not in (None, "") else ""


def _dest(nota):
	return frappe._dict(json.loads(nota.destinatario_json or "{}"))


# ===================================================================== XML
def xml_nota(nota):
	cfg = config()
	d = _dest(nota)
	emissao = format_datetime(nota.data_emissao, "yyyy-MM-ddTHH:mm:ss") + "-03:00"
	if nota.tipo_documento == "NFS-e":
		return f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- {"SIMULAÇÃO: documento sem valor fiscal, não assinado" if simulacao(cfg) else "NFS-e"} -->
<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse" versao="1.00">
 <infNFSe Id="NFS{nota.chave_acesso}">
  {_x("nNFSe", nota.numero)}{_x("cLocIncid", cfg.codigo_municipio)}{_x("xLocIncid", cfg.municipio)}{_x("dhProc", emissao)}{_x("nDFSe", nota.protocolo)}
  <emit>{_x("CNPJ", util.limpar_documento(cfg.cnpj))}{_x("IM", cfg.inscricao_municipal)}{_x("xNome", cfg.razao_social)}</emit>
  <valores>{_x("vLiq", f"{flt(nota.valor_liquido):.2f}")}</valores>
  <DPS versao="1.00"><infDPS>
   {_x("tpAmb", "2" if cfg.ambiente != "Produção" else "1")}{_x("dhEmi", emissao)}{_x("serie", nota.serie)}{_x("nDPS", nota.numero)}{_x("cLocEmi", cfg.codigo_municipio)}
   <prest>{_x("CNPJ", util.limpar_documento(cfg.cnpj))}<regTrib>{_x("opSimpNac", "3" if cfg.regime_tributario == "Simples Nacional" else "1")}</regTrib></prest>
   <toma>{_x("CNPJ" if len(util.limpar_documento(d.cnpj_cpf)) == 14 else "CPF", util.limpar_documento(d.cnpj_cpf))}{_x("xNome", d.razao_social)}
    <end><endNac>{_x("cMun", d.codigo_municipio)}{_x("CEP", util.so_digitos(d.cep))}</endNac>{_x("xLgr", d.logradouro)}{_x("nro", d.numero)}{_x("xBairro", d.bairro)}</end>{_x("email", d.email_nota)}
   </toma>
   <serv><cServ>{_x("cTribNac", cfg.codigo_servico_nacional)}{_x("xDescServ", nota.discriminacao)}{_x("cNBS", cfg.codigo_nbs)}</cServ></serv>
   <valores><vServPrest>{_x("vServ", f"{flt(nota.valor_total):.2f}")}</vServPrest>
    <trib><tribMun>{_x("tribISSQN", "1")}{_x("pAliq", f"{flt(nota.aliquota_iss):.2f}")}{_x("tpRetISSQN", "2" if nota.iss_retido else "1")}</tribMun>
     <tribFed>{_x("vRetCP", "0.00")}{_x("vRetIRRF", f"{flt(nota.valor_ir_retido):.2f}")}{_x("vRetCSLL", f"{flt(nota.valor_csll_retido):.2f}")}</tribFed>
    </trib>
   </valores>
  </infDPS></DPS>
 </infNFSe>
</NFSe>
"""
	itens = []
	for n, i in enumerate(nota.itens, 1):
		itens.append(
			f'  <det nItem="{n}"><prod>{_x("cProd", i.item_code or n)}{_x("xProd", i.descricao)}{_x("NCM", i.ncm)}{_x("CFOP", i.cfop)}{_x("uCom", i.unidade)}'
			f'{_x("qCom", f"{flt(i.quantidade):.4f}")}{_x("vUnCom", f"{flt(i.valor_unitario):.2f}")}{_x("vProd", f"{flt(i.valor_total):.2f}")}{_x("indTot", "1")}</prod>'
			f"<imposto><ICMS>{_icms_xml(nota, cfg)}</ICMS></imposto></det>"
		)
	ref = f"<NFref>{_x('refNFe', nota.nf_referenciada)}</NFref>" if nota.nf_referenciada else ""
	return f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- {"SIMULAÇÃO: documento sem valor fiscal, não assinado" if simulacao(cfg) else "NF-e"} -->
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
 <NFe><infNFe Id="NFe{nota.chave_acesso}" versao="4.00">
  <ide>{_x("cUF", util.UF_CODIGO.get((cfg.uf or "").upper(), ""))}{_x("natOp", nota.natureza)}{_x("mod", "55")}{_x("serie", nota.serie)}{_x("nNF", nota.numero)}{_x("dhEmi", emissao)}{_x("tpNF", "1")}{_x("idDest", "1" if (nota.uf_destino or "").upper() == (cfg.uf or "").upper() else "2")}{_x("tpAmb", "2" if cfg.ambiente != "Produção" else "1")}{_x("finNFe", "1")}{ref}</ide>
  <emit>{_x("CNPJ", util.limpar_documento(cfg.cnpj))}{_x("xNome", cfg.razao_social)}{_x("IE", util.so_digitos(cfg.inscricao_estadual))}{_x("CRT", "1" if cfg.regime_tributario == "Simples Nacional" else "3")}</emit>
  <dest>{_x("CNPJ" if len(util.limpar_documento(d.cnpj_cpf)) == 14 else "CPF", util.limpar_documento(d.cnpj_cpf))}{_x("xNome", d.razao_social)}
   <enderDest>{_x("xLgr", d.logradouro)}{_x("nro", d.numero)}{_x("xBairro", d.bairro)}{_x("cMun", d.codigo_municipio)}{_x("xMun", d.municipio)}{_x("UF", (d.uf or "").upper())}{_x("CEP", util.so_digitos(d.cep))}</enderDest>
   {_x("indIEDest", {"Contribuinte": "1", "Isento": "2"}.get(d.contribuinte_icms, "9"))}{_x("IE", util.so_digitos(d.inscricao_estadual) if d.contribuinte_icms == "Contribuinte" else "")}{_x("email", d.email_nota)}
  </dest>
{chr(10).join(itens)}
  <total><ICMSTot>{_x("vBC", f"{flt(nota.base_icms):.2f}")}{_x("vICMS", f"{flt(nota.valor_icms):.2f}")}{_x("vProd", f"{flt(nota.valor_total):.2f}")}{_x("vNF", f"{flt(nota.valor_total):.2f}")}</ICMSTot>
   <IBSCBSTot>{_x("vCBS", f"{flt(nota.valor_cbs):.2f}")}{_x("vIBS", f"{flt(nota.valor_ibs):.2f}")}</IBSCBSTot></total>
  <transp>{_x("modFrete", "9")}</transp>
  <infAdic>{_x("infCpl", nota.informacoes_complementares)}</infAdic>
 </infNFe></NFe>
 <protNFe versao="4.00"><infProt>{_x("tpAmb", "2" if cfg.ambiente != "Produção" else "1")}{_x("chNFe", nota.chave_acesso)}{_x("dhRecbto", emissao)}{_x("nProt", nota.protocolo)}{_x("cStat", "100")}{_x("xMotivo", "Autorizado o uso da NF-e")}</infProt></protNFe>
</nfeProc>
"""


def _icms_xml(nota, cfg):
	nat = frappe.get_cached_doc("Natureza Operacao Fiscal", nota.natureza)
	if cfg.regime_tributario == "Simples Nacional":
		return f"<ICMSSN{nat.csosn or '102'}>{_x('orig', '0')}{_x('CSOSN', nat.csosn or '102')}</ICMSSN{nat.csosn or '102'}>"
	cst = nat.cst_icms or "00"
	return f"<ICMS{cst}>{_x('orig', '0')}{_x('CST', cst)}{_x('vBC', f'{flt(nota.base_icms):.2f}')}{_x('pICMS', f'{flt(nota.aliquota_icms):.2f}')}{_x('vICMS', f'{flt(nota.valor_icms):.2f}')}</ICMS{cst}>"


# ===================================================================== HTML para imprimir
ESTILO = """
@page { size: A4; margin: 12mm; }
* { box-sizing: border-box; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 10px; color: #111; margin: 0; }
.doc { max-width: 190mm; margin: 0 auto; position: relative; }
.marca { position: fixed; top: 38%; left: 0; right: 0; text-align: center; font-size: 46px; font-weight: 800; color: rgba(220, 38, 38, .13);
  transform: rotate(-24deg); letter-spacing: 3px; pointer-events: none; }
table { width: 100%; border-collapse: collapse; }
td, th { border: 1px solid #333; padding: 3px 5px; vertical-align: top; }
th { background: #eee; font-size: 8px; text-transform: uppercase; text-align: left; }
.r { font-size: 7px; text-transform: uppercase; color: #444; display: block; }
.v { font-size: 10px; font-weight: 600; }
.g { font-size: 13px; font-weight: 700; }
.c { text-align: center; } .d { text-align: right; }
h1 { font-size: 15px; margin: 0; }
.aviso { border: 2px solid #dc2626; color: #b91c1c; padding: 6px; text-align: center; font-weight: 700; margin-bottom: 6px; }
.mono { font-family: "Courier New", monospace; letter-spacing: .5px; }
.tracejado { border-top: 1px dashed #555; margin: 14px 0 8px; }
"""


def _pagina(titulo, corpo, sim):
	marca = '<div class="marca">SEM VALOR FISCAL<br>SIMULAÇÃO</div>' if sim else ""
	aviso = '<div class="aviso">SIMULAÇÃO — DOCUMENTO SEM VALOR FISCAL. Gerado para testes do processo.</div>' if sim else ""
	return f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{escape(titulo)}</title><style>{ESTILO}</style></head><body><div class="doc">{marca}{aviso}{corpo}</div></body></html>'


def _cel(rotulo, valor, extra=""):
	return f'<td {extra}><span class="r">{rotulo}</span><span class="v">{escape(str(valor or ""))}</span></td>'


def _end(o):
	partes = [o.logradouro, o.numero, o.complemento, o.bairro]
	return ", ".join(p for p in partes if p) + f" — {o.municipio or ''}/{(o.uf or '').upper()} — CEP {util.formatar_cep(o.cep)}"


def html_nota(nota):
	cfg = config()
	sim = (nota.ambiente or cfg.ambiente) != "Produção"
	d = _dest(nota)
	if nota.status == "Cancelada":
		sim_corpo = '<div class="aviso">NOTA CANCELADA</div>'
	else:
		sim_corpo = ""
	if nota.tipo_documento == "NFS-e":
		corpo = f"""{sim_corpo}
<table><tr><td style="width:65%"><h1>DANFSe — Documento Auxiliar da NFS-e</h1><div>{escape(cfg.razao_social or "")} · CNPJ {util.formatar_documento(cfg.cnpj)} · IM {escape(cfg.inscricao_municipal or "")}</div>
<div>{escape(_end(cfg))}</div></td>
{_cel("Número da NFS-e", nota.numero, 'class="c"')}{_cel("Emissão", format_datetime(nota.data_emissao, "dd/MM/yyyy HH:mm"), 'class="c"')}</tr>
<tr><td colspan="3"><span class="r">Chave de acesso</span><span class="v mono">{util.formatar_chave(nota.chave_acesso)}</span></td></tr></table>
<table style="margin-top:6px"><tr><th colspan="4">Tomador do serviço</th></tr>
<tr>{_cel("Nome / Razão social", d.razao_social, 'colspan="2"')}{_cel("CNPJ/CPF", util.formatar_documento(d.cnpj_cpf))}{_cel("Inscrição municipal", d.inscricao_municipal)}</tr>
<tr>{_cel("Endereço", _end(d), 'colspan="3"')}{_cel("E-mail", d.email_nota)}</tr></table>
<table style="margin-top:6px"><tr><th>Discriminação do serviço</th></tr><tr><td style="height:120px;white-space:pre-line;font-size:10px">{escape(nota.discriminacao or "")}</td></tr></table>
<table style="margin-top:6px"><tr><th colspan="4">Serviço e tributação</th></tr>
<tr>{_cel("Código de tributação nacional", cfg.codigo_servico_nacional)}{_cel("Item LC 116", cfg.item_lista_servico)}{_cel("NBS", cfg.codigo_nbs)}{_cel("Município de incidência", f"{cfg.municipio}/{cfg.uf}")}</tr>
<tr>{_cel("Valor do serviço", util.moeda(nota.valor_total))}{_cel("Alíquota ISS", f"{flt(nota.aliquota_iss):g}%")}{_cel("Valor do ISS", util.moeda(nota.valor_iss))}{_cel("ISS retido pelo tomador", "Sim" if nota.iss_retido else "Não")}</tr>
<tr>{_cel("PIS retido", util.moeda(nota.valor_pis_retido))}{_cel("COFINS retido", util.moeda(nota.valor_cofins_retido))}{_cel("CSLL retido", util.moeda(nota.valor_csll_retido))}{_cel("IR retido", util.moeda(nota.valor_ir_retido))}</tr>
<tr>{_cel("CBS (informativo)", util.moeda(nota.valor_cbs))}{_cel("IBS (informativo)", util.moeda(nota.valor_ibs))}{_cel("Total retido", util.moeda(nota.valor_retencoes))}<td><span class="r">Valor líquido</span><span class="g">{util.moeda(nota.valor_liquido)}</span></td></tr></table>
<p style="margin-top:8px">Protocolo {escape(nota.protocolo or "")} · Fatura {escape(nota.fatura or "")} · Consulte a autenticidade no portal da NFS-e Nacional (gov.br/nfse) pela chave de acesso.</p>"""
		return _pagina(f"NFS-e {nota.numero}", corpo, sim)

	linhas = "".join(
		f'<tr><td>{escape(i.item_code or "")}</td><td>{escape(i.descricao or "")}{(" · Série " + escape(i.numero_serie)) if i.numero_serie else ""}</td><td class="c">{i.ncm or ""}</td>'
		f'<td class="c">{i.cfop or ""}</td><td class="c">{escape(i.unidade or "")}</td><td class="d">{flt(i.quantidade):g}</td><td class="d">{util.moeda(i.valor_unitario)}</td><td class="d">{util.moeda(i.valor_total)}</td></tr>'
		for i in nota.itens
	)
	corpo = f"""{sim_corpo}
<table><tr><td style="width:42%"><h1>{escape(cfg.razao_social or "")}</h1><div>{escape(_end(cfg))}</div><div>Fone {escape(cfg.telefone or "")}</div></td>
<td class="c" style="width:18%"><div class="g">DANFE</div><div>Documento Auxiliar da Nota Fiscal Eletrônica</div><div>1 - SAÍDA</div><div class="g">Nº {nota.numero}</div><div>Série {nota.serie}</div></td>
<td><div class="c" style="margin-bottom:4px">{util.svg_qrcode(nota.chave_acesso or "", 2) if nota.chave_acesso else ""}</div><span class="r">Chave de acesso</span><span class="v mono" style="font-size:9px">{util.formatar_chave(nota.chave_acesso)}</span>
<span class="r" style="margin-top:3px">Consulta de autenticidade no portal nacional da NF-e (www.nfe.fazenda.gov.br/portal)</span></td></tr></table>
<table><tr>{_cel("Natureza da operação", nota.natureza, 'style="width:60%"')}{_cel("Protocolo de autorização de uso", f"{nota.protocolo} — {format_datetime(nota.data_emissao, 'dd/MM/yyyy HH:mm')}")}</tr>
<tr>{_cel("Inscrição estadual", cfg.inscricao_estadual)}{_cel("CNPJ", util.formatar_documento(cfg.cnpj))}</tr></table>
<table style="margin-top:6px"><tr><th colspan="4">Destinatário / Remetente</th></tr>
<tr>{_cel("Nome / Razão social", d.razao_social, 'colspan="2"')}{_cel("CNPJ/CPF", util.formatar_documento(d.cnpj_cpf))}{_cel("Data de emissão", format_datetime(nota.data_emissao, "dd/MM/yyyy"))}</tr>
<tr>{_cel("Endereço", _end(d), 'colspan="2"')}{_cel("Inscrição estadual", d.inscricao_estadual or ("ISENTO" if d.contribuinte_icms == "Isento" else ""))}{_cel("UF", (d.uf or "").upper())}</tr></table>
<table style="margin-top:6px"><tr><th colspan="5">Cálculo do imposto</th></tr>
<tr>{_cel("Base de cálculo do ICMS", util.moeda(nota.base_icms))}{_cel("Valor do ICMS", util.moeda(nota.valor_icms))}{_cel("CBS (informativo)", util.moeda(nota.valor_cbs))}{_cel("IBS (informativo)", util.moeda(nota.valor_ibs))}<td><span class="r">Valor total da nota</span><span class="g">{util.moeda(nota.valor_total)}</span></td></tr></table>
<table style="margin-top:6px"><tr><th>Código</th><th>Descrição</th><th>NCM</th><th>CFOP</th><th>Un</th><th>Qtd</th><th>Valor unit.</th><th>Valor total</th></tr>{linhas}</table>
<table style="margin-top:6px"><tr><th>Dados adicionais</th></tr><tr><td style="height:70px">{escape(nota.informacoes_complementares or "")}{("<br>Nota referenciada: " + util.formatar_chave(nota.nf_referenciada)) if nota.nf_referenciada else ""}</td></tr></table>"""
	return _pagina(f"NF-e {nota.numero}", corpo, sim)


def html_boleto(bol):
	cfg = config()
	sim = (bol.ambiente or cfg.ambiente) != "Produção"
	venc = getdate(bol.vencimento).strftime("%d/%m/%Y")
	pix = ""
	if bol.pix_copia_cola:
		pix = f"""<table style="margin-top:8px"><tr><td style="width:120px" class="c">{util.svg_qrcode(bol.pix_copia_cola, 3)}</td>
<td><span class="g">Pague com Pix</span><p>Abra o app do seu banco, escolha Pix &gt; Ler QR Code, ou use o Pix Copia e Cola:</p><p class="mono" style="word-break:break-all;font-size:8px">{escape(bol.pix_copia_cola)}</p></td></tr></table>"""
	if bol.status == "Pago":
		pago = f'<div class="aviso" style="border-color:#059669;color:#047857">PAGO em {getdate(bol.pago_em).strftime("%d/%m/%Y")} — {util.moeda(bol.valor_pago)}</div>'
	elif bol.status == "Cancelado":
		pago = '<div class="aviso">BOLETO CANCELADO</div>'
	else:
		pago = ""
	ficha = f"""<table><tr><td style="width:22%" class="g">{escape(cfg.banco_nome or "")}</td><td style="width:10%" class="g c">{escape(cfg.banco_codigo or "")}-9</td>
<td class="g d mono">{escape(bol.linha_digitavel or "")}</td></tr></table>
<table><tr>{_cel("Local de pagamento", "Pagável em qualquer banco ou pelo Pix", 'colspan="3"')}{_cel("Vencimento", venc, 'class="d"')}</tr>
<tr>{_cel("Beneficiário", f"{cfg.razao_social} — CNPJ {util.formatar_documento(cfg.cnpj)}", 'colspan="3"')}{_cel("Agência / Código do beneficiário", f"{cfg.agencia} / {cfg.conta}", 'class="d"')}</tr>
<tr>{_cel("Data do documento", getdate(bol.emissao).strftime("%d/%m/%Y"))}{_cel("Nº do documento", f"{bol.fatura} {bol.parcela or ''}".strip())}{_cel("Carteira", cfg.carteira)}{_cel("Nosso número", bol.nosso_numero, 'class="d"')}</tr>
<tr><td colspan="3" rowspan="2"><span class="r">Instruções (texto de responsabilidade do beneficiário)</span>{escape(bol.instrucoes or "")}<br>Multa de {flt(bol.multa_percentual):g}% após o vencimento e juros de {flt(bol.juros_mes_percentual):g}% ao mês.{("<br>Referente à nota " + escape(bol.nota_fiscal)) if bol.nota_fiscal else ""}</td>
<td class="d"><span class="r">(=) Valor do documento</span><span class="g">{util.moeda(bol.valor)}</span></td></tr><tr>{_cel("(+) Mora / Multa", "", 'class="d"')}</tr>
<tr>{_cel("Pagador", f"{bol.nome_cliente} — {util.formatar_documento(bol.documento_cliente)}", 'colspan="4"')}</tr></table>
<div style="margin-top:6px">{util.svg_codigo_barras(bol.codigo_barras) if bol.codigo_barras else ""}</div>"""
	parcela = f" · Parcela {escape(bol.parcela)}" if bol.parcela else ""
	corpo = f"""{pago}<h1>Boleto — {escape(bol.nome_cliente or "")}</h1><p>Valor {util.moeda(bol.valor)} · Vencimento {venc}{parcela}</p>{pix}
<div class="tracejado"></div><span class="r">Recibo do pagador</span>{ficha}"""
	return _pagina(f"Boleto {bol.name}", corpo, sim)


def pdf(html):
	"""PDF pelo WeasyPrint (Frappe 16 já traz); devolve None se não houver, para servir o HTML."""
	try:
		from weasyprint import HTML
	except Exception:
		return None
	return HTML(string=html).write_pdf()
