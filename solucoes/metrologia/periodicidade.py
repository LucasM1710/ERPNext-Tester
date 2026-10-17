"""Periodicidade inteligente (ILAC-G24 / OIML D10).

Sugere o intervalo de calibração a partir do histórico, medido como "uso da tolerância":

	uso = (|erro encontrado| + U) / tolerância      (do pior ponto de cada calibração)

	uso < 0,5  -> muita folga       uso 0,5–0,8 -> adequado
	uso > 0,8  -> pouca folga       uso > 1     -> encontrado fora da tolerância

Métodos:
- Tendência de deriva (≥ 3 calibrações): regressão linear do uso no tempo; projeta quando o
  uso chega a 1 e aplica margem de segurança.
- Escada (ILAC-G24 método 1, "staircase"): reage à última calibração (+25% / −25% / −50%).

A sugestão é limitada a no máximo dobrar ou reduzir à metade de uma vez: a periodicidade
é decisão do cliente e mudanças graduais são mais seguras.
Função pura (sem banco) para ser testável e reaproveitável por qualquer adapter.
"""

import math
from datetime import date

from frappe.utils import getdate

MARGEM_SEGURANCA = 0.8  # agenda a calibração antes de chegar a 80% do caminho até o limite
MINIMO_MESES, MAXIMO_MESES = 1, 60


def _limitar(meses, atual):
	return int(max(MINIMO_MESES, min(MAXIMO_MESES, atual * 2, max(meses, math.ceil(atual / 2)))))


def _regressao(xs, ys):
	n = len(xs)
	mx, my = sum(xs) / n, sum(ys) / n
	sxx = sum((x - mx) ** 2 for x in xs)
	if not sxx:
		return 0.0, my, 0.0
	inclinacao = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx
	intercepto = my - inclinacao * mx
	ss_tot = sum((y - my) ** 2 for y in ys)
	ss_res = sum((y - (intercepto + inclinacao * x)) ** 2 for x, y in zip(xs, ys, strict=True))
	r2 = 1 - ss_res / ss_tot if ss_tot else 1.0
	return inclinacao, intercepto, r2


def sugerir_periodicidade(historico: list[dict], atual_meses: int | None) -> dict | None:
	"""historico: [{"data": date|str, "uso": float}] de qualquer ordem. Retorna None sem dados."""
	pontos = sorted(
		({"data": getdate(h["data"]), "uso": float(h["uso"])} for h in historico if h.get("uso") is not None),
		key=lambda h: h["data"],
	)
	if not pontos or not atual_meses:
		return None

	ultimo = pontos[-1]["uso"]
	base = {"atual": atual_meses, "uso_ultimo_pct": round(100 * ultimo), "calibracoes_analisadas": len(pontos)}

	def resultado(sugerida, metodo, justificativa, confianca):
		sugerida = _limitar(sugerida, atual_meses)
		acao = "aumentar" if sugerida > atual_meses else "reduzir" if sugerida < atual_meses else "manter"
		return {**base, "sugerida": sugerida, "acao": acao, "metodo": metodo, "justificativa": justificativa, "confianca": confianca}

	# 1) Encontrado fora da tolerância: reduzir à metade, independentemente do resto
	if ultimo > 1:
		return resultado(
			math.floor(atual_meses / 2),
			"Reação a não conformidade",
			f"Na última calibração o equipamento foi encontrado fora da tolerância (uso de {round(100 * ultimo)}%). "
			"Recomenda-se reduzir o intervalo até que o comportamento se estabilize.",
			"alta",
		)

	# 2) Tendência de deriva, com histórico suficiente
	if len(pontos) >= 3:
		inicio: date = pontos[0]["data"]
		xs = [(p["data"] - inicio).days for p in pontos]
		ys = [p["uso"] for p in pontos]
		inclinacao, _, r2 = _regressao(xs, ys)
		confianca = "alta" if r2 >= 0.8 and len(pontos) >= 4 else "média" if r2 >= 0.5 else "baixa"
		if inclinacao > 0 and r2 >= 0.5:
			dias_ate_limite = (1 - ultimo) / inclinacao * MARGEM_SEGURANCA
			meses = max(1, math.floor(dias_ate_limite / 30.4))
			return resultado(
				meses,
				"Tendência de deriva",
				f"O erro cresce cerca de {round(100 * inclinacao * 365, 1)} pontos percentuais da tolerância por ano "
				f"(R² = {r2:.2f}). Projetando a deriva, o equipamento atingiria o limite em ~{round(dias_ate_limite / MARGEM_SEGURANCA / 30.4)} meses; "
				f"com margem de segurança de {round(100 * (1 - MARGEM_SEGURANCA))}%, a sugestão é {meses} meses.",
				confianca,
			)
		if inclinacao <= 0 and max(ys) < 0.5:
			return resultado(
				math.ceil(atual_meses * 1.25),
				"Tendência de deriva",
				f"Nas últimas {len(pontos)} calibrações o erro ficou estável ou diminuiu, sempre abaixo de 50% da tolerância. "
				"Há margem para ampliar o intervalo com segurança.",
				confianca,
			)

	# 3) Escada (ILAC-G24 método 1)
	if ultimo > 0.8:
		return resultado(
			math.floor(atual_meses * 0.75),
			"Escada (ILAC-G24)",
			f"A última calibração usou {round(100 * ultimo)}% da tolerância: pouca folga para o próximo ciclo.",
			"média",
		)
	if ultimo < 0.5 and len(pontos) >= 2 and pontos[-2]["uso"] < 0.8:
		return resultado(
			math.ceil(atual_meses * 1.25),
			"Escada (ILAC-G24)",
			f"As duas últimas calibrações ficaram com folga (uso de {round(100 * pontos[-2]['uso'])}% e {round(100 * ultimo)}%).",
			"média" if len(pontos) >= 3 else "baixa",
		)
	return resultado(
		atual_meses,
		"Escada (ILAC-G24)",
		f"O uso da tolerância ({round(100 * ultimo)}%) está na faixa adequada"
		+ ("." if len(pontos) >= 2 else "; é necessário mais histórico para recomendar mudanças."),
		"média" if len(pontos) >= 2 else "baixa",
	)
