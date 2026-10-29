// Cores de status/prioridade/SLA: as mesmas em etiquetas e gráficos, nos dois temas.
export const COR = {
	marca: "#6366f1",
	verde: "#10b981",
	ambar: "#f59e0b",
	vermelho: "#f43f5e",
	laranja: "#f97316",
	azul: "#3b82f6",
	violeta: "#8b5cf6",
	cinza: "#94a3b8",
}

const TONS = {
	verde: "bg-emerald-500/12 text-emerald-700 ring-emerald-600/20 dark:text-emerald-300",
	ambar: "bg-amber-500/14 text-amber-700 ring-amber-600/25 dark:text-amber-300",
	vermelho: "bg-rose-500/12 text-rose-700 ring-rose-600/20 dark:text-rose-300",
	laranja: "bg-orange-500/12 text-orange-700 ring-orange-600/20 dark:text-orange-300",
	azul: "bg-blue-500/12 text-blue-700 ring-blue-600/20 dark:text-blue-300",
	violeta: "bg-violet-500/12 text-violet-700 ring-violet-600/20 dark:text-violet-300",
	marca: "bg-marca-500/12 text-marca-700 ring-marca-600/20 dark:text-marca-300",
	cinza: "bg-slate-500/12 text-slate-600 ring-slate-500/20 dark:text-slate-300",
}

const TOM_POR_VALOR = {
	Aberto: "azul",
	"Em Atendimento": "marca",
	"Aguardando Usuário": "ambar",
	Resolvido: "verde",
	Fechado: "cinza",
	Cancelado: "cinza",
	Crítica: "vermelho",
	Alta: "laranja",
	Média: "azul",
	Baixa: "cinza",
	"No Prazo": "verde",
	"Em Risco": "ambar",
	Violado: "vermelho",
	Cumprido: "verde",
	// equipamentos
	"Em Uso": "verde",
	"Em Estoque": "azul",
	"Em Manutenção": "ambar",
	Emprestado: "violeta",
	Descartado: "cinza",
	Extraviado: "vermelho",
}

export function tom(valor) {
	return TONS[TOM_POR_VALOR[valor] || "cinza"]
}

export const COR_PRIORIDADE = { Crítica: COR.vermelho, Alta: COR.laranja, Média: COR.azul, Baixa: COR.cinza }

/** Opções comuns de gráfico; cores do texto/grade seguem o tema. */
export function baseGrafico(escuro) {
	const texto = escuro ? "#8b95a8" : "#64748b"
	const grade = escuro ? "#1f2533" : "#eef1f6"
	return {
		texto,
		grade,
		tooltip: {
			backgroundColor: escuro ? "#1c2130" : "#0f172a",
			borderWidth: 0,
			padding: [8, 12],
			textStyle: { color: "#f8fafc", fontSize: 12, fontFamily: "Inter" },
			extraCssText: "border-radius:10px;box-shadow:0 10px 30px -10px rgba(0,0,0,.5);",
		},
		eixo: {
			axisLine: { show: false },
			axisTick: { show: false },
			axisLabel: { color: texto, fontSize: 11, fontFamily: "Inter" },
			splitLine: { lineStyle: { color: grade } },
		},
	}
}
