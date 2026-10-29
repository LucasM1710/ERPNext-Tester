"""SLA em horas úteis: expediente, sábados opcionais e feriados (Holiday List do ERPNext).

As funções de cálculo são puras (recebem um `Expediente`) para serem testáveis sem banco.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

import frappe
from frappe.utils import get_datetime, get_time, getdate, now_datetime

CONFIG = "Configuracao Central TI"
PRIORIDADES = ("Baixa", "Média", "Alta", "Crítica")

# Prazos padrão (horas úteis): usados quando a configuração ainda não tem a tabela preenchida
PRAZOS_PADRAO = {
	"Crítica": (1, 4),
	"Alta": (2, 8),
	"Média": (4, 16),
	"Baixa": (8, 40),
}


@dataclass
class Expediente:
	inicio: time = time(8, 0)
	fim: time = time(18, 0)
	sabado: bool = False
	feriados: set = field(default_factory=set)

	def dia_util(self, d: date) -> bool:
		if d in self.feriados:
			return False
		return d.weekday() < 5 or (self.sabado and d.weekday() == 5)

	def janela(self, d: date) -> tuple[datetime, datetime]:
		return datetime.combine(d, self.inicio), datetime.combine(d, self.fim)


def adicionar_horas_uteis(inicio: datetime, horas: float, exp: Expediente) -> datetime:
	"""Data/hora em que se completam `horas` úteis a partir de `inicio`."""
	cursor = get_datetime(inicio)
	restante = timedelta(hours=float(horas or 0))
	for _ in range(3660):  # no máximo ~10 anos de dias, por segurança
		abre, fecha = exp.janela(cursor.date())
		if not exp.dia_util(cursor.date()) or cursor >= fecha:
			cursor = datetime.combine(cursor.date() + timedelta(days=1), exp.inicio)
			continue
		cursor = max(cursor, abre)
		disponivel = fecha - cursor
		if restante <= disponivel:
			return cursor + restante
		restante -= disponivel
		cursor = datetime.combine(cursor.date() + timedelta(days=1), exp.inicio)
	return cursor


def horas_uteis_entre(a: datetime, b: datetime, exp: Expediente) -> float:
	"""Horas úteis entre dois instantes (0 se b <= a)."""
	a, b = get_datetime(a), get_datetime(b)
	if b <= a:
		return 0.0
	total = timedelta()
	dia = a.date()
	while dia <= b.date():
		if exp.dia_util(dia):
			abre, fecha = exp.janela(dia)
			ini, fim = max(a, abre), min(b, fecha)
			if fim > ini:
				total += fim - ini
		dia += timedelta(days=1)
	return round(total.total_seconds() / 3600, 4)


def situacao(inicio, prazo, concluido_em, agora, alerta_pct, exp: Expediente) -> str:
	"""No Prazo / Em Risco / Violado (em andamento) ou Cumprido / Violado (concluído)."""
	if not prazo:
		return ""
	prazo = get_datetime(prazo)
	if concluido_em:
		return "Cumprido" if get_datetime(concluido_em) <= prazo else "Violado"
	agora = get_datetime(agora)
	if agora > prazo:
		return "Violado"
	total = horas_uteis_entre(inicio, prazo, exp)
	usado = horas_uteis_entre(inicio, agora, exp)
	if total and usado / total * 100 >= (alerta_pct or 80):
		return "Em Risco"
	return "No Prazo"


# ------------------------------------------------------------------ leitura da configuração
def config():
	return frappe.get_cached_doc(CONFIG)


def expediente() -> Expediente:
	cfg = config()
	feriados = set()
	if cfg.lista_feriados:
		feriados = {getdate(d) for d in frappe.get_all("Holiday", filters={"parent": cfg.lista_feriados}, pluck="holiday_date")}
	return Expediente(
		inicio=get_time(cfg.horario_inicio or "08:00:00"),
		fim=get_time(cfg.horario_fim or "18:00:00"),
		sabado=bool(cfg.trabalha_sabado),
		feriados=feriados,
	)


def prazos_da_prioridade(prioridade: str) -> tuple[float, float]:
	"""(horas úteis para a 1ª resposta, horas úteis para a resolução)."""
	for linha in config().prazos or []:
		if linha.prioridade == prioridade:
			return float(linha.primeira_resposta_horas or 0), float(linha.resolucao_horas or 0)
	return PRAZOS_PADRAO.get(prioridade, PRAZOS_PADRAO["Média"])


def agora() -> datetime:
	return now_datetime()
