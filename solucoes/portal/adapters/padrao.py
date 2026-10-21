"""Adapter padrão: lê os DocTypes do módulo Metrologia deste app."""

import frappe
from frappe import _
from frappe.utils import getdate, today

from solucoes.portal.adapters.base import Certificado, Equipamento, Ordem, PortalAdapter, como_escopo
from solucoes.portal.sessao import CONSULTA, usa_distritos

EQP = "Equipamento Cliente"
CERT = "Certificado Calibracao"
OS = "Ordem Servico Metrologia"
OS_ITEM = "Ordem Servico Metrologia Item"

ETAPAS_OS = ["Solicitada", "Recebida", "Em Análise", "Aguardando Aprovação", "Em Execução", "Concluída", "Enviada"]

CAMPOS_EDITAVEIS_EQP = (
	"tag", "descricao", "grandeza", "fabricante", "modelo", "numero_serie", "faixa_medicao",
	"resolucao", "unidade", "distrito", "localizacao", "responsavel", "status", "calibrado_por",
	"fornecedor_externo", "periodicidade_meses", "tolerancia", "proxima_calibracao", "observacoes",
	"verificacao_intervalo_dias", "tolerancia_verificacao",
)  # fmt: skip
# Equipamento cadastrado pelo laboratório: o cliente organiza (onde está, quem usa, transferência) e
# decide os intervalos (periodicidade de calibração e de verificação intermediária são dele)
CAMPOS_EDITAVEIS_EQP_LAB = (
	"distrito", "localizacao", "responsavel", "status",
	"periodicidade_meses", "verificacao_intervalo_dias", "tolerancia_verificacao",
)  # fmt: skip


def _str(valor):
	return str(valor) if valor else None


def _nao_encontrado(doc, mensagem):
	if not doc:
		frappe.throw(mensagem, frappe.DoesNotExistError)
	return doc


class AdapterPadrao(PortalAdapter):
	# ================================================================ escopo
	def _eqp_permitidos(self, escopo) -> list[str] | None:
		"""None = sem restrição de distrito; senão, os ids de equipamento visíveis."""
		if not escopo.restrito:
			return None
		proprios = [c for c in escopo if escopo.so_proprios(c)]
		if proprios:
			# perfil Usuário: só os equipamentos dos quais é dono
			return frappe.get_all(EQP, filters={"cliente": ["in", proprios], "dono": escopo.usuario}, pluck="name")
		livres = [c for c in escopo if escopo.distritos_de(c) is None]
		distritos = set().union(*(escopo.distritos_de(c) or set() for c in escopo))
		ids = frappe.get_all(EQP, filters={"cliente": ["in", livres]}, pluck="name") if livres else []
		if distritos:
			ids += frappe.get_all(EQP, filters={"cliente": ["in", list(escopo)], "distrito": ["in", list(distritos)]}, pluck="name")
		return ids

	def _nomes_distritos(self, escopo) -> dict[str, str]:
		return dict(
			frappe.get_all("Distrito Cliente", filters={"cliente": ["in", list(escopo) or [""]]}, fields=["name", "nome_distrito"], as_list=True)
		)

	def _exigir_edicao(self, escopo, cliente, distrito=None):
		if not escopo.pode_editar(cliente, distrito):
			raise frappe.PermissionError(_("Seu perfil não permite alterar este registro."))

	# ================================================================ equipamentos
	def _equipamento(self, d, distritos=None) -> Equipamento:
		return {
			"id": d.name,
			"cliente": d.cliente,
			"tag": d.tag,
			"descricao": d.descricao,
			"grandeza": d.grandeza,
			"fabricante": d.fabricante,
			"modelo": d.modelo,
			"numero_serie": d.numero_serie,
			"faixa_medicao": d.faixa_medicao,
			"resolucao": d.resolucao,
			"unidade": d.unidade,
			"distrito": d.distrito,
			"distrito_nome": (distritos or {}).get(d.distrito) if d.distrito else None,
			"localizacao": d.localizacao,
			"responsavel": d.responsavel,
			"status": d.status,
			"calibrado_por": d.calibrado_por,
			"fornecedor_externo": d.fornecedor_externo,
			"periodicidade_meses": d.periodicidade_meses,
			"tolerancia": d.tolerancia,
			"ultima_calibracao": _str(d.ultima_calibracao),
			"proxima_calibracao": _str(d.proxima_calibracao),
			"situacao": d.situacao_calibracao or "Sem Calibração",
			"origem_cadastro": d.origem_cadastro,
			"imagem": d.imagem,
			"editavel": d.origem_cadastro == "Cliente",
			"verificacao_intervalo_dias": d.verificacao_intervalo_dias,
			"tolerancia_verificacao": d.tolerancia_verificacao,
			"ultima_verificacao": _str(d.ultima_verificacao),
			"proxima_verificacao": _str(d.proxima_verificacao),
			"resultado_ultima_verificacao": d.resultado_ultima_verificacao,
		}

	def listar_equipamentos(self, clientes, filtros=None):
		escopo = como_escopo(clientes)
		filtros = filtros or {}
		f = {"cliente": ["in", list(escopo)]}
		for campo, chave in (("situacao_calibracao", "situacao"), ("status", "status"), ("grandeza", "grandeza"), ("calibrado_por", "calibrado_por"), ("distrito", "distrito")):
			if filtros.get(chave):
				f[campo] = filtros[chave]
		if (permitidos := self._eqp_permitidos(escopo)) is not None:
			f["name"] = ["in", permitidos or [""]]
		or_filters = None
		if busca := filtros.get("busca"):
			like = f"%{busca}%"
			or_filters = {"tag": ["like", like], "descricao": ["like", like], "numero_serie": ["like", like], "localizacao": ["like", like]}

		linhas = frappe.get_all(EQP, filters=f, or_filters=or_filters, fields=["*"], order_by="proxima_calibracao asc, tag asc", limit_page_length=0)
		distritos = self._nomes_distritos(escopo)
		return [self._equipamento(d, distritos) for d in linhas]

	def _get_eqp_doc(self, clientes, id):
		escopo = como_escopo(clientes)
		doc = frappe.get_doc(EQP, id) if frappe.db.exists(EQP, id) else None
		if not doc or not escopo.pode_ver(doc.cliente, doc.distrito, doc.get("dono")):
			return None
		return doc

	def obter_equipamento(self, clientes, id):
		doc = self._get_eqp_doc(clientes, id)
		return self._equipamento(doc, self._nomes_distritos([doc.cliente])) if doc else None

	def criar_equipamento(self, clientes, dados):
		escopo = como_escopo(clientes)
		cliente = escopo[0]
		doc = frappe.new_doc(EQP)
		doc.update({k: v for k, v in dados.items() if k in CAMPOS_EDITAVEIS_EQP})
		doc.cliente = cliente
		self._validar_distrito(escopo, cliente, doc)
		self._exigir_edicao(escopo, cliente, doc.distrito)
		doc.origem_cadastro = "Cliente"
		doc.cadastrado_por_usuario = frappe.session.user
		doc.insert(ignore_permissions=True)
		return self.obter_equipamento(escopo, doc.name)

	def _validar_distrito(self, escopo, cliente, doc):
		"""Cliente com controle por distritos: distrito obrigatório e dentro do que o usuário pode ver."""
		permitidos = escopo.distritos_de(cliente)
		if not usa_distritos(cliente):
			return
		if not doc.distrito and permitidos and len(permitidos) == 1:
			doc.distrito = next(iter(permitidos))
		if not doc.distrito:
			frappe.throw(_("Informe o distrito do equipamento."))
		if permitidos is not None and doc.distrito not in permitidos:
			raise frappe.PermissionError(_("Você não tem acesso a este distrito."))

	def atualizar_equipamento(self, clientes, id, dados):
		escopo = como_escopo(clientes)
		doc = _nao_encontrado(self._get_eqp_doc(escopo, id), _("Equipamento não encontrado."))
		self._exigir_edicao(escopo, doc.cliente, doc.distrito)
		campos = CAMPOS_EDITAVEIS_EQP if doc.origem_cadastro == "Cliente" else CAMPOS_EDITAVEIS_EQP_LAB
		doc.update({k: v for k, v in dados.items() if k in campos})
		self._validar_distrito(escopo, doc.cliente, doc)
		doc.save(ignore_permissions=True)
		return self.obter_equipamento(escopo, id)

	def definir_donos(self, cliente, usuario, equipamentos) -> int:
		equipamentos = set(equipamentos or [])
		for nome in frappe.get_all(EQP, filters={"cliente": cliente, "dono": usuario}, pluck="name"):
			if nome not in equipamentos:
				frappe.db.set_value(EQP, nome, "dono", None)
		for id in equipamentos:
			if frappe.db.get_value(EQP, id, "cliente") != cliente:
				raise frappe.PermissionError
			frappe.db.set_value(EQP, id, "dono", usuario)
		return len(equipamentos)

	def atribuir_distrito(self, cliente, distrito, equipamentos) -> int:
		"""Move equipamentos para um distrito (organização inicial ou transferência). Fica no histórico."""
		movidos = 0
		for id in equipamentos:
			doc = frappe.get_doc(EQP, id)
			if doc.cliente != cliente:
				raise frappe.PermissionError
			if doc.distrito != distrito:
				doc.distrito = distrito
				doc.save(ignore_permissions=True)
				movidos += 1
		return movidos

	# ================================================================ certificados
	def _certificado(self, d) -> Certificado:
		return {
			"id": d.name,
			"numero": d.numero_certificado or d.name,
			"equipamento_id": d.equipamento,
			"tag": d.tag,
			"descricao_equipamento": d.descricao_equipamento,
			"cliente": d.cliente,
			"data_calibracao": _str(d.data_calibracao),
			"data_validade": _str(d.data_validade),
			"resultado": d.resultado or "Sem Critério",
			"origem": d.origem,
			"laboratorio": d.laboratorio_externo if d.origem == "Externo" else frappe.defaults.get_global_default("company"),
			"acreditado": bool(d.acreditado),
			"status_analise": d.status_analise,
			"analisado_por": d.analisado_por,
			"data_analise": _str(d.data_analise),
			"tem_arquivo": bool(d.arquivo),
		}

	def listar_certificados(self, clientes, filtros=None):
		escopo = como_escopo(clientes)
		filtros = filtros or {}
		f = {"cliente": ["in", list(escopo)]}
		for campo in ("equipamento", "resultado", "origem", "status_analise"):
			if filtros.get(campo):
				f[campo] = filtros[campo]
		if filtros.get("de"):
			f["data_calibracao"] = [">=", filtros["de"]]
		if (permitidos := self._eqp_permitidos(escopo)) is not None:
			if filtros.get("equipamento") and filtros["equipamento"] not in permitidos:
				return []
			f.setdefault("equipamento", ["in", permitidos or [""]])
		or_filters = None
		if busca := filtros.get("busca"):
			like = f"%{busca}%"
			or_filters = {"tag": ["like", like], "name": ["like", like], "numero_certificado": ["like", like], "descricao_equipamento": ["like", like]}
		linhas = frappe.get_all(CERT, filters=f, or_filters=or_filters, fields=["*"], order_by="data_calibracao desc, creation desc", limit_page_length=0)
		return [self._certificado(d) for d in linhas]

	def _get_cert_doc(self, clientes, id):
		doc = frappe.get_doc(CERT, id) if frappe.db.exists(CERT, id) else None
		if not doc or not self._get_eqp_doc(clientes, doc.equipamento):
			return None
		return doc

	def obter_certificado(self, clientes, id):
		doc = self._get_cert_doc(clientes, id)
		if not doc:
			return None
		cert = self._certificado(doc)
		tolerancia_eqp, unidade = frappe.db.get_value(EQP, doc.equipamento, ["tolerancia", "unidade"])
		cert["unidade"] = unidade
		cert["pontos"] = [
			{
				"valor_nominal": p.valor_nominal,
				"valor_encontrado": p.valor_encontrado,
				"valor_medido": p.valor_medido,
				"erro": p.erro,
				"incerteza": p.incerteza,
				"tolerancia": p.tolerancia or tolerancia_eqp,
				"conforme": bool(p.conforme),
			}
			for p in doc.pontos
		]
		cert["padroes_utilizados"] = doc.padroes_utilizados
		cert["padroes"] = [
			{
				"codigo": p.padrao,
				"descricao": p.descricao,
				"numero_certificado": p.numero_certificado,
				"laboratorio": p.laboratorio_calibrador,
				"validade": _str(p.data_validade),
				"acreditado": bool(p.acreditado),
			}
			for p in doc.padroes
		]
		cert["tecnico"] = doc.tecnico
		cert["ajustado"] = bool(doc.ajustado)
		cert["observacao_analise"] = doc.observacao_analise
		return cert

	def obter_arquivo_certificado(self, clientes, id):
		doc = self._get_cert_doc(clientes, id)
		return doc.arquivo if doc else None

	def registrar_analise_critica(self, clientes, id, status, observacao, usuario):
		escopo = como_escopo(clientes)
		doc = _nao_encontrado(self._get_cert_doc(escopo, id), _("Certificado não encontrado."))
		self._exigir_edicao(escopo, doc.cliente, frappe.db.get_value(EQP, doc.equipamento, "distrito"))
		doc.status_analise = status
		doc.observacao_analise = observacao
		doc.analisado_por = usuario
		doc.data_analise = frappe.utils.now_datetime()
		doc.save(ignore_permissions=True)
		return self.obter_certificado(escopo, id)

	def criar_certificado_externo(self, clientes, dados, file_url):
		escopo = como_escopo(clientes)
		eqp = _nao_encontrado(self._get_eqp_doc(escopo, dados.get("equipamento_id")), _("Equipamento não encontrado."))
		self._exigir_edicao(escopo, eqp.cliente, eqp.distrito)
		doc = frappe.get_doc(
			{
				"doctype": CERT,
				"equipamento": eqp.name,
				"origem": "Externo",
				"numero_certificado": dados.get("numero"),
				"laboratorio_externo": dados.get("laboratorio"),
				"acreditado": int(bool(dados.get("acreditado"))),
				"data_calibracao": dados.get("data_calibracao"),
				"data_validade": dados.get("data_validade"),
				"arquivo": file_url,
			}
		)
		doc.insert(ignore_permissions=True)
		return self._certificado(doc)

	# ================================================================ ordens de serviço
	def _ordem(self, d, qtd_itens=0) -> Ordem:
		etapa = -1 if d.status == "Cancelada" else ETAPAS_OS.index(d.status)
		finalizada = d.status in ("Concluída", "Enviada", "Cancelada")
		atrasada = bool(d.data_prevista and not finalizada and getdate(d.data_prevista) < getdate(today()))
		return {
			"id": d.name,
			"cliente": d.cliente,
			"tipo": d.tipo_servico,
			"local_atendimento": d.local_atendimento,
			"status": d.status,
			"etapas": ETAPAS_OS,
			"etapa_atual": etapa,
			"data_solicitacao": _str(d.data_solicitacao),
			"data_prevista": _str(d.data_prevista),
			"data_conclusao": _str(d.data_conclusao),
			"finalizada": finalizada,
			"atrasada": atrasada,
			"qtd_itens": qtd_itens,
			"orcamento": d.orcamento,
			"status_orcamento": d.status_orcamento,
		}

	def _os_com_equipamentos(self, equipamentos) -> list[str]:
		return frappe.get_all(OS_ITEM, filters={"equipamento": ["in", equipamentos or [""]], "parenttype": OS}, pluck="parent", distinct=True)

	def listar_ordens(self, clientes, filtros=None):
		escopo = como_escopo(clientes)
		filtros = filtros or {}
		f = {"cliente": ["in", list(escopo)]}
		if filtros.get("status"):
			f["status"] = filtros["status"]
		permitidos = self._eqp_permitidos(escopo)
		if filtros.get("equipamento"):
			if permitidos is not None and filtros["equipamento"] not in permitidos:
				return []
			f["name"] = ["in", self._os_com_equipamentos([filtros["equipamento"]]) or [""]]
		elif permitidos is not None:
			# OS visível ao usuário de distrito se contém ao menos um equipamento dos seus distritos
			f["name"] = ["in", self._os_com_equipamentos(permitidos) or [""]]
		linhas = frappe.get_all(OS, filters=f, fields=["*"], order_by="data_solicitacao desc, creation desc", limit_page_length=0)
		if not linhas:
			return []
		contagem = dict(
			frappe.get_all(
				OS_ITEM,
				filters={"parent": ["in", [l.name for l in linhas]], "parenttype": OS},
				fields=["parent", "count(*) as qtd"],
				group_by="parent",
				as_list=True,
			)
		)
		return [self._ordem(d, contagem.get(d.name, 0)) for d in linhas]

	def _get_os_doc(self, clientes, id):
		escopo = como_escopo(clientes)
		doc = frappe.get_doc(OS, id) if frappe.db.exists(OS, id) else None
		if not doc or doc.cliente not in escopo:
			return None
		if escopo.distritos_de(doc.cliente) is not None and not any(self._get_eqp_doc(escopo, i.equipamento) for i in doc.itens):
			return None
		return doc

	def obter_ordem(self, clientes, id):
		escopo = como_escopo(clientes)
		doc = self._get_os_doc(escopo, id)
		if not doc:
			return None
		ordem = self._ordem(doc, len(doc.itens))
		visiveis = {i.equipamento for i in doc.itens if self._get_eqp_doc(escopo, i.equipamento)}
		descricoes = dict(frappe.get_all(EQP, filters={"name": ["in", list(visiveis) or [""]]}, fields=["name", "descricao"], as_list=True))
		ordem["itens"] = [
			{
				"equipamento_id": i.equipamento,
				"tag": i.tag,
				"descricao": descricoes.get(i.equipamento),
				"servico": i.servico,
				"status": i.status_item,
				"certificado_id": i.certificado,
				"laudo": i.laudo,
			}
			for i in doc.itens
			if i.equipamento in visiveis
		]
		ordem["itens_outros_distritos"] = len(doc.itens) - len(ordem["itens"])
		ordem["historico"] = [{"status": h.status, "data": _str(h.data), "usuario": h.usuario} for h in doc.historico]
		ordem["observacoes_cliente"] = doc.observacoes_cliente
		return ordem

	def solicitar_servico(self, clientes, contato, dados):
		escopo = como_escopo(clientes)
		cliente = escopo[0]
		equipamentos = dados.get("equipamentos") or []
		if not equipamentos:
			frappe.throw(_("Selecione ao menos um equipamento."))
		for id in equipamentos:
			eqp = _nao_encontrado(self._get_eqp_doc(escopo, id), _("Equipamento {0} não encontrado.").format(id))
			self._exigir_edicao(escopo, eqp.cliente, eqp.distrito)
		tipo = dados.get("tipo") or "Calibração"
		doc = frappe.get_doc(
			{
				"doctype": OS,
				"cliente": cliente,
				"contato": contato,
				"tipo_servico": tipo,
				"local_atendimento": dados.get("local_atendimento") or "Laboratório",
				"origem": "Portal",
				"coleta": int(bool(dados.get("coleta"))),
				"endereco_coleta": dados.get("endereco_coleta"),
				"observacoes_cliente": dados.get("observacoes"),
				"itens": [{"equipamento": e, "servico": tipo} for e in equipamentos],
			}
		)
		doc.insert(ignore_permissions=True)
		return self._ordem(doc, len(doc.itens))

	def responder_orcamento(self, clientes, id, aprovado):
		escopo = como_escopo(clientes)
		doc = _nao_encontrado(self._get_os_doc(escopo, id), _("Ordem de serviço não encontrada."))
		if escopo.perfil(doc.cliente) == CONSULTA:  # visibilidade já validada em _get_os_doc
			raise frappe.PermissionError(_("Seu perfil é somente consulta."))
		if doc.status_orcamento != "Aguardando Cliente":
			frappe.throw(_("Não há orçamento aguardando aprovação nesta OS."))
		doc.status_orcamento = "Aprovado" if aprovado else "Recusado"
		doc.status = "Em Execução" if aprovado else "Cancelada"
		doc.save(ignore_permissions=True)
		return self.obter_ordem(escopo, id)
