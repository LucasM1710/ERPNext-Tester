<script setup>
import {
	ArrowRight,
	CalendarClock,
	ClipboardCheck,
	ClipboardList,
	FileSearch,
	Plus,
	ReceiptText,
	ShieldCheck,
	TriangleAlert,
} from "lucide-vue-next"
import { computed, onMounted, ref } from "vue"
import { api } from "@/api"
import CartaoKpi from "@/components/CartaoKpi.vue"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import Grafico from "@/components/Grafico.vue"
import LinhaEtapas from "@/components/LinhaEtapas.vue"
import { COR, COR_SITUACAO, eixoBase, tooltipBase } from "@/cores"
import { data, mesCurto, relativo } from "@/format"
import { definirDistrito, podeEditar, store } from "@/store"

const d = ref(null)
const erro = ref(null)

onMounted(async () => {
	try {
		d.value = await api("dashboard")
	} catch (e) {
		erro.value = e.message
	}
})

const primeiroNome = computed(() => (store.contexto.usuario.nome || "").split(" ")[0])
const hoje = new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" })

const grafSituacao = computed(() => {
	const s = d.value.situacoes
	return {
		tooltip: { ...tooltipBase, trigger: "item", formatter: "{b}: <b>{c}</b> ({d}%)" },
		series: [
			{
				type: "pie",
				radius: ["64%", "86%"],
				padAngle: 2,
				itemStyle: { borderRadius: 6 },
				label: { show: false },
				emphasis: { scale: true, scaleSize: 4 },
				data: Object.entries(s)
					.filter(([, v]) => v > 0)
					.map(([nome, valor]) => ({ name: nome, value: valor, itemStyle: { color: COR_SITUACAO[nome] } })),
			},
		],
	}
})

const grafVencimentos = computed(() => {
	const v = d.value.vencimentos_por_mes
	const rotulos = ["Vencidos", ...v.meses.map(mesCurto)]
	const valores = [
		{ value: v.ja_vencidos, itemStyle: { color: COR.vermelho } },
		...v.quantidades.map((q, i) => ({
			value: q,
			itemStyle: {
				color:
					i === 0
						? COR.ambar
						: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "#3b67f5" }, { offset: 1, color: "#93b4fd" }] },
			},
		})),
	]
	return {
		grid: { left: 8, right: 8, top: 24, bottom: 4, containLabel: true },
		tooltip: { ...tooltipBase, trigger: "axis", axisPointer: { type: "shadow", shadowStyle: { color: "rgba(37,73,234,.06)" } } },
		xAxis: { type: "category", data: rotulos, ...eixoBase, splitLine: { show: false } },
		yAxis: { type: "value", minInterval: 1, ...eixoBase },
		series: [
			{
				type: "bar",
				name: "Equipamentos",
				data: valores,
				barMaxWidth: 26,
				itemStyle: { borderRadius: [6, 6, 2, 2] },
				label: { show: true, position: "top", color: COR.texto, fontSize: 11, formatter: (p) => (p.value ? p.value : "") },
			},
		],
	}
})

const grafResultados = computed(() => {
	const r = d.value.resultados_12m
	return {
		grid: { left: 8, right: 8, top: 36, bottom: 4, containLabel: true },
		legend: { top: 0, right: 0, icon: "roundRect", itemWidth: 10, itemHeight: 10, textStyle: { color: COR.texto, fontSize: 12 } },
		tooltip: { ...tooltipBase, trigger: "axis" },
		xAxis: { type: "category", data: r.meses.map(mesCurto), ...eixoBase, splitLine: { show: false } },
		yAxis: { type: "value", minInterval: 1, ...eixoBase },
		series: [
			{ name: "Aprovados", type: "bar", stack: "t", data: r.aprovados, barMaxWidth: 22, itemStyle: { color: COR.verde } },
			{ name: "Reprovados", type: "bar", stack: "t", data: r.reprovados, barMaxWidth: 22, itemStyle: { color: COR.vermelho, borderRadius: [6, 6, 0, 0] } },
		],
	}
})

const grafGrandeza = computed(() => {
	const entradas = Object.entries(d.value.por_grandeza).reverse()
	return {
		grid: { left: 4, right: 28, top: 4, bottom: 4, containLabel: true },
		tooltip: { ...tooltipBase, trigger: "item", formatter: "{b}: <b>{c}</b>" },
		xAxis: { type: "value", show: false },
		yAxis: { type: "category", data: entradas.map((e) => e[0]), ...eixoBase },
		series: [
			{
				type: "bar",
				data: entradas.map((e) => e[1]),
				barWidth: 14,
				itemStyle: { color: COR.brand, borderRadius: 7 },
				showBackground: true,
				backgroundStyle: { color: "#f1f5f9", borderRadius: 7 },
				label: { show: true, position: "right", color: COR.texto, fontSize: 11 },
			},
		],
	}
})

// Ranking de distritos: barras empilhadas por situação, pior distrito em cima
const grafDistritos = computed(() => {
	const r = [...d.value.por_distrito].reverse()
	const serie = (nome) => ({
		name: nome,
		type: "bar",
		stack: "t",
		barWidth: 16,
		data: r.map((x) => x[nome]),
		itemStyle: { color: COR_SITUACAO[nome] },
	})
	return {
		grid: { left: 4, right: 56, top: 32, bottom: 4, containLabel: true },
		legend: { top: 0, right: 0, icon: "roundRect", itemWidth: 10, itemHeight: 10, textStyle: { color: COR.texto, fontSize: 12 } },
		tooltip: { ...tooltipBase, trigger: "axis", axisPointer: { type: "shadow", shadowStyle: { color: "rgba(37,73,234,.06)" } } },
		xAxis: { type: "value", show: false },
		yAxis: {
			type: "category",
			data: r.map((x) => x.nome),
			...eixoBase,
			axisLabel: { ...eixoBase.axisLabel, fontSize: 12, color: "#334155" },
		},
		series: [
			serie("Vencido"),
			serie("A Vencer"),
			serie("Em Dia"),
			{
				...serie("Sem Calibração"),
				itemStyle: { color: COR_SITUACAO["Sem Calibração"], borderRadius: [0, 6, 6, 0] },
				label: {
					show: true,
					position: "right",
					formatter: (p) => `${r[p.dataIndex].em_dia_pct}%`,
					fontWeight: 600,
					color: "#0f172a",
				},
			},
		],
	}
})

function abrirDistrito(params) {
	const alvo = [...d.value.por_distrito].reverse()[params.dataIndex]
	if (alvo) definirDistrito(alvo.distrito)
}

const grafEmDia = computed(() => ({
	series: [
		{
			type: "gauge",
			startAngle: 90,
			endAngle: -270,
			radius: "100%",
			pointer: { show: false },
			progress: { show: true, roundCap: true, width: 9, itemStyle: { color: d.value.kpis.em_dia_pct >= 90 ? COR.verde : d.value.kpis.em_dia_pct >= 75 ? COR.ambar : COR.vermelho } },
			axisLine: { lineStyle: { width: 9, color: [[1, "#eef2f7"]] } },
			splitLine: { show: false },
			axisTick: { show: false },
			axisLabel: { show: false },
			detail: { show: false },
			data: [{ value: d.value.kpis.em_dia_pct }],
		},
	],
}))
</script>

<template>
	<div class="space-y-6">
		<!-- Cabeçalho -->
		<div class="flex flex-wrap items-end justify-between gap-4">
			<div>
				<p class="text-sm text-slate-500 first-letter:uppercase">{{ hoje }}</p>
				<h1 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Olá, {{ primeiroNome }} 👋</h1>
				<p class="mt-1 text-sm text-slate-500">Acompanhe a saúde metrológica do seu parque de equipamentos.</p>
			</div>
			<RouterLink v-if="podeEditar()" to="/solicitar" class="btn-primary"><Plus class="size-4" /> Solicitar serviço</RouterLink>
		</div>

		<div v-if="erro" class="card p-6 text-sm text-rose-600">{{ erro }}</div>

		<template v-else-if="!d">
			<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
				<div v-for="i in 4" :key="i" class="card p-5"><Esqueleto :linhas="3" /></div>
			</div>
			<div class="grid gap-4 lg:grid-cols-3">
				<div v-for="i in 3" :key="i" class="card h-72 p-5"><Esqueleto :linhas="6" /></div>
			</div>
		</template>

		<template v-else>
			<!-- Alerta de vencidos -->
			<div
				v-if="d.kpis.vencidos"
				class="flex flex-wrap items-center gap-4 rounded-2xl border border-rose-200 bg-gradient-to-r from-rose-50 to-white p-4"
			>
				<span class="grid size-10 place-items-center rounded-xl bg-rose-100 text-rose-600"><TriangleAlert class="size-5" /></span>
				<div class="min-w-0 flex-1">
					<p class="font-semibold text-rose-900">
						{{ d.kpis.vencidos }} equipamento{{ d.kpis.vencidos > 1 ? "s" : "" }} com calibração vencida
					</p>
					<p class="text-sm text-rose-700/80">Instrumentos vencidos não devem ser usados em medições do processo.</p>
				</div>
				<RouterLink :to="{ path: '/equipamentos', query: { situacao: 'Vencido' } }" class="btn-danger">
					Ver e solicitar calibração <ArrowRight class="size-4" />
				</RouterLink>
			</div>

			<!-- KPIs -->
			<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
				<div class="card flex items-center gap-4 p-5">
					<div class="relative size-[84px] shrink-0">
						<Grafico :opcoes="grafEmDia" altura="84px" />
						<span class="absolute inset-0 grid place-items-center text-sm font-semibold text-slate-900 tabular-nums"
							>{{ Math.round(d.kpis.em_dia_pct) }}%</span
						>
					</div>
					<div>
						<p class="text-sm font-medium text-slate-500">Parque em dia</p>
						<p class="mt-1 text-xs leading-relaxed text-slate-500">
							{{ d.kpis.total_equipamentos }} equipamentos ativos<br />{{ d.situacoes["Sem Calibração"] }} sem calibração registrada
						</p>
					</div>
				</div>
				<CartaoKpi
					titulo="Vencidos"
					:valor="d.kpis.vencidos"
					descricao="Precisam de calibração imediata"
					:icone="TriangleAlert"
					tom="vermelho"
					:para="{ path: '/equipamentos', query: { situacao: 'Vencido' } }"
				/>
				<CartaoKpi
					titulo="A vencer"
					:valor="d.kpis.a_vencer"
					:descricao="`Nos próximos ${store.contexto.config.dias_alerta} dias`"
					:icone="CalendarClock"
					tom="ambar"
					:para="{ path: '/equipamentos', query: { situacao: 'A Vencer' } }"
				/>
				<CartaoKpi
					titulo="Ordens em andamento"
					:valor="d.kpis.ordens_abertas"
					descricao="Em atendimento pelo laboratório"
					:icone="ClipboardList"
					tom="violeta"
					para="/ordens"
				/>
			</div>

			<!-- Pendências do cliente -->
			<div
				v-if="d.kpis.analises_pendentes || d.kpis.orcamentos_pendentes || d.kpis.verificacoes_atrasadas || d.kpis.verificacoes_nao_conformes"
				class="grid gap-4 md:grid-cols-2"
			>
				<RouterLink
					v-if="d.kpis.verificacoes_nao_conformes || d.kpis.verificacoes_atrasadas"
					:to="{ path: '/equipamentos', query: { verificacao: 'pendente' } }"
					class="card group flex items-center gap-4 p-4 transition hover:shadow-pop"
				>
					<span
						class="grid size-10 place-items-center rounded-xl"
						:class="d.kpis.verificacoes_nao_conformes ? 'bg-rose-50 text-rose-600' : 'bg-amber-50 text-amber-600'"
						><ClipboardCheck class="size-5"
					/></span>
					<div class="flex-1">
						<p class="font-medium text-slate-900">
							<template v-if="d.kpis.verificacoes_nao_conformes">{{ d.kpis.verificacoes_nao_conformes }} verificação(ões) não conforme(s)</template>
							<template v-if="d.kpis.verificacoes_nao_conformes && d.kpis.verificacoes_atrasadas"> · </template>
							<template v-if="d.kpis.verificacoes_atrasadas">{{ d.kpis.verificacoes_atrasadas }} atrasada(s)</template>
						</p>
						<p class="text-sm text-slate-500">Verificações intermediárias entre calibrações.</p>
					</div>
					<ArrowRight class="size-4 text-slate-400 transition group-hover:translate-x-0.5" />
				</RouterLink>
				<RouterLink
					v-if="d.kpis.orcamentos_pendentes"
					to="/ordens?aba=aprovacao"
					class="card group flex items-center gap-4 p-4 transition hover:shadow-pop"
				>
					<span class="grid size-10 place-items-center rounded-xl bg-amber-50 text-amber-600"><ReceiptText class="size-5" /></span>
					<div class="flex-1">
						<p class="font-medium text-slate-900">{{ d.kpis.orcamentos_pendentes }} orçamento(s) aguardando sua aprovação</p>
						<p class="text-sm text-slate-500">O serviço só começa depois da sua resposta.</p>
					</div>
					<ArrowRight class="size-4 text-slate-400 transition group-hover:translate-x-0.5" />
				</RouterLink>
				<RouterLink
					v-if="d.kpis.analises_pendentes"
					to="/certificados?aba=pendentes"
					class="card group flex items-center gap-4 p-4 transition hover:shadow-pop"
				>
					<span class="grid size-10 place-items-center rounded-xl bg-brand-50 text-brand-600"><FileSearch class="size-5" /></span>
					<div class="flex-1">
						<p class="font-medium text-slate-900">{{ d.kpis.analises_pendentes }} certificado(s) aguardando análise crítica</p>
						<p class="text-sm text-slate-500">Registre a aprovação para manter a rastreabilidade da auditoria.</p>
					</div>
					<ArrowRight class="size-4 text-slate-400 transition group-hover:translate-x-0.5" />
				</RouterLink>
			</div>

			<!-- Ranking de distritos (clientes com controle por distritos) -->
			<section v-if="d.por_distrito.length > 1 && !store.distrito" class="card p-5">
				<div class="flex flex-wrap items-start justify-between gap-4">
					<div>
						<h2 class="font-semibold text-slate-900">Ranking dos distritos</h2>
						<p class="text-xs text-slate-500">% do parque em dia por distrito, do que mais precisa de atenção. Clique para ver só um distrito.</p>
					</div>
					<div class="flex gap-3 text-right">
						<div v-for="dist in d.por_distrito.slice(0, 1)" :key="dist.distrito" class="rounded-xl bg-rose-50 px-3 py-1.5">
							<p class="text-[11px] text-rose-600">Mais crítico</p>
							<p class="text-sm font-semibold text-rose-900">{{ dist.nome }} · {{ dist.em_dia_pct }}%</p>
						</div>
					</div>
				</div>
				<Grafico class="mt-3 cursor-pointer" :opcoes="grafDistritos" :altura="`${Math.max(160, d.por_distrito.length * 44 + 40)}px`" @click="abrirDistrito" />
			</section>

			<!-- Gráficos -->
			<div class="grid gap-4 lg:grid-cols-3">
				<section class="card p-5">
					<h2 class="font-semibold text-slate-900">Situação do parque</h2>
					<p class="text-xs text-slate-500">Distribuição por status de calibração</p>
					<div class="relative mt-2">
						<Grafico :opcoes="grafSituacao" altura="210px" />
						<div class="pointer-events-none absolute inset-0 grid place-items-center text-center">
							<div>
								<p class="text-3xl font-semibold text-slate-900 tabular-nums">{{ d.kpis.total_equipamentos }}</p>
								<p class="text-xs text-slate-500">equipamentos</p>
							</div>
						</div>
					</div>
					<ul class="mt-3 grid grid-cols-2 gap-2">
						<li v-for="(v, k) in d.situacoes" :key="k">
							<RouterLink :to="{ path: '/equipamentos', query: { situacao: k } }" class="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-slate-50">
								<span class="size-2.5 rounded-full" :style="{ background: COR_SITUACAO[k] }" />
								<span class="flex-1 truncate text-slate-600">{{ k }}</span>
								<span class="font-semibold text-slate-900 tabular-nums">{{ v }}</span>
							</RouterLink>
						</li>
					</ul>
				</section>

				<section class="card p-5 lg:col-span-2">
					<div class="flex items-start justify-between gap-4">
						<div>
							<h2 class="font-semibold text-slate-900">Agenda de vencimentos</h2>
							<p class="text-xs text-slate-500">Equipamentos que vencem em cada mês — planeje seus envios</p>
						</div>
						<RouterLink v-if="podeEditar()" to="/solicitar" class="btn-secondary py-1.5 text-xs">Agendar</RouterLink>
					</div>
					<Grafico class="mt-3" :opcoes="grafVencimentos" altura="270px" />
				</section>
			</div>

			<div class="grid gap-4 lg:grid-cols-3">
				<section class="card p-5 lg:col-span-2">
					<h2 class="font-semibold text-slate-900">Resultados das calibrações</h2>
					<p class="text-xs text-slate-500">Últimos 12 meses · aprovados x reprovados na análise crítica</p>
					<Grafico class="mt-3" :opcoes="grafResultados" altura="250px" />
				</section>
				<section class="card p-5">
					<h2 class="font-semibold text-slate-900">Por grandeza</h2>
					<p class="text-xs text-slate-500">Composição do parque</p>
					<Grafico class="mt-3" :opcoes="grafGrandeza" altura="250px" />
				</section>
			</div>

			<!-- Listas -->
			<div class="grid gap-4 lg:grid-cols-5">
				<section class="card overflow-hidden lg:col-span-3">
					<div class="flex items-center justify-between px-5 pt-5 pb-3">
						<div>
							<h2 class="font-semibold text-slate-900">Atenção nos vencimentos</h2>
							<p class="text-xs text-slate-500">Vencidos e a vencer, do mais urgente</p>
						</div>
						<RouterLink to="/equipamentos" class="text-sm font-medium text-brand-600 hover:text-brand-700">Ver todos</RouterLink>
					</div>
					<div v-if="!d.proximos_vencimentos.length" class="flex items-center gap-3 px-5 pb-6 text-sm text-emerald-700">
						<ShieldCheck class="size-5" /> Tudo em dia. Nenhum equipamento vencido ou a vencer.
					</div>
					<ul v-else class="divide-y divide-slate-100">
						<li v-for="e in d.proximos_vencimentos" :key="e.id">
							<RouterLink :to="`/equipamentos/${e.id}`" class="flex items-center gap-4 px-5 py-3 hover:bg-slate-50">
								<div class="min-w-0 flex-1">
									<p class="truncate text-sm font-medium text-slate-900">{{ e.tag }} <span class="font-normal text-slate-500">· {{ e.descricao }}</span></p>
									<p class="truncate text-xs text-slate-500">{{ e.localizacao || "Sem localização" }}</p>
								</div>
								<div class="text-right">
									<p class="text-sm text-slate-700 tabular-nums">{{ data(e.proxima_calibracao) }}</p>
									<p class="text-xs" :class="e.situacao === 'Vencido' ? 'text-rose-600' : 'text-amber-600'">{{ relativo(e.proxima_calibracao) }}</p>
								</div>
								<Etiqueta :valor="e.situacao" class="hidden sm:inline-flex" />
							</RouterLink>
						</li>
					</ul>
				</section>

				<section class="card overflow-hidden lg:col-span-2">
					<div class="flex items-center justify-between px-5 pt-5 pb-3">
						<div>
							<h2 class="font-semibold text-slate-900">Ordens recentes</h2>
							<p class="text-xs text-slate-500">Acompanhe cada etapa</p>
						</div>
						<RouterLink to="/ordens" class="text-sm font-medium text-brand-600 hover:text-brand-700">Ver todas</RouterLink>
					</div>
					<ul class="divide-y divide-slate-100">
						<li v-for="o in d.ordens_recentes" :key="o.id">
							<RouterLink :to="`/ordens/${o.id}`" class="block space-y-2.5 px-5 py-3.5 hover:bg-slate-50">
								<div class="flex items-center justify-between gap-3">
									<p class="text-sm font-medium text-slate-900">{{ o.id }}</p>
									<Etiqueta :valor="o.status" />
								</div>
								<LinhaEtapas :etapas="o.etapas" :atual="o.etapa_atual" compacta />
								<p class="text-xs text-slate-500">{{ o.tipo }} · {{ o.qtd_itens }} item(ns) · {{ data(o.data_solicitacao) }}</p>
							</RouterLink>
						</li>
					</ul>
				</section>
			</div>
		</template>
	</div>
</template>
