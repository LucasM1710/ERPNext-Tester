<script setup>
import { CircleAlert, Clock, Copy, ExternalLink, Gauge, Repeat, RefreshCw, Smile, Star, Target, Timer, Tv, Zap } from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"
import { api } from "@/api"
import Avatar from "@/components/Avatar.vue"
import Esqueleto from "@/components/Esqueleto.vue"
import Grafico from "@/components/Grafico.vue"
import Modal from "@/components/Modal.vue"
import { baseGrafico, COR, COR_PRIORIDADE } from "@/cores"
import { horas } from "@/format"
import { store, toast } from "@/store"

const dias = ref(30)

// Modo TV: link secreto, sem login
const tv = ref(null)
async function abrirTv() {
	tv.value = await api("tv.link")
}
async function acaoTv(metodo, msg) {
	if (metodo === "tv.gerar_link" && tv.value?.url && !confirm("Gerar um novo link? A TV com o link atual vai parar de funcionar até receber o novo.")) return
	tv.value = await api(metodo, {}, { post: true })
	toast(msg)
}
async function copiarTv() {
	try {
		await navigator.clipboard.writeText(tv.value.url)
		toast("Link copiado.")
	} catch {
		toast("Não foi possível copiar: selecione o link e copie manualmente.", "erro")
	}
}
const d = ref(null)
async function carregar() {
	d.value = null
	d.value = await api("painel", { dias: dias.value })
}
onMounted(carregar)
watch(dias, carregar)

const g = computed(() => baseGrafico(store.escuro))
const pct = (v) => (v === null || v === undefined ? "—" : `${String(v).replace(".", ",")}%`)

// KPIs com meta: verde/âmbar/vermelho conforme a referência de mercado para equipes pequenas
const kpis = computed(() => {
	const k = d.value.kpis
	const nivel = (v, bom, ok, maiorMelhor = true) =>
		v === null || v === undefined ? "neutro" : maiorMelhor ? (v >= bom ? "bom" : v >= ok ? "ok" : "ruim") : v <= bom ? "bom" : v <= ok ? "ok" : "ruim"
	return [
		{ titulo: "SLA de 1ª resposta", valor: pct(k.sla_resposta_pct), meta: "meta ≥ 90%", nivel: nivel(k.sla_resposta_pct, 90, 80), icone: Zap },
		{ titulo: "SLA de resolução", valor: pct(k.sla_resolucao_pct), meta: "meta ≥ 85%", nivel: nivel(k.sla_resolucao_pct, 85, 75), icone: Target },
		{ titulo: "Tempo médio de 1ª resposta", valor: horas(k.tempo_primeira_resposta_h), meta: "horas úteis", nivel: nivel(k.tempo_primeira_resposta_h, 2, 4, false), icone: Timer },
		{ titulo: "Tempo médio de resolução", valor: horas(k.mttr_h), meta: "horas úteis (MTTR)", nivel: nivel(k.mttr_h, 8, 16, false), icone: Clock },
		{ titulo: "Satisfação (CSAT)", valor: k.csat ? `${String(k.csat).replace(".", ",")} ★` : "—", meta: `${pct(k.csat_satisfeitos_pct)} satisfeitos · ${pct(k.taxa_avaliacao_pct)} avaliaram`, nivel: nivel(k.csat, 4.3, 3.8), icone: Smile },
		{ titulo: "Resolvidos no 1º contato", valor: pct(k.fcr_pct), meta: "meta ≥ 70% (FCR)", nivel: nivel(k.fcr_pct, 70, 55), icone: Gauge },
		{ titulo: "Reabertos", valor: pct(k.reabertos_pct), meta: "meta ≤ 5%", nivel: nivel(k.reabertos_pct, 5, 10, false), icone: Repeat },
		{ titulo: "Criados / resolvidos", valor: `${k.criados} / ${k.resolvidos}`, meta: `no período de ${d.value.dias} dias`, nivel: "neutro", icone: Star },
	]
})
const COR_NIVEL = {
	bom: "text-emerald-600 dark:text-emerald-400",
	ok: "text-amber-600 dark:text-amber-400",
	ruim: "text-rose-600 dark:text-rose-400",
	neutro: "text-tinta",
}

const grafSerie = computed(() => {
	const s = d.value.serie
	const area = (cor) => ({ color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: cor + "55" }, { offset: 1, color: cor + "00" }] } })
	return {
		grid: { left: 8, right: 12, top: 36, bottom: 4, containLabel: true },
		legend: { top: 0, right: 0, icon: "roundRect", itemWidth: 10, itemHeight: 10, textStyle: { color: g.value.texto, fontSize: 12 } },
		tooltip: { ...g.value.tooltip, trigger: "axis" },
		xAxis: { type: "category", data: s.dias.map((x) => x.slice(8, 10) + "/" + x.slice(5, 7)), boundaryGap: false, ...g.value.eixo, splitLine: { show: false } },
		yAxis: { type: "value", minInterval: 1, ...g.value.eixo },
		series: [
			{ name: "Abertos", type: "line", smooth: 0.35, symbol: "none", data: s.criados, lineStyle: { width: 2.5, color: COR.marca }, itemStyle: { color: COR.marca }, areaStyle: area(COR.marca) },
			{ name: "Resolvidos", type: "line", smooth: 0.35, symbol: "none", data: s.resolvidos, lineStyle: { width: 2.5, color: COR.verde }, itemStyle: { color: COR.verde }, areaStyle: area(COR.verde) },
		],
	}
})

const grafCategoria = computed(() => {
	const itens = [...d.value.por_categoria].slice(0, 8).reverse()
	return {
		grid: { left: 4, right: 30, top: 4, bottom: 4, containLabel: true },
		tooltip: { ...g.value.tooltip, trigger: "item", formatter: "{b}: <b>{c}</b>" },
		xAxis: { type: "value", show: false },
		yAxis: { type: "category", data: itens.map((i) => i[0]), ...g.value.eixo },
		series: [
			{
				type: "bar",
				data: itens.map((i) => i[1]),
				barWidth: 14,
				itemStyle: { color: COR.marca, borderRadius: 7 },
				showBackground: true,
				backgroundStyle: { color: store.escuro ? "#1c2130" : "#f1f3f9", borderRadius: 7 },
				label: { show: true, position: "right", color: g.value.texto, fontSize: 11 },
			},
		],
	}
})

const grafPrioridade = computed(() => {
	const p = d.value.por_prioridade
	return {
		grid: { left: 4, right: 4, top: 20, bottom: 4, containLabel: true },
		tooltip: { ...g.value.tooltip, trigger: "item", formatter: "{b}: <b>{c}</b> em aberto" },
		xAxis: { type: "category", data: Object.keys(p), ...g.value.eixo, splitLine: { show: false } },
		yAxis: { type: "value", minInterval: 1, ...g.value.eixo },
		series: [
			{
				type: "bar",
				barMaxWidth: 34,
				data: Object.entries(p).map(([k, v]) => ({ value: v, itemStyle: { color: COR_PRIORIDADE[k], borderRadius: [8, 8, 2, 2] } })),
				label: { show: true, position: "top", color: g.value.texto, fontSize: 11 },
			},
		],
	}
})

const grafIdade = computed(() => {
	const f = d.value.idade_fila
	const cores = [COR.verde, COR.marca, COR.ambar, COR.laranja, COR.vermelho]
	return {
		grid: { left: 4, right: 4, top: 20, bottom: 4, containLabel: true },
		tooltip: { ...g.value.tooltip, trigger: "item", formatter: "{b}: <b>{c}</b> chamado(s) em aberto" },
		xAxis: { type: "category", data: Object.keys(f), ...g.value.eixo, splitLine: { show: false } },
		yAxis: { type: "value", minInterval: 1, ...g.value.eixo },
		series: [
			{
				type: "bar",
				barMaxWidth: 34,
				data: Object.values(f).map((v, i) => ({ value: v, itemStyle: { color: cores[i], borderRadius: [8, 8, 2, 2] } })),
				label: { show: true, position: "top", color: g.value.texto, fontSize: 11 },
			},
		],
	}
})

const grafCsat = computed(() => {
	const c = d.value.csat_distribuicao
	const cores = [COR.vermelho, COR.laranja, COR.ambar, "#84cc16", COR.verde]
	return {
		grid: { left: 4, right: 4, top: 20, bottom: 4, containLabel: true },
		tooltip: { ...g.value.tooltip, trigger: "item", formatter: "{b}: <b>{c}</b> avaliação(ões)" },
		xAxis: { type: "category", data: ["1★", "2★", "3★", "4★", "5★"], ...g.value.eixo, splitLine: { show: false } },
		yAxis: { type: "value", minInterval: 1, ...g.value.eixo },
		series: [
			{
				type: "bar",
				barMaxWidth: 34,
				data: [1, 2, 3, 4, 5].map((n, i) => ({ value: c[n] || 0, itemStyle: { color: cores[i], borderRadius: [8, 8, 2, 2] } })),
				label: { show: true, position: "top", color: g.value.texto, fontSize: 11 },
			},
		],
	}
})
</script>

<template>
	<div class="space-y-6">
		<div class="flex flex-wrap items-end justify-between gap-4">
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-tinta">Indicadores da TI</h1>
				<p class="mt-1 text-sm text-suave">Prazos contados em horas úteis, conforme o expediente configurado.</p>
			</div>
			<div class="flex flex-wrap items-center gap-2">
			<button class="btn-secundario" @click="abrirTv"><Tv class="size-4" /> Modo TV</button>
			<nav class="flex gap-1 rounded-xl bg-realce p-1">
				<button
					v-for="op in [7, 30, 90]"
					:key="op"
					class="rounded-lg px-3.5 py-1.5 text-sm font-medium transition"
					:class="dias === op ? 'bg-superficie text-tinta shadow-sm' : 'text-suave hover:text-tinta'"
					@click="dias = op"
				>
					{{ op }} dias
				</button>
			</nav>
			</div>
		</div>

		<template v-if="!d">
			<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><div v-for="i in 8" :key="i" class="card p-5"><Esqueleto :linhas="3" /></div></div>
		</template>

		<template v-else>
			<!-- Situação agora -->
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
				<RouterLink to="/fila" class="card p-4 transition hover:shadow-pop"><p class="text-xs text-suave">Abertos agora</p><p class="mt-1 text-2xl font-semibold text-tinta tabular-nums">{{ d.kpis.abertos }}</p></RouterLink>
				<div class="card p-4"><p class="text-xs text-suave">Sem responsável</p><p class="mt-1 text-2xl font-semibold tabular-nums" :class="d.kpis.sem_responsavel ? 'text-amber-600 dark:text-amber-400' : 'text-tinta'">{{ d.kpis.sem_responsavel }}</p></div>
				<div class="card p-4"><p class="text-xs text-suave">Em risco</p><p class="mt-1 text-2xl font-semibold tabular-nums" :class="d.kpis.em_risco ? 'text-amber-600 dark:text-amber-400' : 'text-tinta'">{{ d.kpis.em_risco }}</p></div>
				<div class="card p-4"><p class="flex items-center gap-1 text-xs text-suave"><CircleAlert class="size-3.5" /> Prazo vencido</p><p class="mt-1 text-2xl font-semibold tabular-nums" :class="d.kpis.violados ? 'text-rose-600 dark:text-rose-400' : 'text-tinta'">{{ d.kpis.violados }}</p></div>
				<div class="card p-4"><p class="text-xs text-suave">Aguardando colaborador</p><p class="mt-1 text-2xl font-semibold text-tinta tabular-nums">{{ d.kpis.aguardando_usuario }}</p></div>
			</div>

			<!-- KPIs do período -->
			<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
				<div v-for="k in kpis" :key="k.titulo" class="card p-5">
					<div class="flex items-start justify-between gap-2">
						<p class="text-sm font-medium text-suave">{{ k.titulo }}</p>
						<component :is="k.icone" class="size-4 text-suave" />
					</div>
					<p class="mt-3 text-3xl font-semibold tracking-tight tabular-nums" :class="COR_NIVEL[k.nivel]">{{ k.valor }}</p>
					<p class="mt-1 text-xs text-suave">{{ k.meta }}</p>
				</div>
			</div>

			<div class="grid gap-4 lg:grid-cols-3">
				<section class="card p-5 lg:col-span-2">
					<h2 class="font-semibold text-tinta">Volume de chamados</h2>
					<p class="text-xs text-suave">Abertos x resolvidos por dia. Abertos acima dos resolvidos por vários dias = fila crescendo.</p>
					<Grafico class="mt-3" :opcoes="grafSerie" altura="260px" />
				</section>
				<section class="card p-5">
					<h2 class="font-semibold text-tinta">Por categoria</h2>
					<p class="text-xs text-suave">Onde estão os problemas: ajuda a priorizar melhorias.</p>
					<Grafico class="mt-3" :opcoes="grafCategoria" altura="260px" />
				</section>
			</div>

			<div class="grid gap-4 lg:grid-cols-3">
				<section class="card p-5">
					<h2 class="font-semibold text-tinta">Em aberto por prioridade</h2>
					<Grafico class="mt-3" :opcoes="grafPrioridade" altura="220px" />
				</section>
				<section class="card p-5">
					<h2 class="font-semibold text-tinta">Avaliações</h2>
					<Grafico class="mt-3" :opcoes="grafCsat" altura="220px" />
				</section>
				<section class="card overflow-hidden lg:row-span-1">
					<h2 class="px-5 pt-5 font-semibold text-tinta">Por técnico</h2>
					<table class="mt-3 w-full">
						<thead class="border-y border-borda bg-realce/50">
							<tr><th class="th">Técnico</th><th class="th text-right">Abertos</th><th class="th text-right">Resolv.</th><th class="th text-right">MTTR</th><th class="th text-right">CSAT</th></tr>
						</thead>
						<tbody class="divide-y divide-borda tabular-nums">
							<tr v-for="t in d.por_tecnico" :key="t.id">
								<td class="td"><span class="flex items-center gap-2"><Avatar :nome="t.nome" tamanho="size-6" /><span class="text-tinta">{{ t.nome.split(" ")[0] }}</span></span></td>
								<td class="td text-right">{{ t.abertos }}</td>
								<td class="td text-right">{{ t.resolvidos }}</td>
								<td class="td text-right">{{ horas(t.mttr) }}</td>
								<td class="td text-right">{{ t.csat ? String(t.csat).replace(".", ",") + " ★" : "—" }}</td>
							</tr>
						</tbody>
					</table>
				</section>
			</div>

			<div class="grid gap-4 lg:grid-cols-3">
				<section class="card p-5">
					<h2 class="font-semibold text-tinta">Idade da fila</h2>
					<p class="text-xs text-suave">Há quanto tempo os chamados em aberto estão parados. Barras à direita crescendo = acúmulo escondido.</p>
					<Grafico class="mt-3" :opcoes="grafIdade" altura="220px" />
				</section>
				<section class="card overflow-hidden lg:col-span-2">
					<h2 class="px-5 pt-5 font-semibold text-tinta">Problemas recorrentes</h2>
					<p class="px-5 text-xs text-suave">Categorias mês a mês e equipamentos com 3+ chamados em 90 dias: atacar a causa reduz a fila de verdade.</p>
					<div class="mt-3 grid gap-4 p-5 pt-2 md:grid-cols-2">
						<table class="w-full text-sm">
							<thead><tr class="text-xs text-suave"><th class="py-1 text-left font-medium">Categoria</th><th v-for="m in d.recorrentes.meses" :key="m" class="py-1 text-right font-medium">{{ m.slice(5) }}/{{ m.slice(2, 4) }}</th></tr></thead>
							<tbody class="divide-y divide-borda tabular-nums">
								<tr v-for="c in d.recorrentes.categorias" :key="c.categoria">
									<td class="py-1.5 text-tinta">{{ c.categoria }}</td>
									<td v-for="(v, i) in c.por_mes" :key="i" class="py-1.5 text-right" :class="i === c.por_mes.length - 1 && v > c.por_mes[i - 1] ? 'font-semibold text-rose-600 dark:text-rose-400' : 'text-texto'">{{ v }}</td>
								</tr>
							</tbody>
						</table>
						<div>
							<p class="text-xs font-medium text-suave">Equipamentos que mais voltam</p>
							<ul v-if="d.recorrentes.equipamentos.length" class="mt-2 space-y-1.5">
								<li v-for="e in d.recorrentes.equipamentos" :key="e.id">
									<RouterLink :to="`/inventario/${e.id}`" class="flex items-center justify-between rounded-lg px-2 py-1 text-sm hover:bg-realce">
										<span class="font-medium text-tinta">{{ e.id }}</span><span class="text-rose-600 dark:text-rose-400">{{ e.chamados }} chamados</span>
									</RouterLink>
								</li>
							</ul>
							<p v-else class="mt-2 text-sm text-suave">Nenhum equipamento com chamados repetidos.</p>
						</div>
					</div>
				</section>
			</div>
		</template>

		<Modal v-if="tv" titulo="Modo TV" subtitulo="Painel em tela cheia para a TV da TI — abre sem login, só com este link." largura="max-w-xl" @fechar="tv = null">
			<template v-if="tv.url">
				<label class="rotulo">Link da TV</label>
				<div class="flex gap-2">
					<input :value="tv.url" readonly class="campo font-mono text-xs" @focus="$event.target.select()" />
					<button class="btn-secundario" title="Copiar" @click="copiarTv"><Copy class="size-4" /></button>
					<a :href="tv.url" target="_blank" class="btn-secundario" title="Abrir"><ExternalLink class="size-4" /></a>
				</div>
				<ul class="mt-4 space-y-1.5 text-sm text-texto">
					<li>• Abra o link no navegador da TV (Smart TV, Chromecast/Fire TV ou mini PC) e clique duas vezes para tela cheia.</li>
					<li>• Slides a cada {{ tv.segundos_slide }} s; dados atualizados a cada minuto.</li>
					<li>• {{ tv.mostrar_nomes ? "Mostrando nomes dos colaboradores." : "Sem nomes de colaboradores (assunto e departamento apenas)." }} Ajuste em Configurações.</li>
					<li>• Quem tiver o link vê o painel: trate como senha. Gerar um novo invalida o anterior.</li>
				</ul>
			</template>
			<p v-else class="text-sm text-texto">O painel da TV está desativado. Gere um link para começar.</p>
			<template #rodape>
				<button v-if="tv.url" class="btn-fantasma text-rose-600" @click="acaoTv('tv.desativar_link', 'Link da TV desativado.')">Desativar</button>
				<button class="btn-primario" @click="acaoTv('tv.gerar_link', 'Novo link gerado.')"><RefreshCw class="size-4" /> {{ tv.url ? "Gerar novo link" : "Gerar link" }}</button>
			</template>
		</Modal>
	</div>
</template>
