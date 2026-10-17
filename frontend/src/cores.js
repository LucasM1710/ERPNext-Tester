// Paleta única usada em badges e gráficos, para que "Vencido" tenha a mesma cor em toda parte.
export const COR = {
	brand: "#2549ea",
	brandClaro: "#93b4fd",
	verde: "#10b981",
	ambar: "#f59e0b",
	vermelho: "#f43f5e",
	cinza: "#94a3b8",
	texto: "#64748b",
	grade: "#eef2f7",
}

export const COR_SITUACAO = {
	"Em Dia": COR.verde,
	"A Vencer": COR.ambar,
	Vencido: COR.vermelho,
	"Sem Calibração": COR.cinza,
}

const TONS = {
	verde: "bg-emerald-50 text-emerald-700 ring-emerald-600/15",
	ambar: "bg-amber-50 text-amber-700 ring-amber-600/20",
	vermelho: "bg-rose-50 text-rose-700 ring-rose-600/15",
	azul: "bg-brand-50 text-brand-700 ring-brand-600/15",
	violeta: "bg-violet-50 text-violet-700 ring-violet-600/15",
	cinza: "bg-slate-100 text-slate-600 ring-slate-500/15",
}

const TOM_POR_VALOR = {
	"Em Dia": "verde",
	"A Vencer": "ambar",
	Vencido: "vermelho",
	"Sem Calibração": "cinza",
	Aprovado: "verde",
	Reprovado: "vermelho",
	"Sem Critério": "cinza",
	Pendente: "ambar",
	Solicitada: "cinza",
	Recebida: "azul",
	"Em Análise": "azul",
	"Aguardando Aprovação": "ambar",
	"Em Execução": "violeta",
	Concluída: "verde",
	Enviada: "verde",
	Cancelada: "vermelho",
	Concluído: "verde",
	"Sem Reparo": "vermelho",
	"Aguardando Cliente": "ambar",
	Recusado: "vermelho",
	Ativo: "verde",
	"Em Calibração": "violeta",
	"Em Manutenção": "violeta",
	Inativo: "cinza",
	Sucateado: "cinza",
	Reserva: "azul",
	Terceiro: "violeta",
	Externo: "violeta",
	Interno: "azul",
}

export function classeTom(valor) {
	return TONS[TOM_POR_VALOR[valor] || "cinza"]
}

export const tooltipBase = {
	backgroundColor: "#0f172a",
	borderWidth: 0,
	padding: [8, 12],
	textStyle: { color: "#f8fafc", fontSize: 12, fontFamily: "Inter" },
	extraCssText: "border-radius:10px;box-shadow:0 10px 30px -10px rgba(15,23,42,.5);",
}

export const eixoBase = {
	axisLine: { show: false },
	axisTick: { show: false },
	axisLabel: { color: COR.texto, fontSize: 11, fontFamily: "Inter" },
	splitLine: { lineStyle: { color: COR.grade } },
}
