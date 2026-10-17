"""ESQUELETO de adapter para os DocTypes da empresa (não está em uso).

Mostra como ligar o portal a "Equipamentos", "Ordem Servico Interna" e
"Ordem Servico Externa" sem alterar as telas. Ajuste os nomes de campo marcados
com TODO para os reais e aponte "Configuracao Portal Metrologia" > Adapter para
"solucoes.portal.adapters.exemplo_empresa.AdapterEmpresa".

Dica: herdar de AdapterPadrao permite trocar só uma parte (ex.: equipamentos e
ordens) e continuar usando o Certificado Calibracao deste app.
"""

import frappe

from solucoes.metrologia.utils import calcular_situacao
from solucoes.portal.adapters.padrao import AdapterPadrao

EQP = "Equipamentos"
OS_INTERNA = "Ordem Servico Interna"
OS_EXTERNA = "Ordem Servico Externa"

# Etapas exibidas na linha do tempo do portal para as OS da empresa  # TODO
ETAPAS = ["Aberta", "Em Andamento", "Aguardando Aprovação", "Concluída", "Entregue"]


class AdapterEmpresa(AdapterPadrao):
	DOCTYPE_EQUIPAMENTO = EQP  # verificações intermediárias apontam para o DocType da empresa

	def listar_equipamentos(self, clientes, filtros=None):
		linhas = frappe.get_all(
			EQP,
			filters={"cliente": ["in", clientes]},  # TODO: nome do campo Link -> Customer
			fields=["*"],
			limit_page_length=0,
		)
		return [
			{
				"id": d.name,
				"cliente": d.cliente,  # TODO
				"tag": d.get("tag") or d.name,  # TODO
				"descricao": d.get("descricao"),  # TODO
				"numero_serie": d.get("numero_serie"),  # TODO
				# Controle por distritos: aponte para o campo de distrito/localização do seu DocType
				# e filtre com escopo.pode_ver(cliente, distrito) — ver AdapterPadrao._eqp_permitidos
				"distrito": d.get("distrito"),  # TODO
				"status": d.get("status") or "Ativo",
				"calibrado_por": "Nosso Laboratório",
				"proxima_calibracao": str(d.get("proxima_calibracao") or "") or None,  # TODO
				"situacao": calcular_situacao(d.get("proxima_calibracao")),
				"origem_cadastro": "Laboratório",
				"editavel": False,
			}
			for d in linhas
		]

	def listar_ordens(self, clientes, filtros=None):
		ordens = []
		for doctype, tipo in ((OS_INTERNA, "Interna"), (OS_EXTERNA, "Externa")):
			for d in frappe.get_all(doctype, filters={"cliente": ["in", clientes]}, fields=["*"]):  # TODO
				etapa = ETAPAS.index(d.status) if d.status in ETAPAS else 0
				ordens.append(
					{
						"id": d.name,
						"cliente": d.cliente,
						"tipo": tipo,
						"status": d.status,
						"etapas": ETAPAS,
						"etapa_atual": etapa,
						"finalizada": d.status in ("Concluída", "Entregue"),  # TODO
						"data_solicitacao": str(d.creation.date()),
						"data_prevista": None,  # TODO
						"data_conclusao": None,
						"atrasada": False,
						"qtd_itens": 1,
					}
				)
		return sorted(ordens, key=lambda o: o["data_solicitacao"], reverse=True)

	# obter_ordem, solicitar_servico, obter_equipamento... seguem o mesmo padrão.
