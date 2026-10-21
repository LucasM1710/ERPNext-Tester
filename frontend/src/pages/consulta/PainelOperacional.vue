<script setup>
import { Activity, CircleAlert, FlaskConical, Info, PackageCheck, ShieldAlert, Timer } from "lucide-vue-next"
import { computed, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import Grafico from "@/components/Grafico.vue"
import { COR, COR_STATUS } from "@/cores"
import { data } from "@/format"
import { clienteAtual, store } from "@/store"

const router = useRouter()
const d = ref(null)
const erro = ref(null)

onMounted(async () => {
	try {
		d.value = await api("consulta.painel")
	} catch (e) {
		erro.value = e.message
	}
})

const escopo = computed(() => {
	const distrito = (clienteAtual()?.distritos || []).find((x) => x.id === store.distrito)
	return distrito ? `Distrito ${distrito.nome}` : clienteAtual()?.usa_distritos ? "Todos os distritos" : clienteAtual()?.nome || "Todos os clientes"
})

const totais = computed(() => ({
	previsto: (d.value?.por_mes || []).reduce((s, m) => s + m.previsto, 0),
	executado: (d.value?.por_mes || []).reduce((s, m) => s + m.executado, 0),
}))

const grafMes = computed(() => ({
	tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
	grid: { left: 8, right: 8, top: 16, bottom: 4, containLabel: true },
	xAxis: { type: "category", data: d.value.por_mes.map((m) => m.mes), axisTick: { show: false }, axisLine: { show: false }, axisLabel: { color: "#55555a" } },
	yAxis: { type: "value", minInterval: 1, splitLine: { lineStyle: { color: "rgba(4,90,136,0.08)", type: "dashed" } }, axisLabel: { color: "#55555a" } },
	series: [
		{ name: "Previsto", type: "bar", barWidth: 16, barGap: "40%", data: d.value.por_mes.map((m) => m.previsto), itemStyle: { color: COR.ciano, borderRadius: [5, 5, 0, 0] } },
		{ name: "Executado", type: "bar", barWidth: 16, data: d.value.por_mes.map((m) => m.executado), itemStyle: { color: COR.brand, borderRadius: [5, 5, 0, 0] } },
	],
}))

const grafStatus = computed(() => ({
	tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
	series: [
		{
			type: "pie",
			radius: ["58%", "82%"],
			avoidLabelOverlap: true,
			itemStyle: { borderColor: "#fff", borderWidth: 3 },
			label: { show: true, position: "center", formatter: () => `${d.value.kpis.cadastrados}\nequipamentos`, fontSize: 15, fontWeight: 600, color: "#0f172a", lineHeight: 20 },
			data: d.value.status.filter((s) => s.valor).map((s) => ({ name: s.nome, value: s.valor, itemStyle: { color: COR_STATUS[s.nome] } })),
		},
	],
}))

const ANEL = 2 * Math.PI * 52
// % do parque em dia: equipamentos com calibração registrada que não estão vencidos.
const saude = computed(() => {
	if (!d.value) return null
	const k = d.value.kpis
	const base = k.cadastrados - k.sem_calibracao
	return base ? Math.round((100 * (base - k.vencidos)) / base) : null
})
const proximo = computed(() => (d.value?.urgentes || []).find((e) => e.dias_para_vencer >= 0))

function pct(v) {
	return v === null || v === undefined ? "—" : `${Math.round(v)}%`
}
function corPct(v) {
	if (v === null || v === undefined) return COR.cinza
	return v >= 90 ? COR.verde : v >= 70 ? COR.ambar : COR.vermelho
}
function dias(e) {
	if (e.dias_para_vencer < 0) return `vencido há ${-e.dias_para_vencer} dia(s)`
	if (e.dias_para_vencer === 0) return "vence hoje"
	return `vence em ${e.dias_para_vencer} dia(s)`
}
</script>

<template>
	<div class="space-y-5">
		<!-- Cabeçalho: saúde do parque -->
		<section class="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-900 via-brand-700 to-brand-600 p-6 text-white shadow-pop sm:p-8">
			<div class="pointer-events-none absolute -top-24 -right-10 size-72 rounded-full bg-white/5" />
			<div class="pointer-events-none absolute -bottom-32 left-1/4 size-80 rounded-full bg-cyan-300/10" />
			<div class="relative flex flex-wrap items-center justify-between gap-8">
				<div class="min-w-[280px] flex-1">
					<p class="text-sm text-white/70">Olá, {{ (store.contexto?.usuario.nome || "").split(" ")[0] }} 👋</p>
					<h1 class="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">Visão operacional</h1>
					<p class="mt-1 text-sm text-white/75">Situação de calibração do parque · {{ escopo }}</p>
					<div v-if="d" class="mt-5 flex flex-wrap gap-2 text-xs">
						<span class="rounded-full bg-white/10 px-3 py-1 ring-1 ring-white/20"><b>{{ d.kpis.laboratorio }}</b> calibrados pela ER Analítica</span>
						<span class="rounded-full bg-white/10 px-3 py-1 ring-1 ring-white/20"><b>{{ d.kpis.terceiros }}</b> por outros laboratórios</span>
						<span v-if="proximo" class="rounded-full bg-white/10 px-3 py-1 ring-1 ring-white/20">
							Próximo vencimento: <b>{{ proximo.tag }}</b> em {{ data(proximo.proxima_calibracao) }}
						</span>
					</div>
				</div>
				<div v-if="d" class="flex shrink-0 items-center gap-5 rounded-2xl bg-white/10 p-5 ring-1 ring-white/15 backdrop-blur">
					<svg viewBox="0 0 120 120" class="size-28 -rotate-90">
						<circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="10" />
						<circle cx="60" cy="60" r="52" fill="none" stroke="#5eead4" stroke-width="10" stroke-linecap="round" :stroke-dasharray="ANEL" :stroke-dashoffset="ANEL * (1 - (saude ?? 0) / 100)" />
					</svg>
					<div>
						<p class="text-[11px] tracking-[0.16em] text-white/60 uppercase">Parque em dia</p>
						<p class="text-4xl font-semibold tabular-nums">{{ saude === null ? "—" : `${saude}%` }}</p>
						<p class="text-xs text-white/70">dos equipamentos com calibração registrada</p>
					</div>
				</div>
			</div>
		</section>

		<div v-if="erro" class="card flex items-center gap-3 p-5 text-sm text-rose-700"><CircleAlert class="size-5" /> {{ erro }}</div>

		<template v-else-if="!d">
			<div class="grid gap-4 lg:grid-cols-4"><div v-for="i in 4" :key="i" class="card p-5"><Esqueleto :linhas="2" /></div></div>
			<div class="card p-5"><Esqueleto :linhas="8" /></div>
		</template>

		<template v-else>
			<!-- KPIs -->
			<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
				<div class="card p-5">
					<div class="flex items-start justify-between">
						<p class="text-[11px] font-semibold tracking-[0.16em] text-slate-500 uppercase">Equipamentos cadastrados</p>
						<span class="grid size-9 place-items-center rounded-xl bg-brand-50 text-brand-600"><PackageCheck class="size-[18px]" /></span>
					</div>
					<p class="mt-2 text-4xl font-semibold tracking-tight text-slate-900 tabular-nums">{{ d.kpis.cadastrados }}</p>
					<p class="mt-1 text-xs text-slate-500">{{ d.kpis.sem_calibracao }} ainda sem calibração registrada</p>
				</div>
				<div class="card p-5">
					<div class="flex items-start justify-between">
						<p class="text-[11px] font-semibold tracking-[0.16em] text-slate-500 uppercase">Equipamentos calibrados</p>
						<span class="grid size-9 place-items-center rounded-xl bg-emerald-50 text-emerald-600"><Activity class="size-[18px]" /></span>
					</div>
					<p class="mt-2 text-4xl font-semibold tracking-tight text-slate-900 tabular-nums">{{ d.kpis.calibrados }}</p>
					<p class="mt-1 text-xs text-slate-500">Com mais de 45 dias de validade</p>
				</div>
				<div class="card p-5">
					<div class="flex items-start justify-between">
						<p class="text-[11px] font-semibold tracking-[0.16em] text-slate-500 uppercase">Críticos</p>
						<span class="grid size-9 place-items-center rounded-xl bg-orange-50 text-orange-600"><Timer class="size-[18px]" /></span>
					</div>
					<p class="mt-2 text-4xl font-semibold tracking-tight text-slate-900 tabular-nums">{{ d.kpis.criticos }}</p>
					<p class="mt-1 text-xs text-slate-500">Vencem em até 45 dias</p>
				</div>
				<div class="card border-rose-200 p-5">
					<div class="flex items-start justify-between">
						<p class="text-[11px] font-semibold tracking-[0.16em] text-rose-600 uppercase">Equipamentos vencidos</p>
						<span class="grid size-9 place-items-center rounded-xl bg-rose-50 text-rose-600"><ShieldAlert class="size-[18px]" /></span>
					</div>
					<p class="mt-2 text-4xl font-semibold tracking-tight text-rose-700 tabular-nums">{{ d.kpis.vencidos }}</p>
					<p class="mt-1 text-xs text-slate-500">Calibração fora da validade</p>
				</div>
			</div>

			<!-- Gráficos -->
			<div class="grid items-stretch gap-5 xl:grid-cols-[1.5fr_1fr]">
				<section class="card flex min-w-0 flex-col p-5">
					<div class="flex flex-wrap items-start justify-between gap-3">
						<div>
							<h2 class="font-semibold text-slate-900">Calibrações por mês · {{ d.ano }}</h2>
							<p class="text-xs text-slate-500">Previsto = vencimentos no mês · Executado = calibrações realizadas (certificados emitidos)</p>
						</div>
						<div class="flex gap-4 text-xs text-slate-500">
							<span class="flex items-center gap-1.5"><span class="size-2.5 rounded-full" :style="{ background: COR.ciano }" /> Previsto</span>
							<span class="flex items-center gap-1.5"><span class="size-2.5 rounded-full" :style="{ background: COR.brand }" /> Executado</span>
						</div>
					</div>
					<Grafico class="mt-3 flex-1" :opcoes="grafMes" altura="280px" />
					<div class="mt-4 flex items-center gap-6 border-t border-slate-100 pt-4">
						<div>
							<p class="text-[10px] font-semibold tracking-[0.16em] text-slate-500 uppercase">Previsto</p>
							<p class="text-2xl font-semibold text-slate-900 tabular-nums">{{ totais.previsto }}</p>
						</div>
						<div class="h-8 w-px bg-slate-200" />
						<div>
							<p class="text-[10px] font-semibold tracking-[0.16em] text-slate-500 uppercase">Executado</p>
							<p class="text-2xl font-semibold text-slate-900 tabular-nums">{{ totais.executado }}</p>
						</div>
					</div>
				</section>

				<section class="card min-w-0 p-5">
					<h2 class="font-semibold text-slate-900">Status dos equipamentos</h2>
					<p class="text-xs text-slate-500">Faixas do laboratório pela data da próxima calibração</p>
					<Grafico class="mt-2" :opcoes="grafStatus" altura="230px" />
					<ul class="mt-3 grid grid-cols-2 gap-x-5 gap-y-2 text-sm">
						<li v-for="s in d.status" :key="s.nome" class="flex min-w-0 items-center justify-between gap-2">
							<span class="flex min-w-0 items-center gap-2 truncate text-slate-600"><span class="size-2.5 rounded-full" :style="{ background: COR_STATUS[s.nome] }" /> {{ s.nome }}</span>
							<span class="font-semibold text-slate-900 tabular-nums">{{ s.valor }}</span>
						</li>
					</ul>
				</section>
			</div>

			<!-- Resumo por distrito -->
			<section class="card overflow-hidden">
				<div class="px-5 pt-5 pb-3">
					<h2 class="font-semibold text-slate-900">Resumo por distrito</h2>
					<p class="text-xs text-slate-500">Responsável, UF e cidade vêm do cadastro do distrito</p>
				</div>
				<div class="overflow-x-auto">
					<table class="w-full min-w-[900px] text-sm">
						<thead class="bg-brand-700 text-white">
							<tr>
								<th class="px-4 py-2.5 text-left text-[11px] font-semibold tracking-wider uppercase">Distrito</th>
								<th class="px-4 py-2.5 text-left text-[11px] font-semibold tracking-wider uppercase">Responsável</th>
								<th class="px-4 py-2.5 text-left text-[11px] font-semibold tracking-wider uppercase">Cidade/UF</th>
								<th v-for="s in ['Calibrado', 'Alerta 60', 'Crítico', 'Vencido', 'Agendado', 'Sem calibração']" :key="s" class="px-3 py-2.5 text-right text-[11px] font-semibold tracking-wider uppercase">{{ s }}</th>
								<th class="px-3 py-2.5 text-right text-[11px] font-semibold tracking-wider uppercase">Total</th>
								<th class="px-4 py-2.5 text-right text-[11px] font-semibold tracking-wider uppercase">Em dia</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-slate-100">
							<tr v-if="!d.distritos.length"><td colspan="11" class="py-8 text-center text-slate-500">Nenhum equipamento no filtro selecionado.</td></tr>
							<tr v-for="g in d.distritos" :key="g.distrito" class="hover:bg-slate-50/70">
								<td class="px-4 py-2.5 font-medium text-slate-900">{{ g.distrito }}</td>
								<td class="px-4 py-2.5 text-slate-600">{{ g.owner || "—" }}</td>
								<td class="px-4 py-2.5 text-slate-600">{{ [g.cidade, g.uf].filter(Boolean).join("/") || "—" }}</td>
								<td v-for="s in ['Calibrado', 'Alerta 60', 'Crítico', 'Vencido', 'Agendado', 'Sem calibração']" :key="s" class="px-3 py-2.5 text-right tabular-nums" :class="g[s] && s === 'Vencido' ? 'font-semibold text-rose-600' : 'text-slate-700'">{{ g[s] }}</td>
								<td class="px-3 py-2.5 text-right font-semibold text-slate-900 tabular-nums">{{ g.total }}</td>
								<td class="px-4 py-2.5 text-right font-semibold tabular-nums" :style="{ color: corPct(g.em_dia_pct) }">{{ pct(g.em_dia_pct) }}</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>

			<!-- Urgentes -->
			<section class="card p-5">
				<div class="flex flex-wrap items-start justify-between gap-2">
					<div>
						<h2 class="font-semibold text-slate-900">Equipamentos urgentes</h2>
						<p class="text-xs text-slate-500">Vencidos ou vencendo nos próximos 45 dias — programe o envio ao laboratório</p>
					</div>
					<RouterLink to="/equipamentos" class="text-sm font-medium text-brand-600 hover:text-brand-700">Ver todos →</RouterLink>
				</div>
				<p v-if="!d.urgentes.length" class="mt-4 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-800">Nenhum equipamento vencido ou vencendo em 45 dias.</p>
				<ul v-else class="mt-4 divide-y divide-slate-100">
					<li v-for="e in d.urgentes" :key="e.id">
						<button class="flex w-full flex-wrap items-center gap-3 py-3 text-left hover:bg-slate-50/70" @click="router.push(`/equipamentos/${e.id}`)">
							<Etiqueta :valor="e.status_calibracao" />
							<span class="min-w-0 flex-1">
								<span class="font-medium text-slate-900">{{ e.descricao }}</span>
								<span class="text-slate-500"> · {{ e.tag }} · série {{ e.numero_serie || "—" }}</span>
								<span class="block text-xs text-slate-500">{{ e.distrito_nome || "Sem distrito" }}{{ e.owner ? ` · ${e.owner}` : "" }} · {{ e.vendor }}</span>
							</span>
							<span class="text-right text-sm">
								<span class="block font-medium" :class="e.dias_para_vencer < 0 ? 'text-rose-600' : 'text-orange-600'">{{ dias(e) }}</span>
								<span class="text-xs text-slate-500">próxima: {{ data(e.proxima_calibracao) }}</span>
							</span>
						</button>
					</li>
				</ul>
			</section>

			<p class="flex items-start gap-2 text-xs text-slate-500">
				<Info class="mt-0.5 size-3.5 shrink-0" />
				<span>
					<FlaskConical class="inline size-3.5" /> Equipamentos calibrados pela ER Analítica: datas e certificados vêm das ordens de serviço do laboratório.
					Equipamentos de outros laboratórios: dados informados pela sua empresa no portal. "Agendado" = equipamento em atendimento no laboratório.
				</span>
			</p>
		</template>
	</div>
</template>
