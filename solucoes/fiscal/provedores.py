"""Adaptadores de emissão: quem transmite as notas e registra os boletos.

Hoje só o Simulador funciona (nada sai daqui). Para ligar um provedor real, crie uma classe com os
mesmos métodos e registre em PROVEDORES_NOTAS / PROVEDORES_BOLETO:

	Notas:   emitir(nota) -> dict;   cancelar(nota, motivo) -> dict
	Boletos: registrar(boleto) -> dict;   cancelar(boleto) -> dict

O resto do sistema (telas, conferência, boleto, baixa no ERP) não muda.
"""

import random
from datetime import timedelta

import frappe
from frappe.utils import cint, get_datetime, getdate, now_datetime

from solucoes.fiscal import util
from solucoes.fiscal.regras import CONFIG, config

PROVEDORES_NOTAS = {}
PROVEDORES_BOLETO = {}


def provedor_notas():
	cfg = config()
	nome = "Simulador" if cfg.ambiente == "Simulação" else cfg.provedor_notas
	if nome not in PROVEDORES_NOTAS:
		frappe.throw(f"A emissão por {nome} ainda não está ligada. Volte o ambiente para Simulação ou peça a integração.")
	return PROVEDORES_NOTAS[nome]()


def provedor_boleto():
	cfg = config()
	nome = "Simulador" if cfg.ambiente == "Simulação" else cfg.provedor_boleto
	if nome not in PROVEDORES_BOLETO:
		frappe.throw(f"O registro de boletos por {nome} ainda não está ligado. Volte o ambiente para Simulação ou peça a integração.")
	return PROVEDORES_BOLETO[nome]()


def proximo_numero(campo):
	"""Numeração sem buracos nem repetição (trava a linha da configuração até o commit)."""
	linha = frappe.db.sql("select value from tabSingles where doctype=%s and field=%s for update", (CONFIG, campo))
	numero = max(cint(linha[0][0]) if linha else 1, 1)
	frappe.db.set_single_value(CONFIG, campo, numero + 1)
	return numero


def rejeicao(codigo, mensagem, orientacao):
	return {"status": "Rejeitada", "codigo": codigo, "mensagem": mensagem, "orientacao": orientacao}


# Rejeições que acontecem na vida real mesmo com o cadastro certo (para treinar a equipe)
REJEICOES_ALEATORIAS = [
	("108", "Serviço paralisado momentaneamente (simulação).", "O sistema da SEFAZ/prefeitura está fora do ar. Espere alguns minutos e clique em Tentar de novo."),
	("999", "Erro não catalogado: tempo de resposta esgotado (simulação).", "Instabilidade na comunicação. Tente de novo; se repetir, avise a TI."),
	("539", "Duplicidade de NF-e com diferença na chave de acesso (simulação).", "Já existe uma nota com esse número. Clique em Tentar de novo: o sistema usa o próximo número."),
]


class Simulador:
	"""Faz o papel da SEFAZ (NF-e) e da NFS-e Nacional: valida, numera, autoriza ou rejeita."""

	def emitir(self, nota):
		cfg = config()
		d = frappe._dict(frappe.parse_json(nota.destinatario_json or "{}"))
		# validações que a SEFAZ/prefeitura fazem (a conferência já barra quase tudo antes)
		if not util.cnpj_valido(cfg.cnpj):
			return rejeicao("213", "CNPJ do emitente inválido (simulação).", "Corrija o CNPJ da nossa empresa na configuração fiscal.")
		if not util.documento_valido(d.cnpj_cpf):
			return rejeicao("207", "CNPJ/CPF do destinatário inválido (simulação).", "Corrija o CNPJ/CPF no cadastro fiscal do cliente.")
		if nota.tipo_documento == "NF-e":
			if d.contribuinte_icms == "Contribuinte" and not d.inscricao_estadual:
				return rejeicao("233", "IE do destinatário não informada (simulação).", "Informe a inscrição estadual do cliente ou marque-o como Não contribuinte.")
			for i in nota.itens:
				if len(util.so_digitos(i.ncm)) != 8:
					return rejeicao("778", f"Informado NCM inexistente no item {i.idx} (simulação).", "Corrija o NCM do item (8 dígitos).")
			if nota.nf_referenciada and not util.decodificar_chave_nfe(nota.nf_referenciada)["valida"]:
				return rejeicao("547", "Dígito verificador da chave de acesso da NF-e referenciada inválido (simulação).", "Confira a chave da nota de origem.")
		if cint(cfg.simulacao_falha_percentual) and random.randint(1, 100) <= cint(cfg.simulacao_falha_percentual):
			return rejeicao(*random.choice(REJEICOES_ALEATORIAS))

		agora = now_datetime()
		cnum = random.randint(10_000_000, 99_999_999)
		if nota.tipo_documento == "NF-e":
			numero = proximo_numero("proximo_numero_nfe")
			serie = str(cfg.serie_nfe or 1)
			chave = util.chave_nfe(cfg.uf, agora, cfg.cnpj, serie, numero, cnum)
			mensagem = "Autorizado o uso da NF-e (simulação)."
		else:
			numero = proximo_numero("proximo_numero_dps")
			serie = cfg.serie_dps or "1"
			chave = util.chave_nfse(cfg.codigo_municipio, cfg.cnpj, numero, agora, random.randint(100_000_000, 999_999_999))
			mensagem = "NFS-e gerada com sucesso (simulação)."
		protocolo = util.UF_CODIGO.get((cfg.uf or "SP").upper(), "35") + agora.strftime("%y") + str(random.randint(10**10, 10**11 - 1))
		return {"status": "Autorizada", "numero": str(numero), "serie": serie, "chave": chave, "protocolo": protocolo, "codigo": "100", "mensagem": mensagem, "data": agora}

	def cancelar(self, nota, motivo):
		if len((motivo or "").strip()) < 15:
			return {"ok": False, "mensagem": "A justificativa precisa ter pelo menos 15 caracteres (regra da SEFAZ)."}
		if nota.tipo_documento == "NF-e" and now_datetime() - get_datetime(nota.data_emissao) > timedelta(hours=24):
			return {"ok": False, "mensagem": "Rejeição 501: passou o prazo de 24 horas para cancelar a NF-e (simulação). "
			        "Converse com o contador: o caminho agora é uma nota de devolução ou de estorno."}  # fmt: skip
		return {"ok": True, "protocolo": str(random.randint(10**14, 10**15 - 1)), "mensagem": "Cancelamento homologado (simulação)."}


class SimuladorBoleto:
	"""Faz o papel do banco: registra o boleto com código de barras, linha digitável e Pix."""

	def registrar(self, bol):
		cfg = config()
		nosso = proximo_numero("proximo_nosso_numero")
		campo_livre = util.campo_livre_simulado(cfg.agencia, cfg.carteira, nosso, cfg.conta)
		codigo = util.codigo_barras_boleto(cfg.banco_codigo or "000", getdate(bol.vencimento), bol.valor, campo_livre)
		chave_pix = cfg.chave_pix or util.limpar_documento(cfg.cnpj) or "pix@exemplo.com.br"
		return {
			"nosso_numero": str(nosso).rjust(11, "0"),
			"codigo_barras": codigo,
			"linha_digitavel": util.linha_digitavel(codigo),
			"pix": util.pix_copia_cola(chave_pix, bol.valor, cfg.razao_social or "Beneficiario", cfg.municipio or "Cidade", bol.name),
		}

	def cancelar(self, bol):
		return {"ok": True, "mensagem": "Baixa do boleto registrada no banco (simulação)."}


PROVEDORES_NOTAS["Simulador"] = Simulador
PROVEDORES_BOLETO["Simulador"] = SimuladorBoleto
