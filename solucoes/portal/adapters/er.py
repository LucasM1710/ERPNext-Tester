"""Adapter da página /consulta.

Duas fontes, sempre identificadas no portal (coluna "Calibrado por" / "Fonte"):

1. Equipamentos calibrados pela ER Analítica — SÓ LEITURA, vindos do ERP:
   - Equipamento: "Equipamentos" (cliente = `customer`).
   - Situação: última OS (Interna ou Externa) Encerrada do equipamento
     (`informe_numero_serie`), com `data_cal` e `data_cal_recomendada`.
   - Certificado: a própria OS Encerrada com `anexo_certificado` (PDF); padrões da tabela
     "Rastreabilidade dos Padrões"; RBC por `cal_rbc`.
   - Ordens: OS Interna e OS Externa, etapas pelo `status_order_service`.
2. Equipamentos de TERCEIROS — cadastrados e mantidos pelo próprio cliente no portal:
   "Equipamento Cliente" (origem Cliente) e "Certificado Calibracao" (origem Externo).

Distrito, responsável (owner), UF e cidade vêm do "Distrito Cliente"; o distrito de um
equipamento do ERP fica em "Distrito Equipamento" (o equipamento não ganha campo novo).
"""

import frappe
from frappe import _
from frappe.utils import cint, date_diff, getdate, today

from solucoes.metrologia.utils import calcular_situacao
from solucoes.portal import auditoria
from solucoes.portal.adapters.base import PortalAdapter, como_escopo
from solucoes.portal.adapters.padrao import AdapterPadrao

EQP = "Equipamentos"
EQP_CLIENTE = "Equipamento Cliente"
CERT_CLIENTE = "Certificado Calibracao"
OSI = "Ordem Servico Interna"
OSE = "Ordem Servico Externa"
MAPA = "Distrito Equipamento"
ENCERRADA = "Encerrada"
LABORATORIO = "ER Analítica"

# Faixas de status de calibração (dias até a próxima calibração).
DIAS_CRITICO = 45
DIAS_ALERTA = 60
# "Agendado" (A CONFIRMAR com o Lucas): hoje = equipamento com OS em aberto no laboratório.
AGENDADO_POR_OS_ABERTA = True

CAMPOS_OS = [
	"name", "customer", "status_order_service", "informe_numero_serie", "equipment_description",
	"equipment_tag", "serie_number", "data_cal", "data_cal_recomendada", "anexo_certificado", "cal_rbc",
	"quotation_link", "quotation_date", "sales_order_date", "repaired_date", "repair_status",
	"repair_schedule_date", "creation",
]  # fmt: skip
CAMPOS_EXTRA = {
	OSI: ["situacao_equipamento", "entry_date", "data_saida", "delivery_note_date"],
	OSE: ["sales_order_reference"],
}

# Etapas que o cliente vê e como cada status interno aparece para ele.
ETAPAS = {
	OSI: ["Recebida", "Em Análise", "Aguardando Aprovação", "Em Execução", "Expedição", "Concluída"],
	OSE: ["Em Análise", "Aguardando Aprovação", "Em Execução", "Concluída"],
}
STATUS_CLIENTE = {
	OSI: {
		"Em Recebimento": ("Recebida", 0),
		"Aguardando Orçamento": ("Em Análise", 1),
		"Em Orçamento": ("Em Análise", 1),
		"Em Aprovação": ("Aguardando Aprovação", 2),
		"Reprovado": ("Orçamento Recusado", 2),
		"Em Conserto": ("Em Execução", 3),
		"Sem Conserto": ("Sem Reparo", 3),
		"Embalar": ("Expedição", 4),
		"Aguardando Retirada": ("Pronta para Retirada", 4),
		ENCERRADA: ("Concluída", 5),
	},
	OSE: {
		"Em Orçamento": ("Em Análise", 0),
		"Em Aprovação": ("Aguardando Aprovação", 1),
		"Em Conserto": ("Em Execução", 2),
		ENCERRADA: ("Concluída", 3),
	},
}
FINAIS = (ENCERRADA, "Reprovado", "Sem Conserto")
RESULTADO = {
	"CONFORME": "Aprovado",
	"CONFORME COM RESTRIÇÃO": "Aprovado",
	"NÃO CONFORME": "Reprovado",
	"Liberado": "Aprovado",
	"Liberado com Restrição": "Aprovado",
	"Não Liberado": "Reprovado",
}
SOMENTE_CONSULTA = _("Os equipamentos calibrados pela ER Analítica são somente para consulta.")


def _str(valor):
	return str(valor) if valor else None


def _data(valor):
	"""Data em texto livre (ex.: validade do padrão) para ISO; None se não for data."""
	if not valor:
		return None
	try:
		return str(getdate(valor))
	except Exception:
		return None


def status_calibracao(proxima, agendado=False) -> tuple[str, int | None]:
	"""(status, dias para vencer) pelas faixas do laboratório."""
	dias = date_diff(proxima, today()) if proxima else None
	if agendado:
		return "Agendado", dias
	if dias is None:
		return "Sem calibração", None
	if dias < 0:
		return "Vencido", dias
	if dias <= DIAS_CRITICO:
		return "Crítico", dias
	if dias <= DIAS_ALERTA:
		return "Alerta 60", dias
	return "Calibrado", dias


def marcar_vigencia(certificados):
	"""Situação de cada certificado pela validade (fase 1, sem resultado de medição):
	Vigente = o mais recente do equipamento, dentro da validade; Vencido = o mais recente,
	com a validade vencida; Anterior = já substituído por um certificado mais novo.
	`certificados` precisa vir do mais recente para o mais antigo."""
	vistos = set()
	hoje = today()
	for c in certificados:
		eqp = c.get("equipamento_id")
		if eqp in vistos:
			c["vigencia"] = "Anterior"
			continue
		vistos.add(eqp)
		c["vigencia"] = "Vencido" if c.get("data_validade") and str(c["data_validade"]) < hoje else "Vigente"


class AdapterER(PortalAdapter):
	DOCTYPE_EQUIPAMENTO = EQP

	def __init__(self):
		self.padrao = AdapterPadrao()

	# ================================================================ distritos
	def _distritos(self, clientes) -> dict[str, dict]:
		return {
			d.name: d
			for d in frappe.get_all(
				"Distrito Cliente",
				filters={"cliente": ["in", list(clientes) or [""]]},
				fields=["name", "nome_distrito", "responsavel_nome", "responsavel_email", "uf", "cidade"],
			)
		}

	def _mapa(self, ids) -> dict[str, dict]:
		"""{equipamento do ERP: {distrito, observacao}}."""
		if not ids:
			return {}
		return {
			m.equipamento: m
			for m in frappe.get_all(
				MAPA,
				filters={"equipamento_doctype": EQP, "equipamento": ["in", list(ids)]},
				fields=["name", "equipamento", "distrito", "observacao", "dono"],
			)
		}

	def definir_donos(self, cliente, usuario, equipamentos) -> int:
		"""Equipamentos sob responsabilidade de `usuario` (perfil Usuário): define os da lista e
		tira o dono dos que ele tinha e saíram da lista."""
		equipamentos = set(equipamentos or [])
		alterados = 0
		for nome in frappe.get_all(MAPA, filters={"cliente": cliente, "dono": usuario}, pluck="equipamento"):
			if nome not in equipamentos:
				frappe.db.set_value(MAPA, {"equipamento_doctype": EQP, "equipamento": nome}, "dono", None)
				alterados += 1
		for nome in frappe.get_all(EQP_CLIENTE, filters={"cliente": cliente, "dono": usuario}, pluck="name"):
			if nome not in equipamentos:
				frappe.db.set_value(EQP_CLIENTE, nome, "dono", None)
				alterados += 1
		for id in equipamentos:
			if frappe.db.exists(EQP_CLIENTE, id):
				if frappe.db.get_value(EQP_CLIENTE, id, "cliente") != cliente:
					raise frappe.PermissionError
				frappe.db.set_value(EQP_CLIENTE, id, "dono", usuario)
			else:
				if frappe.db.get_value(EQP, id, "customer") != cliente:
					raise frappe.PermissionError
				nome = frappe.db.get_value(MAPA, {"equipamento_doctype": EQP, "equipamento": id})
				doc = frappe.get_doc(MAPA, nome) if nome else frappe.new_doc(MAPA)
				doc.update({"equipamento_doctype": EQP, "equipamento": id, "cliente": cliente, "dono": usuario})
				doc.save(ignore_permissions=True)
			alterados += 1
		return alterados

	def atribuir_distrito(self, cliente, distrito, equipamentos) -> int:
		movidos = 0
		for id in equipamentos:
			if frappe.db.exists(EQP_CLIENTE, id):
				movidos += self.padrao.atribuir_distrito(cliente, distrito, [id])
				continue
			if frappe.db.get_value(EQP, id, "customer") != cliente:
				raise frappe.PermissionError
			atual = frappe.db.get_value(MAPA, {"equipamento_doctype": EQP, "equipamento": id}, ["name", "distrito"], as_dict=True)
			if atual and atual.distrito == distrito:
				continue
			doc = frappe.get_doc(MAPA, atual.name) if atual else frappe.new_doc(MAPA)
			doc.update({"equipamento_doctype": EQP, "equipamento": id, "cliente": cliente, "distrito": distrito})
			doc.save(ignore_permissions=True)
			movidos += 1
		if movidos:
			auditoria.registrar(
				"Distribuição de equipamentos", cliente, "Distrito Cliente", distrito, depois={"equipamentos": equipamentos}
			)
		return movidos

	# ================================================================ OS (base do que vem do ERP)
	def _os(self, filtros) -> list[dict]:
		linhas = []
		for doctype in (OSI, OSE):
			for d in frappe.get_all(doctype, filters=filtros, fields=CAMPOS_OS + CAMPOS_EXTRA[doctype], limit_page_length=0):
				d.doctype = doctype
				linhas.append(d)
		return linhas

	def _calibracoes(self, equipamentos) -> dict[str, list]:
		"""{equipamento: OS encerradas, da mais recente para a mais antiga}."""
		por_eqp = {}
		for d in self._os({"informe_numero_serie": ["in", list(equipamentos) or [""]], "status_order_service": ENCERRADA}):
			por_eqp.setdefault(d.informe_numero_serie, []).append(d)
		for lista in por_eqp.values():
			lista.sort(key=lambda d: (str(d.data_cal or ""), str(d.creation)), reverse=True)
		return por_eqp

	def _em_andamento(self, equipamentos) -> set[str]:
		filtros = {"informe_numero_serie": ["in", list(equipamentos) or [""]], "status_order_service": ["not in", FINAIS]}
		return {d.informe_numero_serie for d in self._os(filtros)}

	# ================================================================ equipamentos
	def _base(self, origem, id, cliente, distrito, distritos, nomes_clientes, proxima, agendado, dono=None):
		info = distritos.get(distrito) or {}
		status, dias = status_calibracao(proxima, agendado)
		# Responsável: o dono do equipamento (perfil Usuário) ou, sem dono, o responsável do distrito.
		return {
			"id": id,
			"origem": origem,  # "laboratorio" (ERP, só leitura) | "cliente" (terceiro, cadastrado pelo cliente)
			"cliente": cliente,
			"cliente_nome": nomes_clientes.get(cliente) or cliente,
			"distrito": distrito,
			"distrito_nome": info.get("nome_distrito"),
			"owner": frappe.utils.get_fullname(dono) if dono else info.get("responsavel_nome"),
			"owner_email": dono or info.get("responsavel_email"),
			"dono": dono,
			"uf": info.get("uf"),
			"cidade": info.get("cidade"),
			"status_calibracao": status,
			"dias_para_vencer": dias,
			"situacao": calcular_situacao(proxima) if proxima else "Sem Calibração",
			"proxima_calibracao": _str(proxima),
			"agendado": bool(agendado),
		}

	def _do_erp(self, escopo, filtros_db, distritos, nomes) -> list[dict]:
		f = {"customer": ["in", list(escopo) or [""]]}
		f.update(filtros_db or {})
		linhas = frappe.get_all(
			EQP,
			filters=f,
			fields=["name", "customer", "tag", "descricao", "grandeza", "marca_equipamento", "modelo_equipamento", "numero_serie", "capacidade", "tipo_equipamento"],
			limit_page_length=0,
		)
		mapa = self._mapa([d.name for d in linhas])
		linhas = [
			d for d in linhas
			if escopo.pode_ver(d.customer, (mapa.get(d.name) or {}).get("distrito"), (mapa.get(d.name) or {}).get("dono"))
		]
		ids = [d.name for d in linhas]
		calibracoes, andamento = self._calibracoes(ids), self._em_andamento(ids)
		saida = []
		for d in linhas:
			m = mapa.get(d.name) or {}
			ultima = next((c for c in calibracoes.get(d.name, []) if c.data_cal), None)
			proxima = ultima.data_cal_recomendada if ultima else None
			periodicidade = None
			if ultima and ultima.data_cal and proxima:
				periodicidade = max(1, round(date_diff(proxima, ultima.data_cal) / 30.4))
			agendado = AGENDADO_POR_OS_ABERTA and d.name in andamento
			eqp = self._base("laboratorio", d.name, d.customer, m.get("distrito"), distritos, nomes, proxima, agendado, m.get("dono"))
			eqp.update(
				{
					"tag": d.tag or d.numero_serie or d.name,
					"descricao": d.descricao,
					"grandeza": d.grandeza,
					"tipo": d.tipo_equipamento,
					"fabricante": d.marca_equipamento,
					"modelo": d.modelo_equipamento,
					"numero_serie": d.numero_serie,
					"faixa_medicao": d.capacidade,
					"observacao": m.get("observacao"),
					"status": "Em Calibração" if d.name in andamento else "Ativo",
					"calibrado_por": "Nosso Laboratório",
					"vendor": LABORATORIO,
					"periodicidade_meses": periodicidade,
					"ultima_calibracao": _str(ultima.data_cal) if ultima else None,
					"certificado": ultima.name if ultima and ultima.anexo_certificado else None,
					"certificado_id": ultima.name if ultima and ultima.anexo_certificado else None,
					"origem_cadastro": "Laboratório",
					"editavel": False,
				}
			)
			saida.append(eqp)
		return saida

	def _de_terceiros(self, escopo, filtros_db, distritos, nomes) -> list[dict]:
		f = {"cliente": ["in", list(escopo) or [""]], "origem_cadastro": "Cliente"}
		f.update(filtros_db or {})
		linhas = frappe.get_all(EQP_CLIENTE, filters=f, fields=["*"], limit_page_length=0)
		linhas = [d for d in linhas if escopo.pode_ver(d.cliente, d.distrito, d.dono)]
		ultimos = {}
		for c in frappe.get_all(
			CERT_CLIENTE,
			filters={"equipamento": ["in", [d.name for d in linhas] or [""]]},
			fields=["name", "equipamento", "numero_certificado", "data_calibracao"],
			order_by="data_calibracao desc",
		):
			ultimos.setdefault(c.equipamento, c)
		saida = []
		for d in linhas:
			cert = ultimos.get(d.name)
			eqp = self._base("cliente", d.name, d.cliente, d.distrito, distritos, nomes, d.proxima_calibracao, False, d.dono)
			eqp.update(
				{
					"tag": d.tag,
					"descricao": d.descricao,
					"grandeza": d.grandeza,
					"tipo": None,
					"fabricante": d.fabricante,
					"modelo": d.modelo,
					"numero_serie": d.numero_serie,
					"faixa_medicao": d.faixa_medicao,
					"observacao": d.observacoes,
					"status": d.status,
					"calibrado_por": "Terceiro",
					"fornecedor_externo": d.fornecedor_externo,
					"vendor": d.fornecedor_externo or "Terceiro",
					"periodicidade_meses": d.periodicidade_meses,
					"ultima_calibracao": _str(d.ultima_calibracao),
					"certificado": (cert.numero_certificado or cert.name) if cert else None,
					"certificado_id": cert.name if cert else None,
					"origem_cadastro": "Cliente",
					"localizacao": d.localizacao,
					"editavel": True,
				}
			)
			saida.append(eqp)
		return saida

	def _equipamentos(self, escopo, filtro_erp=None, filtro_cliente=None, so=None) -> list[dict]:
		distritos = self._distritos(escopo)
		nomes = dict(frappe.get_all("Customer", filters={"name": ["in", list(escopo) or [""]]}, fields=["name", "customer_name"], as_list=True))
		lista = []
		if so in (None, "laboratorio"):
			lista += self._do_erp(escopo, filtro_erp, distritos, nomes)
		if so in (None, "cliente"):
			lista += self._de_terceiros(escopo, filtro_cliente, distritos, nomes)
		return lista

	def listar_equipamentos(self, clientes, filtros=None):
		escopo = como_escopo(clientes)
		filtros = filtros or {}
		lista = self._equipamentos(escopo)
		for chave in ("situacao", "status", "status_calibracao", "calibrado_por", "distrito", "grandeza", "origem"):
			if filtros.get(chave):
				lista = [e for e in lista if e.get(chave) == filtros[chave]]
		if filtros.get("owner"):
			lista = [e for e in lista if e.get("owner") == filtros["owner"]]
		if busca := (filtros.get("busca") or "").strip().lower():
			campos = ("tag", "descricao", "numero_serie", "modelo", "fabricante", "owner", "certificado", "vendor")
			lista = [e for e in lista if any(busca in str(e.get(c) or "").lower() for c in campos)]
		ordem = {"Vencido": 0, "Crítico": 1, "Alerta 60": 2, "Agendado": 3, "Calibrado": 4, "Sem calibração": 5}
		return sorted(
			lista, key=lambda e: (ordem.get(e["status_calibracao"], 9), e["dias_para_vencer"] if e["dias_para_vencer"] is not None else 99999, e["tag"] or "")
		)

	def obter_equipamento(self, clientes, id):
		escopo = como_escopo(clientes)
		if frappe.db.exists(EQP, id):
			lista = self._equipamentos(escopo, filtro_erp={"name": id}, so="laboratorio")
		elif frappe.db.exists(EQP_CLIENTE, id):
			lista = self._equipamentos(escopo, filtro_cliente={"name": id}, so="cliente")
		else:
			return None
		return lista[0] if lista else None

	def _ids_visiveis(self, escopo) -> set[str] | None:
		"""None = sem restrição de distrito; senão, os equipamentos do ERP que o usuário pode ver."""
		if not escopo.restrito:
			return None
		return {e["id"] for e in self._equipamentos(escopo, so="laboratorio")}

	# ---- escrita: só equipamentos de terceiros (e a observação dos do ERP)
	def criar_equipamento(self, clientes, dados):
		dados = dict(dados or {})
		dados["calibrado_por"] = "Terceiro"
		if not (dados.get("fornecedor_externo") or "").strip():
			frappe.throw(_("Informe o laboratório que calibra este equipamento."))
		eqp = self.padrao.criar_equipamento(clientes, dados)
		auditoria.registrar("Cadastro de equipamento de terceiro", eqp["cliente"], EQP_CLIENTE, eqp["id"], depois=dados)
		return self.obter_equipamento(clientes, eqp["id"])

	def atualizar_equipamento(self, clientes, id, dados):
		escopo = como_escopo(clientes)
		atual = self.obter_equipamento(escopo, id)
		if not atual:
			frappe.throw(_("Equipamento não encontrado."), frappe.DoesNotExistError)
		if not escopo.pode_editar(atual["cliente"], atual.get("distrito"), atual.get("dono")):
			raise frappe.PermissionError(_("Seu perfil não permite alterar este equipamento."))
		if atual["origem"] == "laboratorio":
			# Do equipamento calibrado pela ER, o cliente só anota a observação.
			if set((dados or {}).keys()) - {"observacao"}:
				raise frappe.PermissionError(SOMENTE_CONSULTA)
			return self.salvar_observacao(escopo, id, dados.get("observacao"))
		dados = dict(dados or {})
		dados["calibrado_por"] = "Terceiro"
		if "observacao" in dados:
			dados["observacoes"] = dados.pop("observacao")
		self.padrao.atualizar_equipamento(escopo, id, dados)
		auditoria.registrar("Edição de equipamento de terceiro", atual["cliente"], EQP_CLIENTE, id, antes=atual, depois=dados)
		return self.obter_equipamento(escopo, id)

	def salvar_observacao(self, escopo, id, observacao):
		atual = self.obter_equipamento(escopo, id)
		if not atual or atual["origem"] != "laboratorio":
			frappe.throw(_("Equipamento não encontrado."), frappe.DoesNotExistError)
		nome = frappe.db.get_value(MAPA, {"equipamento_doctype": EQP, "equipamento": id})
		doc = frappe.get_doc(MAPA, nome) if nome else frappe.new_doc(MAPA)
		doc.update({"equipamento_doctype": EQP, "equipamento": id, "cliente": atual["cliente"], "observacao": observacao})
		doc.save(ignore_permissions=True)
		auditoria.registrar(
			"Observação do equipamento", atual["cliente"], EQP, id, antes={"observacao": atual.get("observacao")}, depois={"observacao": observacao}
		)
		return self.obter_equipamento(escopo, id)

	# ================================================================ certificados
	def _certificado_os(self, d) -> dict:
		return {
			"id": d.name,
			"numero": d.name,
			"equipamento_id": d.informe_numero_serie,
			"tag": d.equipment_tag or d.serie_number,
			"descricao_equipamento": d.equipment_description,
			"cliente": d.customer,
			"data_calibracao": _str(d.data_cal),
			"data_validade": _str(d.data_cal_recomendada),
			"resultado": RESULTADO.get(d.get("situacao_equipamento") or d.repair_status or "", "Sem Critério"),
			"origem": "Interno",
			"laboratorio": LABORATORIO,
			"acreditado": bool(cint(d.cal_rbc)),
			"status_analise": None,
			"analisado_por": None,
			"data_analise": None,
			"tem_arquivo": bool(d.anexo_certificado),
			"fonte": "Ordem de serviço do laboratório",
		}

	def _os_certificados(self, escopo, filtros=None) -> list:
		filtros = filtros or {}
		f = {"customer": ["in", list(escopo) or [""]], "status_order_service": ENCERRADA, "anexo_certificado": ["is", "set"]}
		if filtros.get("equipamento"):
			f["informe_numero_serie"] = filtros["equipamento"]
		if filtros.get("de"):
			f["data_cal"] = [">=", filtros["de"]]
		linhas = self._os(f)
		if (visiveis := self._ids_visiveis(escopo)) is not None:
			linhas = [d for d in linhas if d.informe_numero_serie in visiveis]
		return linhas

	def _certificados_terceiros(self, escopo, filtros=None) -> list[dict]:
		filtros = filtros or {}
		ids = {e["id"] for e in self._equipamentos(escopo, so="cliente")}
		if filtros.get("equipamento"):
			ids &= {filtros["equipamento"]}
		if not ids:
			return []
		f = {"equipamento": ["in", list(ids)]}
		if filtros.get("de"):
			f["data_calibracao"] = [">=", filtros["de"]]
		saida = []
		for d in frappe.get_all(CERT_CLIENTE, filters=f, fields=["*"], limit_page_length=0):
			c = self.padrao._certificado(d)
			c["laboratorio"] = d.laboratorio_externo or "Terceiro"
			c["fonte"] = "Enviado pelo cliente"
			saida.append(c)
		return saida

	def listar_certificados(self, clientes, filtros=None):
		escopo = como_escopo(clientes)
		filtros = filtros or {}
		lista = [self._certificado_os(d) for d in self._os_certificados(escopo, filtros)]
		lista += self._certificados_terceiros(escopo, filtros)
		if filtros.get("resultado"):
			lista = [c for c in lista if c["resultado"] == filtros["resultado"]]
		if filtros.get("origem"):
			lista = [c for c in lista if c["origem"] == filtros["origem"]]
		if busca := (filtros.get("busca") or "").strip().lower():
			lista = [c for c in lista if any(busca in str(c.get(k) or "").lower() for k in ("numero", "tag", "descricao_equipamento", "laboratorio"))]
		lista = sorted(lista, key=lambda c: c["data_calibracao"] or "", reverse=True)
		marcar_vigencia(lista)
		return lista

	def _os_do_escopo(self, escopo, id):
		"""A OS `id` (Interna ou Externa) se o usuário pode vê-la."""
		for doctype in (OSI, OSE):
			if frappe.db.exists(doctype, id):
				d = frappe.db.get_value(doctype, id, CAMPOS_OS + CAMPOS_EXTRA[doctype], as_dict=True)
				d.doctype = doctype
				if d.customer not in escopo:
					return None
				if (visiveis := self._ids_visiveis(escopo)) is not None and d.informe_numero_serie not in visiveis:
					return None
				return d
		return None

	def _cert_terceiro_do_escopo(self, escopo, id):
		if not frappe.db.exists(CERT_CLIENTE, id):
			return None
		equipamento = frappe.db.get_value(CERT_CLIENTE, id, "equipamento")
		eqp = self.obter_equipamento(escopo, equipamento)
		return frappe.get_doc(CERT_CLIENTE, id) if eqp and eqp["origem"] == "cliente" else None

	def padroes_da_os(self, d) -> list[dict]:
		return [
			{
				"linha": p.idx,
				"codigo": p.codigo,
				"descricao": p.descricao,
				"numero_certificado": p.certificado_padrao,
				"laboratorio": "",
				"validade": _data(p.validade),
				"acreditado": False,
				"status": p.status,
				"tem_arquivo": bool(p.arquivo_padrao or p.padrao),
			}
			for p in frappe.get_all(
				"Rastreabilidade Padrao OS",
				filters={"parent": d.name, "parenttype": d.doctype},
				fields=["idx", "codigo", "descricao", "certificado_padrao", "validade", "status", "arquivo_padrao", "padrao"],
				order_by="idx",
			)
		]

	def _vigencia_de(self, escopo, cert):
		irmaos = self.listar_certificados(escopo, {"equipamento": cert["equipamento_id"]})
		return next((c["vigencia"] for c in irmaos if c["id"] == cert["id"]), None)

	def obter_certificado(self, clientes, id):
		escopo = como_escopo(clientes)
		if doc := self._cert_terceiro_do_escopo(escopo, id):
			cert = self.padrao.obter_certificado([doc.cliente], id)
			cert["laboratorio"] = doc.laboratorio_externo or "Terceiro"
			cert["fonte"] = "Enviado pelo cliente"
			cert["vigencia"] = self._vigencia_de(escopo, cert)
			return cert
		d = self._os_do_escopo(escopo, id)
		if not d or d.status_order_service != ENCERRADA or not d.anexo_certificado:
			return None
		cert = self._certificado_os(d)
		cert["vigencia"] = self._vigencia_de(escopo, cert)
		cert["pontos"] = []  # os resultados ficam no PDF (pontos estruturados: fase 2)
		cert["padroes"] = self.padroes_da_os(d)
		cert["ajustado"] = False
		return cert

	def obter_arquivo_certificado(self, clientes, id):
		escopo = como_escopo(clientes)
		if doc := self._cert_terceiro_do_escopo(escopo, id):
			arquivo, cliente = doc.arquivo, doc.cliente
		else:
			d = self._os_do_escopo(escopo, id)
			if not d or d.status_order_service != ENCERRADA:
				return None
			arquivo, cliente = d.anexo_certificado, d.customer
		if arquivo:
			auditoria.registrar("Download de certificado", cliente, None, None, depois={"certificado": id})
		return arquivo

	def arquivo_do_padrao(self, clientes, os_id, linha):
		"""PDF do certificado de um padrão usado na calibração (com checagem de acesso à OS)."""
		d = self._os_do_escopo(como_escopo(clientes), os_id)
		if not d or d.status_order_service != ENCERRADA:
			return None
		p = frappe.db.get_value(
			"Rastreabilidade Padrao OS",
			{"parent": os_id, "parenttype": d.doctype, "idx": cint(linha)},
			["codigo", "arquivo_padrao", "padrao"],
			as_dict=True,
		)
		if not p:
			return None
		arquivo = p.arquivo_padrao or (frappe.db.get_value("Padrao de Calibracao", p.padrao, "arquivo") if p.padrao else None)
		if arquivo:
			auditoria.registrar("Download de certificado de padrão", d.customer, None, None, depois={"os": os_id, "padrao": p.codigo})
		return arquivo

	def criar_certificado_externo(self, clientes, dados, file_url):
		escopo = como_escopo(clientes)
		eqp = self.obter_equipamento(escopo, (dados or {}).get("equipamento_id"))
		if not eqp:
			frappe.throw(_("Equipamento não encontrado."), frappe.DoesNotExistError)
		if eqp["origem"] != "cliente":
			raise frappe.PermissionError(_("Certificados de equipamentos calibrados pela ER Analítica vêm das OS do laboratório."))
		cert = self.padrao.criar_certificado_externo(escopo, dados, file_url)
		auditoria.registrar("Envio de certificado de terceiro", eqp["cliente"], CERT_CLIENTE, cert["id"], depois=dados)
		return cert

	# ================================================================ ordens de serviço
	def _ordem(self, d) -> dict:
		status, etapa = STATUS_CLIENTE[d.doctype].get(d.status_order_service or "", (d.status_order_service or "Em Análise", 0))
		finalizada = d.status_order_service in FINAIS
		interna = d.doctype == OSI
		return {
			"id": d.name,
			"cliente": d.customer,
			"tipo": "Laboratório" if interna else "In loco",
			"local_atendimento": "Laboratório" if interna else "In loco",
			"status": status,
			"etapas": ETAPAS[d.doctype],
			"etapa_atual": etapa,
			"finalizada": finalizada,
			"data_solicitacao": _str(d.get("entry_date") or getdate(d.creation)),
			"data_prevista": _str(d.repair_schedule_date) if not finalizada else None,
			"data_conclusao": _str(d.get("data_saida") or d.repaired_date) if finalizada else None,
			# Data prevista antiga em OS esquecida não vira "atrasada" para o cliente.
			"atrasada": False,
			"qtd_itens": 1,
			"orcamento": d.quotation_link,
			"status_orcamento": "Aguardando Cliente" if d.status_order_service == "Em Aprovação" else None,
			"equipamento_id": d.informe_numero_serie,
			"tag": d.equipment_tag or d.serie_number,
			"descricao_equipamento": d.equipment_description,
		}

	def listar_ordens(self, clientes, filtros=None):
		escopo = como_escopo(clientes)
		filtros = filtros or {}
		f = {"customer": ["in", list(escopo) or [""]]}
		if filtros.get("equipamento"):
			f["informe_numero_serie"] = filtros["equipamento"]
		linhas = self._os(f)
		if (visiveis := self._ids_visiveis(escopo)) is not None:
			linhas = [d for d in linhas if d.informe_numero_serie in visiveis]
		lista = [self._ordem(d) for d in linhas]
		if filtros.get("status"):
			lista = [o for o in lista if o["status"] == filtros["status"]]
		return sorted(lista, key=lambda o: (o["data_solicitacao"] or "", o["id"]), reverse=True)

	def obter_ordem(self, clientes, id):
		escopo = como_escopo(clientes)
		d = self._os_do_escopo(escopo, id)
		if not d:
			return None
		ordem = self._ordem(d)
		tem_certificado = d.status_order_service == ENCERRADA and d.anexo_certificado
		ordem["itens"] = [
			{
				"equipamento_id": d.informe_numero_serie,
				"tag": d.equipment_tag or d.serie_number,
				"descricao": d.equipment_description,
				"servico": "Calibração / manutenção",
				"status": ordem["status"],
				"certificado_id": d.name if tem_certificado else None,
				"laudo": None,
			}
		]
		ordem["itens_outros_distritos"] = 0
		marcos = [
			("Recebida", d.get("entry_date") or getdate(d.creation)),
			("Orçamento enviado", d.quotation_date),
			("Orçamento aprovado", d.sales_order_date),
			("Serviço concluído", d.repaired_date),
			("Entregue", d.get("data_saida") or d.get("delivery_note_date")),
		]
		ordem["historico"] = [
			{"status": nome, "data": _str(data), "usuario": None}
			for nome, data in sorted((m for m in marcos if m[1]), key=lambda m: str(m[1]), reverse=True)
		]
		ordem["observacoes_cliente"] = None
		return ordem

	# ================================================================ fora desta página (fase 2)
	def registrar_analise_critica(self, clientes, id, status, observacao, usuario):
		raise frappe.PermissionError(_("Análise crítica não está disponível nesta página."))

	def solicitar_servico(self, clientes, contato, dados):
		raise frappe.PermissionError(_("Solicitação de serviço não está disponível nesta página."))

	def responder_orcamento(self, clientes, id, aprovado):
		raise frappe.PermissionError(_("Aprovação de orçamento não está disponível nesta página."))

	def registrar_verificacao(self, clientes, equipamento_id, dados):
		raise frappe.PermissionError(_("Verificação intermediária não está disponível nesta página."))
