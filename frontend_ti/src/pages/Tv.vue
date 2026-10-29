<script setup>
import { AlertTriangle, CheckCircle2, Clock, Maximize, PackageX, ShieldAlert, Wifi, WifiOff } from "lucide-vue-next"
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import Grafico from "@/components/Grafico.vue"
import { baseGrafico, COR, COR_PRIORIDADE } from "@/cores"
import { prazo } from "@/format"

// Painel para TV: sem login (link com ?chave=), sempre escuro, letras grandes, slides alternados.
const chave = new URLSearchParams(location.search).get("chave")
const d = ref(null)
const erro = ref(null)
const offline = ref(false)
const atualizadoEm = ref(null)
const agora = ref(new Date())
const slide = ref(0)
const progresso = ref(0)
const cursorVisivel = ref(true)
const SLIDES = ["Atendimento agora", "Desempenho do mês", "Patrimônio"]

async function carregar() {
	try {
		const r = await fetch("/api/method/solucoes.central_ti.api.tv.dados?" + new URLSearchParams({ chave: chave || "" }), { headers: { Accept: "application/json" } })
		const j = await r.json().catch(() => ({}))
		if (!r.ok) {
			if (r.status === 403) erro.value = (j.exception || "").split(":").slice(1).join(":").trim() || "Link inválido."
			throw new Error()
		}
		d.value = j.message
		atualizadoEm.value = new Date()
		offline.value = false
	} catch {
		offline.value = true // mantém os últimos dados na tela
	}
}

let relogios = []
let wakeLock = null
let cursorTimer
function mostrarCursor() {
	cursorVisivel.value = true
	clearTimeout(cursorTimer)
	cursorTimer = setTimeout(() => (cursorVisivel.value = false), 3000)
}
function telaCheia() {
	document.documentElement.requestFullscreen?.().catch(() => {})
}
function tecla(e) {
	if (e.key === "ArrowRight") irPara(slide.value + 1)
	if (e.key === "ArrowLeft") irPara(slide.value - 1)
	if (e.key === "f") telaCheia()
}
function irPara(n) {
	slide.value = (n + SLIDES.length) % SLIDES.length
	progresso.value = 0
}
onMounted(async () => {
	document.documentElement.classList.add("dark")
	await carregar()
	const passo = 250
	relogios = [
		setInterval(carregar, 60000),
		setInterval(() => (agora.value = new Date()), 1000),
		setInterval(() => {
			progresso.value += passo / (1000 * (d.value?.segundos_slide || 20))
			if (progresso.value >= 1) irPara(slide.value + 1)
		}, passo),
	]
	try {
		wakeLock = await navigator.wakeLock?.request("screen") // mantém a TV/monitor sem apagar
	} catch {
		// navegador sem suporte: tudo bem
	}
	document.addEventListener("keydown", tecla)
	document.addEventListener("mousemove", mostrarCursor)
	mostrarCursor()
})
onBeforeUnmount(() => {
	relogios.forEach(clearInterval)
	wakeLock?.release?.()
	document.removeEventListener("keydown", tecla)
	document.removeEventListener("mousemove", mostrarCursor)
})

const hora = computed(() => agora.value.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }))
const dataHoje = computed(() => agora.value.toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" }))
const segundosDesde = computed(() => (atualizadoEm.value ? Math.round((agora.value - atualizadoEm.value) / 1000) : null))
const pct = (v) => (v === null || v === undefined ? "—" : `${v}%`)
const g = baseGrafico(true)

function nivel(v, bom, ok) {
	return v === null || v === undefined ? "text-slate-400" : v >= bom ? "text-emerald-400" : v >= ok ? "text-amber-400" : "text-rose-400"
}

const kpisAgora = computed(() => {
	const a = d.value.agora
	return [
		{ titulo: "Em aberto", valor: a.abertos, cor: "text-white", sub: `${a.aguardando_usuario} aguardando colaborador` },
		{ titulo: "Sem responsável", valor: a.sem_responsavel, cor: a.sem_responsavel ? "text-amber-400" : "text-emerald-400", sub: "ninguém assumiu" },
		{ titulo: "Em risco", valor: a.em_risco, cor: a.em_risco ? "text-amber-400" : "text-emerald-400", sub: "prazo perto de vencer" },
		{ titulo: "Prazo vencido", valor: a.vencidos, cor: a.vencidos ? "text-rose-400" : "text-emerald-400", sub: "SLA violado", pulsar: a.vencidos > 0 },
	]
})

function medidor(valor, cor, sufixo = "%", max = 100) {
	return {
		series: [
			{
				type: "gauge",
				startAngle: 210,
				endAngle: -30,
				min: 0,
				max,
				radius: "100%",
				pointer: { show: false },
				progress: { show: true, roundCap: true, width: 18, itemStyle: { color: cor } },
				axisLine: { lineStyle: { width: 18, color: [[1, "#1c2130"]] } },
				splitLine: { show: false },
				axisTick: { show: false },
				axisLabel: { show: false },
				detail: { valueAnimation: true, offsetCenter: [0, "5%"], fontSize: 56, fontWeight: 700, color: "#f8fafc", fontFamily: "Inter", formatter: (v) => (valor === null ? "—" : `${String(v).replace(".", ",")}${sufixo}`) },
				data: [{ value: valor ?? 0 }],
			},
		],
	}
}
const corPct = (v, bom, ok) => (v === null ? COR.cinza : v >= bom ? COR.verde : v >= ok ? COR.ambar : COR.vermelho)

const grafSerie = computed(() => {
	const s = d.value.serie
	const area = (cor) => ({ color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: cor + "66" }, { offset: 1, color: cor + "00" }] } })
	return {
		grid: { left: 10, right: 20, top: 50, bottom: 10, containLabel: true },
		legend: { top: 0, right: 0, icon: "roundRect", itemWidth: 14, itemHeight: 14, textStyle: { color: "#cbd5e1", fontSize: 18 } },
		xAxis: { type: "category", boundaryGap: false, data: s.dias.map((x) => x.slice(8, 10) + "/" + x.slice(5, 7)), ...g.eixo, axisLabel: { ...g.eixo.axisLabel, fontSize: 15 }, splitLine: { show: false } },
		yAxis: { type: "value", minInterval: 1, ...g.eixo, axisLabel: { ...g.eixo.axisLabel, fontSize: 15 } },
		series: [
			{ name: "Abertos", type: "line", smooth: 0.35, symbol: "none", data: s.abertos, lineStyle: { width: 4, color: COR.marca }, itemStyle: { color: COR.marca }, areaStyle: area(COR.marca) },
			{ name: "Resolvidos", type: "line", smooth: 0.35, symbol: "none", data: s.resolvidos, lineStyle: { width: 4, color: COR.verde }, itemStyle: { color: COR.verde }, areaStyle: area(COR.verde) },
		],
	}
})
</script>

<template>
	<div class="flex h-screen flex-col overflow-hidden bg-[#07090f] px-10 py-7 text-slate-100 select-none" :class="!cursorVisivel && 'cursor-none'" @dblclick="telaCheia">
		<!-- Link inválido -->
		<div v-if="erro && !d" class="m-auto max-w-2xl text-center">
			<ShieldAlert class="mx-auto size-16 text-rose-400" />
			<p class="mt-6 text-3xl font-semibold">Painel da TV indisponível</p>
			<p class="mt-3 text-xl text-slate-400">{{ erro }}</p>
		</div>
		<div v-else-if="!d" class="m-auto size-14 animate-spin rounded-full border-4 border-indigo-500/20 border-t-indigo-400" />

		<template v-else>
			<!-- Cabeçalho -->
			<header class="flex items-center gap-6">
				<div>
					<p class="text-sm font-semibold tracking-[0.3em] text-indigo-300 uppercase">{{ d.titulo }}</p>
					<p class="text-4xl font-semibold tracking-tight">{{ SLIDES[slide] }}</p>
				</div>
				<div class="ml-auto flex items-center gap-8">
					<p class="flex items-center gap-2 text-lg" :class="offline ? 'text-amber-400' : 'text-slate-500'">
						<WifiOff v-if="offline" class="size-5" /><Wifi v-else class="size-5" />
						{{ offline ? `sem conexão · dados de ${atualizadoEm?.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}` : segundosDesde < 5 ? "atualizado agora" : `atualizado há ${segundosDesde}s` }}
					</p>
					<div class="text-right">
						<p class="text-5xl font-semibold tabular-nums">{{ hora }}</p>
						<p class="text-lg text-slate-400 first-letter:uppercase">{{ dataHoje }}</p>
					</div>
					<button v-if="cursorVisivel" class="rounded-xl bg-white/5 p-3 text-slate-400 hover:bg-white/10" title="Tela cheia (F)" @click="telaCheia"><Maximize class="size-6" /></button>
				</div>
			</header>

			<main class="relative mt-7 min-h-0 flex-1">
				<Transition name="fade" mode="out-in">
					<!-- SLIDE 1: atendimento agora -->
					<section v-if="slide === 0" key="s0" class="grid h-full grid-cols-3 grid-rows-[auto_1fr] gap-6">
						<div class="col-span-3 grid grid-cols-4 gap-6">
							<div v-for="k in kpisAgora" :key="k.titulo" class="rounded-3xl border border-white/5 bg-white/[0.03] p-6" :class="k.pulsar && 'animate-pulse border-rose-500/40 bg-rose-500/10'">
								<p class="text-xl text-slate-400">{{ k.titulo }}</p>
								<p class="mt-2 text-8xl leading-none font-bold tabular-nums" :class="k.cor">{{ k.valor }}</p>
								<p class="mt-3 text-base text-slate-500">{{ k.sub }}</p>
							</div>
						</div>
						<div class="col-span-2 flex min-h-0 flex-col rounded-3xl border border-white/5 bg-white/[0.03] p-6">
							<p class="flex items-center gap-2 text-xl font-semibold"><AlertTriangle class="size-6 text-amber-400" /> Atenção agora</p>
							<ul v-if="d.atencao.length" class="mt-4 flex-1 space-y-3 overflow-hidden">
								<li v-for="c in d.atencao" :key="c.id" class="flex items-center gap-4 rounded-2xl bg-white/[0.03] py-3 pr-5">
									<span class="h-14 w-2 shrink-0 rounded-r-full" :style="{ background: COR_PRIORIDADE[c.prioridade] }" />
									<div class="min-w-0 flex-1">
										<p class="truncate text-2xl font-medium">{{ c.assunto }}</p>
										<p class="truncate text-base text-slate-400">{{ c.id }} · {{ c.prioridade }} · {{ c.departamento || c.categoria }}<template v-if="c.solicitante"> · {{ c.solicitante }}</template></p>
									</div>
									<div class="text-right">
										<p class="text-xl font-semibold whitespace-nowrap" :class="c.sla === 'Violado' ? 'text-rose-400' : c.sla === 'Em Risco' ? 'text-amber-400' : 'text-slate-300'">{{ prazo(c.prazo) }}</p>
										<p class="text-base text-slate-500">{{ c.tecnico || "sem responsável" }}</p>
									</div>
								</li>
							</ul>
							<div v-else class="m-auto flex items-center gap-3 text-3xl text-emerald-400"><CheckCircle2 class="size-10" /> Nada urgente. Fila sob controle.</div>
						</div>
						<div class="flex flex-col gap-6">
							<div class="rounded-3xl border border-white/5 bg-white/[0.03] p-6">
								<p class="text-xl text-slate-400">Hoje</p>
								<div class="mt-3 grid grid-cols-2 gap-4">
									<div><p class="text-6xl font-bold text-indigo-300 tabular-nums">{{ d.hoje.abertos }}</p><p class="text-base text-slate-500">abertos</p></div>
									<div><p class="text-6xl font-bold text-emerald-400 tabular-nums">{{ d.hoje.resolvidos }}</p><p class="text-base text-slate-500">resolvidos</p></div>
								</div>
							</div>
							<div class="flex-1 rounded-3xl border border-white/5 bg-white/[0.03] p-6">
								<p class="text-xl text-slate-400">Equipe</p>
								<ul class="mt-4 space-y-4">
									<li v-for="t in d.tecnicos" :key="t.nome" class="flex items-center gap-4">
										<span class="grid size-12 place-items-center rounded-full bg-indigo-500/20 text-xl font-semibold text-indigo-200">{{ (t.nome || "?")[0] }}</span>
										<span class="flex-1 text-2xl">{{ t.nome }}</span>
										<span class="text-right"><span class="block text-3xl font-bold tabular-nums">{{ t.abertos }}</span><span class="text-sm text-slate-500">em aberto · {{ t.resolvidos_mes }} no mês</span></span>
									</li>
								</ul>
							</div>
						</div>
					</section>

					<!-- SLIDE 2: desempenho do mês -->
					<section v-else-if="slide === 1" key="s1" class="grid h-full grid-cols-4 grid-rows-[auto_1fr] gap-6">
						<div class="rounded-3xl border border-white/5 bg-white/[0.03] p-5 text-center">
							<p class="text-xl text-slate-400">SLA de 1ª resposta</p>
							<Grafico :opcoes="medidor(d.mes.sla_resposta_pct, corPct(d.mes.sla_resposta_pct, 90, 80))" altura="210px" />
							<p class="-mt-6 text-base text-slate-500">meta 90%</p>
						</div>
						<div class="rounded-3xl border border-white/5 bg-white/[0.03] p-5 text-center">
							<p class="text-xl text-slate-400">SLA de resolução</p>
							<Grafico :opcoes="medidor(d.mes.sla_resolucao_pct, corPct(d.mes.sla_resolucao_pct, 85, 75))" altura="210px" />
							<p class="-mt-6 text-base text-slate-500">meta 85%</p>
						</div>
						<div class="rounded-3xl border border-white/5 bg-white/[0.03] p-6 text-center">
							<p class="text-xl text-slate-400">Satisfação</p>
							<p class="mt-8 text-8xl font-bold tabular-nums" :class="nivel(d.mes.csat, 4.3, 3.8)">{{ d.mes.csat ? String(d.mes.csat).replace(".", ",") : "—" }}<span class="text-5xl"> ★</span></p>
							<p class="mt-4 text-xl text-slate-400">{{ pct(d.mes.csat_satisfeitos_pct) }} satisfeitos</p>
						</div>
						<div class="rounded-3xl border border-white/5 bg-white/[0.03] p-6 text-center">
							<p class="flex items-center justify-center gap-2 text-xl text-slate-400"><Clock class="size-5" /> Tempo médio para resolver</p>
							<p class="mt-8 text-8xl font-bold text-white tabular-nums">{{ d.mes.mttr_h !== null ? String(d.mes.mttr_h).replace(".", ",") : "—" }}<span class="text-4xl text-slate-400"> h</span></p>
							<p class="mt-4 text-xl text-slate-400">{{ d.mes.resolvidos }} resolvidos no mês · horas úteis</p>
						</div>
						<div class="col-span-4 rounded-3xl border border-white/5 bg-white/[0.03] p-6">
							<p class="text-xl text-slate-400">Abertos x resolvidos · últimos 14 dias</p>
							<Grafico :opcoes="grafSerie" altura="100%" class="h-[calc(100%-2rem)]" />
						</div>
					</section>

					<!-- SLIDE 3: patrimônio -->
					<section v-else key="s2" class="grid h-full grid-cols-3 gap-6">
						<div class="flex flex-col rounded-3xl border border-white/5 bg-white/[0.03] p-6">
							<p class="flex items-center gap-2 text-xl text-slate-400"><PackageX class="size-6" /> Estoque abaixo do mínimo</p>
							<ul v-if="d.patrimonio.estoque_baixo.length" class="mt-5 space-y-4">
								<li v-for="e in d.patrimonio.estoque_baixo" :key="e.item" class="rounded-2xl bg-rose-500/10 p-4">
									<p class="text-2xl font-medium">{{ e.item }}</p>
									<p class="text-lg text-rose-300">{{ e.quantidade }} em estoque · mínimo {{ e.minimo }}</p>
								</li>
							</ul>
							<p v-else class="m-auto flex items-center gap-3 text-2xl text-emerald-400"><CheckCircle2 class="size-8" /> Estoque em dia</p>
						</div>
						<div class="flex flex-col rounded-3xl border border-white/5 bg-white/[0.03] p-6">
							<p class="text-xl text-slate-400">Garantias vencendo (60 dias)</p>
							<p class="mt-3 text-8xl font-bold tabular-nums" :class="d.patrimonio.garantias_60d_total ? 'text-amber-400' : 'text-emerald-400'">{{ d.patrimonio.garantias_60d_total }}</p>
							<ul class="mt-4 space-y-2 text-xl">
								<li v-for="e in d.patrimonio.garantias_60d" :key="e.nome" class="flex justify-between gap-3 text-slate-300">
									<span>{{ e.nome }} <span class="text-slate-500">· {{ e.tipo }}</span></span><span class="text-slate-400">{{ e.ate.slice(8, 10) }}/{{ e.ate.slice(5, 7) }}</span>
								</li>
							</ul>
						</div>
						<div class="flex flex-col gap-6">
							<div class="rounded-3xl border border-white/5 bg-white/[0.03] p-6">
								<p class="text-xl text-slate-400">Vida útil vencida</p>
								<p class="mt-2 text-8xl font-bold tabular-nums" :class="d.patrimonio.vida_util_vencida ? 'text-rose-400' : 'text-emerald-400'">{{ d.patrimonio.vida_util_vencida }}</p>
								<p class="text-lg text-slate-500">de {{ d.patrimonio.equipamentos }} equipamentos ativos</p>
							</div>
							<div class="flex-1 rounded-3xl border border-white/5 bg-white/[0.03] p-6">
								<p class="text-xl text-slate-400">Renovação em {{ d.patrimonio.renovacao_proximo_ano.ano }}</p>
								<p class="mt-2 text-7xl font-bold text-violet-300 tabular-nums">{{ d.patrimonio.renovacao_proximo_ano.quantidade }}</p>
								<p class="text-lg text-slate-400">equipamentos · ~{{ Number(d.patrimonio.renovacao_proximo_ano.valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }) }}</p>
							</div>
						</div>
					</section>
				</Transition>
			</main>

			<!-- Rodapé: slides -->
			<footer class="mt-6 flex items-center gap-4">
				<button v-for="(s, i) in SLIDES" :key="s" class="relative h-2 flex-1 overflow-hidden rounded-full bg-white/10" @click="irPara(i)">
					<span class="absolute inset-y-0 left-0 rounded-full bg-indigo-400" :style="{ width: i < slide ? '100%' : i === slide ? progresso * 100 + '%' : '0%' }" />
				</button>
				<p class="text-base text-slate-500">{{ d.empresa }}</p>
			</footer>
		</template>
	</div>
</template>
