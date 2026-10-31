"""Cálculos dos documentos fiscais e de cobrança (sem dependência do Frappe).

- CNPJ (inclusive o alfanumérico, a partir de jul/2026) e CPF;
- chave de acesso da NF-e (44 dígitos) e da NFS-e Nacional (50 dígitos);
- boleto FEBRABAN: fator de vencimento, código de barras, linha digitável e desenho do código (Interleaved 2 of 5);
- Pix copia e cola (BR Code / EMV) com CRC16.
"""

import io
import re
from datetime import date

UF_CODIGO = {
	"RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17", "MA": "21", "PI": "22",
	"CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27", "SE": "28", "BA": "29", "MG": "31", "ES": "32",
	"RJ": "33", "SP": "35", "PR": "41", "SC": "42", "RS": "43", "MS": "50", "MT": "51", "GO": "52", "DF": "53",
}  # fmt: skip
CODIGO_UF = {v: k for k, v in UF_CODIGO.items()}


def so_digitos(valor):
	return re.sub(r"\D", "", valor or "")


def limpar_documento(valor):
	"""CNPJ/CPF sem pontuação; mantém letras (CNPJ alfanumérico)."""
	return re.sub(r"[^0-9A-Za-z]", "", valor or "").upper()


# ===================================================================== CNPJ / CPF
def _dv_cnpj(base):
	pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][-len(base) :]
	soma = sum((ord(c) - 48) * p for c, p in zip(base, pesos))
	resto = soma % 11
	return "0" if resto < 2 else str(11 - resto)


def cnpj_valido(valor):
	c = limpar_documento(valor)
	if not re.fullmatch(r"[0-9A-Z]{12}\d{2}", c) or len(set(c)) == 1:
		return False
	return _dv_cnpj(c[:12]) == c[12] and _dv_cnpj(c[:13]) == c[13]


def completar_cnpj(base12):
	"""Base de 12 posições -> CNPJ com os dois dígitos verificadores (usado nas demonstrações)."""
	b = limpar_documento(base12)[:12]
	b += _dv_cnpj(b)
	return b + _dv_cnpj(b)


def cpf_valido(valor):
	c = so_digitos(valor)
	if len(c) != 11 or len(set(c)) == 1:
		return False
	for n in (9, 10):
		soma = sum(int(c[i]) * (n + 1 - i) for i in range(n))
		if (soma * 10 % 11) % 10 != int(c[n]):
			return False
	return True


def documento_valido(valor):
	c = limpar_documento(valor)
	return cpf_valido(c) if len(c) == 11 else cnpj_valido(c)


def formatar_documento(valor):
	c = limpar_documento(valor)
	if len(c) == 14:
		return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"
	if len(c) == 11:
		return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"
	return valor or ""


def formatar_cep(valor):
	c = so_digitos(valor)
	return f"{c[:5]}-{c[5:]}" if len(c) == 8 else (valor or "")


# ===================================================================== módulo 11 / 10
def mod11(numero, base=9):
	"""DV módulo 11 com pesos 2..base da direita para a esquerda (retorna o resto e a soma)."""
	soma, peso = 0, 2
	for d in reversed(numero):
		soma += int(d) * peso
		peso = 2 if peso == base else peso + 1
	return soma % 11


def dv_chave(numero):
	resto = mod11(numero)
	dv = 11 - resto
	return "0" if dv >= 10 else str(dv)


def mod10(numero):
	soma, peso = 0, 2
	for d in reversed(numero):
		p = int(d) * peso
		soma += p // 10 + p % 10
		peso = 1 if peso == 2 else 2
	return str((10 - soma % 10) % 10)


# ===================================================================== chave de acesso
def chave_nfe(uf, emissao, cnpj, serie, numero, codigo_numerico, modelo="55", tipo_emissao="1"):
	"""44 dígitos: cUF AAMM CNPJ mod série nNF tpEmis cNF DV."""
	base = (
		UF_CODIGO[uf.upper()] + emissao.strftime("%y%m") + limpar_documento(cnpj).rjust(14, "0") + modelo
		+ str(serie).rjust(3, "0") + str(numero).rjust(9, "0") + tipo_emissao + str(codigo_numerico).rjust(8, "0")
	)  # fmt: skip
	return base + dv_chave(_numerico(base))


def chave_nfse(codigo_municipio, cnpj, numero, emissao, codigo_numerico, ambiente="2"):
	"""50 dígitos (NFS-e Nacional): cMun ambGer tpInsc inscFed nNFSe AAMM cNum DV."""
	doc = limpar_documento(cnpj)
	base = (
		str(codigo_municipio).rjust(7, "0") + ambiente + ("2" if len(doc) == 14 else "1") + doc.rjust(14, "0")
		+ str(numero).rjust(13, "0") + emissao.strftime("%y%m") + str(codigo_numerico).rjust(9, "0")
	)  # fmt: skip
	return base + dv_chave(_numerico(base))


def _numerico(texto):
	"""Letras do CNPJ alfanumérico entram pelo valor ASCII - 48 (regra da Receita); aqui só dígitos são esperados."""
	return "".join(c if c.isdigit() else str((ord(c) - 48) % 10) for c in texto)


def decodificar_chave_nfe(chave):
	"""Lê uma chave de NF-e de 44 dígitos. Devolve dict com as partes e `valida`."""
	c = so_digitos(chave)
	if len(c) != 44:
		return {"valida": False, "motivo": f"A chave tem {len(c)} dígitos; precisa ter 44."}
	if dv_chave(c[:43]) != c[43]:
		return {"valida": False, "motivo": "O dígito verificador não confere: algum número foi digitado errado."}
	uf = CODIGO_UF.get(c[:2])
	if not uf:
		return {"valida": False, "motivo": "Os dois primeiros dígitos não correspondem a um estado."}
	return {
		"valida": True,
		"chave": c,
		"uf": uf,
		"ano_mes": f"{c[4:6]}/20{c[2:4]}",
		"cnpj_emitente": c[6:20],
		"modelo": c[20:22],
		"serie": str(int(c[22:25])),
		"numero": str(int(c[25:34])),
	}


def formatar_chave(chave):
	c = so_digitos(chave)
	return " ".join(c[i : i + 4] for i in range(0, len(c), 4))


# ===================================================================== boleto (FEBRABAN)
BASE_FATOR_NOVA = date(2025, 2, 22)  # fator 1000 após o fator 9999 (21/02/2025)


def fator_vencimento(vencimento):
	if vencimento >= BASE_FATOR_NOVA:
		return str(1000 + (vencimento - BASE_FATOR_NOVA).days).rjust(4, "0")
	return str((vencimento - date(1997, 10, 7)).days).rjust(4, "0")


def codigo_barras_boleto(banco, vencimento, valor, campo_livre):
	"""44 dígitos: banco(3) moeda(1) DV(1) fator(4) valor(10) campo livre(25)."""
	banco = str(banco).rjust(3, "0")[:3]
	campo_livre = str(campo_livre).rjust(25, "0")[:25]
	centavos = str(round(valor * 100)).rjust(10, "0")
	sem_dv = banco + "9" + fator_vencimento(vencimento) + centavos + campo_livre
	resto = mod11(sem_dv)
	dv = 11 - resto
	dv = "1" if dv in (0, 10, 11) else str(dv)
	return sem_dv[:4] + dv + sem_dv[4:]


def linha_digitavel(codigo_barras):
	c = codigo_barras
	campo1 = c[0:4] + c[19:24]
	campo2 = c[24:34]
	campo3 = c[34:44]
	campo1 += mod10(campo1)
	campo2 += mod10(campo2)
	campo3 += mod10(campo3)
	return f"{campo1[:5]}.{campo1[5:]} {campo2[:5]}.{campo2[5:]} {campo3[:5]}.{campo3[5:]} {c[4]} {c[5:19]}"


def campo_livre_simulado(agencia, carteira, nosso_numero, conta):
	return (so_digitos(agencia).rjust(4, "0")[:4] + so_digitos(carteira).rjust(2, "0")[:2] + str(nosso_numero).rjust(11, "0")
	        + so_digitos(conta).rjust(7, "0")[:7] + "0")  # fmt: skip


_I25 = {"0": "00110", "1": "10001", "2": "01001", "3": "11000", "4": "00101", "5": "10100", "6": "01100", "7": "00011", "8": "10010", "9": "01010"}


def svg_codigo_barras(codigo, altura=50, fino=1):
	"""Desenho do código de barras do boleto (Interleaved 2 of 5) em SVG."""
	grosso = fino * 3
	barras = [(True, fino), (False, fino), (True, fino), (False, fino)]  # início
	for i in range(0, len(codigo), 2):
		a, b = _I25[codigo[i]], _I25[codigo[i + 1]]
		for x, y in zip(a, b):
			barras.append((True, grosso if x == "1" else fino))
			barras.append((False, grosso if y == "1" else fino))
	barras += [(True, grosso), (False, fino), (True, fino)]  # fim
	pos, rects = 0, []
	for preta, largura in barras:
		if preta:
			rects.append(f'<rect x="{pos}" y="0" width="{largura}" height="{altura}"/>')
		pos += largura
	return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {pos} {altura}" width="{pos * 1.6}" height="{altura}" preserveAspectRatio="none" fill="#000">{"".join(rects)}</svg>'


# ===================================================================== Pix (BR Code)
def _emv(identificador, valor):
	return f"{identificador}{len(valor):02d}{valor}"


def crc16(payload):
	crc = 0xFFFF
	for byte in payload.encode("utf-8"):
		crc ^= byte << 8
		for _ in range(8):
			crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
			crc &= 0xFFFF
	return f"{crc:04X}"


def _ascii(texto, tamanho):
	import unicodedata

	t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
	return re.sub(r"[^A-Za-z0-9 ]", "", t).upper().strip()[:tamanho] or "NA"


def pix_copia_cola(chave, valor, nome, cidade, txid):
	conta = _emv("00", "br.gov.bcb.pix") + _emv("01", chave)
	payload = (
		_emv("00", "01") + _emv("01", "12") + _emv("26", conta) + _emv("52", "0000") + _emv("53", "986")
		+ _emv("54", f"{valor:.2f}") + _emv("58", "BR") + _emv("59", _ascii(nome, 25)) + _emv("60", _ascii(cidade, 15))
		+ _emv("62", _emv("05", re.sub(r"[^A-Za-z0-9]", "", txid)[:25] or "***")) + "6304"
	)  # fmt: skip
	return payload + crc16(payload)


def svg_qrcode(texto, escala=3):
	"""QR Code em SVG (pyqrcode já vem com o Frappe)."""
	import pyqrcode

	buf = io.BytesIO()
	pyqrcode.create(texto, error="M").svg(buf, scale=escala, xmldecl=False, svgns=True, omithw=False)
	return buf.getvalue().decode()


def moeda(valor):
	return "R$ " + f"{valor or 0:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
