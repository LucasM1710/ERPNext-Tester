"""Contrato entre o portal e a fonte de dados.

O portal (API + telas) só conhece os dicionários descritos abaixo. Para usar outros
DocTypes (ex.: "Equipamentos", "Ordem Servico Interna", "Ordem Servico Externa"),
crie uma subclasse de PortalAdapter que leia esses DocTypes e devolva os mesmos
formatos, e aponte para ela em "Configuracao Portal Metrologia" > Adapter.

Regra de segurança: TODO método recebe `clientes` — um `Escopo` (ver portal/sessao.py),
que é a lista de Customer visíveis + perfil e distritos permitidos por cliente — e DEVE
filtrar por ele: `escopo.pode_ver(cliente, distrito)` para leitura e
`escopo.pode_editar(cliente, distrito)` para escrita. Nos métodos de criação o escopo
tem exatamente um cliente (`escopo[0]`).
"""

from typing import TypedDict

import frappe
from frappe import _
from frappe.utils import add_days, getdate, today

from solucoes.portal.sessao import Escopo


def como_escopo(clientes) -> Escopo:
	"""Aceita Escopo ou lista simples (lista = sem restrição de distrito, perfil gestor)."""
	return clientes if isinstance(clientes, Escopo) else Escopo(list(clientes))


class Equipamento(TypedDict, total=False):
	id: str
	cliente: str
	tag: str
	descricao: str
	grandeza: str | None
	fabricante: str | None
	modelo: str | None
	numero_serie: str | None
	faixa_medicao: str | None
	resolucao: str | None
	unidade: str | None
	distrito: str | None  # id do Distrito Cliente (controle por distritos)
	distrito_nome: str | None
	localizacao: str | None
	responsavel: str | None
	status: str  # Ativo, Em Calibração, Em Manutenção, Reserva, Inativo, Sucateado
	calibrado_por: str  # "Nosso Laboratório" | "Terceiro"
	fornecedor_externo: str | None
	periodicidade_meses: int | None
	tolerancia: float | None
	ultima_calibracao: str | None  # ISO date
	proxima_calibracao: str | None
	situacao: str  # Em Dia, A Vencer, Vencido, Sem Calibração
	origem_cadastro: str  # "Laboratório" | "Cliente"
	imagem: str | None
	editavel: bool  # cliente pode editar (ex.: cadastrado por ele)
	# verificação intermediária (opcional)
	verificacao_intervalo_dias: int | None
	tolerancia_verificacao: float | None
	ultima_verificacao: str | None
	proxima_verificacao: str | None
	resultado_ultima_verificacao: str | None  # Conforme | Não Conforme


class PontoMedicao(TypedDict, total=False):
	valor_nominal: float
	valor_encontrado: float | None
	valor_medido: float
	erro: float
	incerteza: float | None
	tolerancia: float | None
	conforme: bool


class Certificado(TypedDict, total=False):
	id: str
	numero: str
	equipamento_id: str
	tag: str
	descricao_equipamento: str
	cliente: str
	data_calibracao: str
	data_validade: str | None
	resultado: str  # Aprovado, Reprovado, Sem Critério
	origem: str  # Interno | Externo
	laboratorio: str
	acreditado: bool
	status_analise: str  # Pendente, Aprovado, Reprovado
	analisado_por: str | None
	data_analise: str | None
	tem_arquivo: bool
	pontos: list[PontoMedicao]  # só no detalhe


class EventoOrdem(TypedDict):
	status: str
	data: str
	usuario: str | None


class ItemOrdem(TypedDict, total=False):
	equipamento_id: str
	tag: str
	descricao: str
	servico: str
	status: str
	certificado_id: str | None
	laudo: str | None


class Ordem(TypedDict, total=False):
	id: str
	cliente: str
	tipo: str  # ex.: "Calibração", "Manutenção" (ou "Interna"/"Externa" num adapter da empresa)
	local_atendimento: str | None
	status: str
	etapas: list[str]  # sequência exibida na linha do tempo
	etapa_atual: int  # índice em `etapas` (-1 = cancelada)
	finalizada: bool  # concluída, entregue ou cancelada (não conta como "em aberto")
	data_solicitacao: str
	data_prevista: str | None
	data_conclusao: str | None
	atrasada: bool
	qtd_itens: int
	orcamento: str | None
	status_orcamento: str | None
	itens: list[ItemOrdem]  # só no detalhe
	historico: list[EventoOrdem]  # só no detalhe


class PortalAdapter:
	"""Implementações devem sobrescrever os métodos marcados com NotImplementedError."""

	# DocType dos equipamentos desta fonte de dados (usado no Dynamic Link das verificações)
	DOCTYPE_EQUIPAMENTO = "Equipamento Cliente"

	# ------------------------------------------------------------- verificação intermediária
	# Implementação genérica: grava no DocType "Verificacao Intermediaria" deste app via Dynamic
	# Link, então funciona com qualquer DocType de equipamento sem código extra no adapter.
	def listar_verificacoes(self, clientes, equipamento_id: str, limite: int = 20) -> list[dict]:
		if not self.obter_equipamento(clientes, equipamento_id):
			return []
		linhas = frappe.get_all(
			"Verificacao Intermediaria",
			filters={"equipamento_doctype": self.DOCTYPE_EQUIPAMENTO, "equipamento": equipamento_id},
			fields=["name", "data", "resultado", "realizado_por", "referencia_utilizada", "observacao", "tolerancia"],
			order_by="data desc",
			limit=limite,
		)
		pontos = {}
		for p in frappe.get_all(
			"Verificacao Intermediaria Ponto",
			filters={"parent": ["in", [l.name for l in linhas] or [""]], "parenttype": "Verificacao Intermediaria"},
			fields=["parent", "valor_referencia", "valor_lido", "desvio", "conforme"],
			order_by="idx",
		):
			pontos.setdefault(p.pop("parent"), []).append({**p, "conforme": bool(p.conforme)})
		return [
			{
				"id": l.name,
				"data": str(l.data),
				"resultado": l.resultado,
				"realizado_por": frappe.db.get_value("User", l.realizado_por, "full_name") or l.realizado_por,
				"referencia": l.referencia_utilizada,
				"observacao": l.observacao,
				"tolerancia": l.tolerancia,
				"pontos": pontos.get(l.name, []),
			}
			for l in linhas
		]

	def registrar_verificacao(self, clientes, equipamento_id: str, dados: dict) -> dict:
		escopo = como_escopo(clientes)
		eqp = self.obter_equipamento(escopo, equipamento_id)
		if not eqp:
			frappe.throw(_("Equipamento não encontrado."), frappe.DoesNotExistError)
		if not escopo.pode_editar(eqp["cliente"], eqp.get("distrito")):
			raise frappe.PermissionError(_("Seu perfil não permite registrar verificações."))
		leituras = [p for p in dados.get("pontos") or [] if p.get("valor_referencia") not in (None, "") and p.get("valor_lido") not in (None, "")]
		if not leituras:
			frappe.throw(_("Informe ao menos uma leitura (referência e valor lido)."))
		doc = frappe.get_doc(
			{
				"doctype": "Verificacao Intermediaria",
				"equipamento_doctype": self.DOCTYPE_EQUIPAMENTO,
				"equipamento": equipamento_id,
				"tag": eqp.get("tag"),
				"cliente": eqp["cliente"],
				"distrito": eqp.get("distrito") if frappe.db.exists("Distrito Cliente", eqp.get("distrito") or "") else None,
				"tolerancia": eqp.get("tolerancia_verificacao") or eqp.get("tolerancia"),
				"referencia_utilizada": dados.get("referencia"),
				"observacao": dados.get("observacao"),
				"pontos": [{"valor_referencia": p["valor_referencia"], "valor_lido": p["valor_lido"]} for p in leituras],
			}
		).insert(ignore_permissions=True)
		return self.listar_verificacoes(escopo, equipamento_id, limite=1)[0] | {"id": doc.name}

	# ------------------------------------------------------------- equipamentos
	def listar_equipamentos(self, clientes: list[str], filtros: dict | None = None) -> list[Equipamento]:
		raise NotImplementedError

	def obter_equipamento(self, clientes: list[str], id: str) -> Equipamento | None:
		raise NotImplementedError

	def criar_equipamento(self, clientes: Escopo, dados: dict) -> Equipamento:
		raise NotImplementedError

	def atualizar_equipamento(self, clientes: list[str], id: str, dados: dict) -> Equipamento:
		raise NotImplementedError

	# ------------------------------------------------------------- certificados
	def listar_certificados(self, clientes: list[str], filtros: dict | None = None) -> list[Certificado]:
		raise NotImplementedError

	def obter_certificado(self, clientes: list[str], id: str) -> Certificado | None:
		raise NotImplementedError

	def obter_arquivo_certificado(self, clientes: list[str], id: str) -> str | None:
		"""Retorna o file_url do PDF (a API faz o download com checagem de acesso)."""
		raise NotImplementedError

	def registrar_analise_critica(
		self, clientes: list[str], id: str, status: str, observacao: str | None, usuario: str
	) -> Certificado:
		raise NotImplementedError

	def criar_certificado_externo(self, clientes: Escopo, dados: dict, file_url: str | None) -> Certificado:
		raise NotImplementedError

	# ------------------------------------------------------------- ordens de serviço
	def listar_ordens(self, clientes: list[str], filtros: dict | None = None) -> list[Ordem]:
		"""Filtros: status, equipamento (id de equipamento contido na OS)."""
		raise NotImplementedError

	def obter_ordem(self, clientes: list[str], id: str) -> Ordem | None:
		raise NotImplementedError

	def solicitar_servico(self, clientes: Escopo, contato: str | None, dados: dict) -> Ordem:
		raise NotImplementedError

	def responder_orcamento(self, clientes: list[str], id: str, aprovado: bool) -> Ordem:
		raise NotImplementedError

	# ------------------------------------------------------------- dashboard
	def resumo_dashboard(self, clientes: list[str]) -> dict:
		"""Implementação genérica a partir dos métodos acima. Sobrescreva se precisar de performance."""
		equipamentos = [
			e for e in self.listar_equipamentos(clientes) if e.get("status") not in ("Inativo", "Sucateado")
		]
		certificados = self.listar_certificados(clientes)
		ordens = self.listar_ordens(clientes)

		situacoes = {"Em Dia": 0, "A Vencer": 0, "Vencido": 0, "Sem Calibração": 0}
		for e in equipamentos:
			chave = e.get("situacao") or "Sem Calibração"
			situacoes[chave] = situacoes.get(chave, 0) + 1

		total = len(equipamentos)
		calibraveis = total - situacoes["Sem Calibração"]
		em_dia_pct = round(100 * (situacoes["Em Dia"] + situacoes["A Vencer"]) / calibraveis, 1) if calibraveis else 0

		return {
			"kpis": {
				"total_equipamentos": total,
				"em_dia_pct": em_dia_pct,
				"vencidos": situacoes["Vencido"],
				"a_vencer": situacoes["A Vencer"],
				"ordens_abertas": sum(1 for o in ordens if not o.get("finalizada")),
				"analises_pendentes": sum(1 for c in certificados if c.get("status_analise") == "Pendente"),
				"orcamentos_pendentes": sum(1 for o in ordens if o.get("status_orcamento") == "Aguardando Cliente"),
				"verificacoes_atrasadas": sum(
					1 for e in equipamentos if e.get("proxima_verificacao") and str(e["proxima_verificacao"]) < str(today())
				),
				"verificacoes_nao_conformes": sum(
					1 for e in equipamentos if e.get("resultado_ultima_verificacao") == "Não Conforme"
				),
			},
			"situacoes": situacoes,
			"vencimentos_por_mes": self._vencimentos_por_mes(equipamentos),
			"por_grandeza": self._contar(equipamentos, "grandeza", "Não informada"),
			"por_calibrado_por": self._contar(equipamentos, "calibrado_por", "Não informado"),
			"por_distrito": self.resumo_por_distrito(equipamentos),
			"resultados_12m": self._resultados_por_mes(certificados),
			"proximos_vencimentos": sorted(
				[e for e in equipamentos if e.get("situacao") in ("Vencido", "A Vencer")],
				key=lambda e: e.get("proxima_calibracao") or "",
			)[:8],
			"ordens_recentes": ordens[:5],
		}

	@staticmethod
	def resumo_por_distrito(equipamentos) -> list[dict]:
		"""Ranking de distritos (pior % em dia primeiro). Vazio se ninguém usa distritos."""
		grupos = {}
		for e in equipamentos:
			if not e.get("distrito"):
				continue
			g = grupos.setdefault(
				e["distrito"],
				{"distrito": e["distrito"], "nome": e.get("distrito_nome") or e["distrito"], "cliente": e.get("cliente"),
				 "total": 0, "Em Dia": 0, "A Vencer": 0, "Vencido": 0, "Sem Calibração": 0},
			)  # fmt: skip
			g["total"] += 1
			g[e.get("situacao") or "Sem Calibração"] += 1
		for g in grupos.values():
			calibraveis = g["total"] - g["Sem Calibração"]
			g["em_dia_pct"] = round(100 * (g["Em Dia"] + g["A Vencer"]) / calibraveis, 1) if calibraveis else 0
		return sorted(grupos.values(), key=lambda g: (g["em_dia_pct"], -g["Vencido"]))

	# ------------------------------------------------------------- helpers
	@staticmethod
	def _contar(itens, campo, vazio):
		contagem = {}
		for i in itens:
			chave = i.get(campo) or vazio
			contagem[chave] = contagem.get(chave, 0) + 1
		return dict(sorted(contagem.items(), key=lambda kv: -kv[1]))

	@staticmethod
	def _meses(inicio, quantidade):
		ano, mes = inicio.year, inicio.month
		for _ in range(quantidade):
			yield f"{ano:04d}-{mes:02d}"
			mes += 1
			if mes > 12:
				ano, mes = ano + 1, 1

	def _vencimentos_por_mes(self, equipamentos, meses=12):
		hoje = getdate(today())
		chaves = list(self._meses(hoje, meses))
		dados = dict.fromkeys(chaves, 0)
		vencidos = 0
		for e in equipamentos:
			prox = e.get("proxima_calibracao")
			if not prox:
				continue
			if getdate(prox) < hoje:
				vencidos += 1
				continue
			chave = str(prox)[:7]
			if chave in dados:
				dados[chave] += 1
		return {"meses": chaves, "quantidades": list(dados.values()), "ja_vencidos": vencidos}

	def _resultados_por_mes(self, certificados, meses=12):
		inicio = getdate(add_days(today(), -30 * (meses - 1)))
		chaves = list(self._meses(inicio, meses))
		aprovados = dict.fromkeys(chaves, 0)
		reprovados = dict.fromkeys(chaves, 0)
		for c in certificados:
			chave = str(c.get("data_calibracao") or "")[:7]
			if chave not in aprovados:
				continue
			if c.get("resultado") == "Reprovado":
				reprovados[chave] += 1
			else:
				aprovados[chave] += 1
		return {"meses": chaves, "aprovados": list(aprovados.values()), "reprovados": list(reprovados.values())}
