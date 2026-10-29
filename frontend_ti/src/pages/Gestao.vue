<script setup>
import { AlertTriangle, Boxes, CalendarClock, PackageX, ShieldOff, Target, UsersRound, Wallet, Wrench } from "lucide-vue-next"
import { computed, onMounted, ref } from "vue"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import Grafico from "@/components/Grafico.vue"
import IconeEquipamento from "@/components/IconeEquipamento.vue"
import { baseGrafico, COR } from "@/cores"
import { data } from "@/format"
import { store } from "@/store"

const d = ref(null)
onMounted(async () => (d.value = await api("inventario.gestao")))
const g = computed(() => baseGrafico(store.escuro))
const reais = (v, curto = false) =>
	curto && v >= 1000 ? `R$ ${(v / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mil` : Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 })

const kpis = computed(() => {
	const k = d.value.kpis
	return [
		{ titulo: "Equipamentos ativos", valor: k.equipamentos, texto: `${k.em_uso} em uso · ${k.em_estoque} em estoque`, icone: Boxes, para: "/inventario" },
		{ titulo: "Valor do parque", valor: reais(k.valor_parque, true), texto: "soma do valor de compra", icone: Wallet },
		{ titulo: "Idade média", valor: k.idade_media !== null ? `${String(k.idade_media).replace(".", ",")} anos` : "—", texto: "desde a compra", icone: CalendarClock },
		{ titulo: "Vida útil vencida", valor: k.vida_util_vencida, texto: "candidatos à troca", icone: AlertTriangle, alerta: k.vida_util_vencida > 0, para: "/inventario?alertas=1" },
		{ titulo: "Fora da garantia", valor: k.fora_garantia, texto: "sem cobertura do fabricante", icone: ShieldOff, alerta: false },
		{ titulo: "Manutenção (12 meses)", valor: reais(k.custo_manutencao_12m, true), texto: "upgrades e consertos", icone: Wrench },
		{ titulo: "Estoque abaixo do mínimo", valor: k.estoque_baixo, texto: "itens para comprar", icone: PackageX, alerta: k.estoque_baixo > 0, para: "/estoque" },
		custoColaborador.value,
	].filter(Boolean)
})

// custo de TI por colaborador no ano corrente (compras + manutenções ÷ colaboradores)
const custoColaborador = computed(() => {
	const c = d.value.custo_por_colaborador
	const atual = c.anos.at(-1)
	if (!c.colaboradores || !atual) return null
	const anterior = c.anos.length > 1 ? c.anos[0] : null
	return {
		titulo: `Custo de TI por colaborador (${atual.ano})`,
		valor: reais(atual.valor),
		texto: `${c.colaboradores} colaboradores (${c.origem})${anterior ? ` · ${anterior.ano}: ${reais(anterior.valor)}` : ""}`,
		icone: UsersRound,
	}
})

const grafOrcamento = computed(() => {
	const o = d.value.orcamento
	return {
		grid: { left: 8, right: 8, top: 36, bottom: 4, containLabel: true },
		legend: { top: 0, right: 0, icon: "roundRect", itemWidth: 10, itemHeight: 10, textStyle: { color: g.value.texto, fontSize: 12 } },
		tooltip: {
			...g.value.tooltip,
			trigger: "axis",
			formatter: (p) => {
				const x = o[p[0].dataIndex]
				return `<b>${x.ano}</b><br/>Orçado: ${reais(x.orcado)}<br/>Realizado: ${reais(x.realizado)}${x.uso_pct !== null ? ` (${String(x.uso_pct).replace(".", ",")}%)` : ""}`
			},
		},
		xAxis: { type: "category", data: o.map((x) => String(x.ano)), ...g.value.eixo, splitLine: { show: false } },
		yAxis: { type: "value", ...g.value.eixo, axisLabel: { ...g.value.eixo.axisLabel, formatter: (v) => (v >= 1000 ? `${v / 1000}k` : v) } },
		series: [
			{ name: "Orçado", type: "bar", barMaxWidth: 34, data: o.map((x) => x.orcado), itemStyle: { color: store.escuro ? "#334155" : "#cbd5e1", borderRadius: [6, 6, 2, 2] } },
			{
				name: "Realizado",
				type: "bar",
				barMaxWidth: 34,
				data: o.map((x) => ({ value: x.realizado, itemStyle: { color: x.realizado > x.orcado ? COR.vermelho : COR.marca, borderRadius: [6, 6, 2, 2] } })),
				label: { show: true, position: "top", color: g.value.texto, fontSize: 11, formatter: (p) => (o[p.dataIndex].uso_pct !== null ? `${String(o[p.dataIndex].uso_pct).replace(".", ",")}%` : "") },
			},
		],
	}
})

const grafGastos = computed(() => {
	const gs = d.value.gastos_por_ano
	return {
		grid: { left: 8, right: 8, top: 36, bottom: 4, containLabel: true },
		legend: { top: 0, right: 0, icon: "roundRect", itemWidth: 10, itemHeight: 10, textStyle: { color: g.value.texto, fontSize: 12 } },
		tooltip: { ...g.value.tooltip, trigger: "axis", valueFormatter: (v) => reais(v) },
		xAxis: { type: "category", data: gs.map((x) => String(x.ano)), ...g.value.eixo, splitLine: { show: false } },
		yAxis: { type: "value", ...g.value.eixo, axisLabel: { ...g.value.eixo.axisLabel, formatter: (v) => (v >= 1000 ? `${v / 1000}k` : v) } },
		series: [
			{ name: "Compras", type: "bar", stack: "t", barMaxWidth: 40, data: gs.map((x) => Math.round(x.compras)), itemStyle: { color: COR.marca } },
			{ name: "Manutenções", type: "bar", stack: "t", barMaxWidth: 40, data: gs.map((x) => Math.round(x.manutencoes)), itemStyle: { color: COR.ambar, borderRadius: [6, 6, 0, 0] } },
		],
	}
})

const grafPlano = computed(() => {
	const p = d.value.plano_renovacao
	return {
		grid: { left: 8, right: 8, top: 24, bottom: 4, containLabel: true },
		tooltip: { ...g.value.tooltip, trigger: "item", formatter: (x) => `${x.name}: <b>${p[x.dataIndex].quantidade}</b> equipamento(s)<br/>${Object.entries(p[x.dataIndex].por_tipo).map(([t, n]) => `${n} ${t}`).join(", ")}<br/>estimativa ${reais(p[x.dataIndex].valor)}` },
		xAxis: { type: "category", data: p.map((x) => x.ano), ...g.value.eixo, splitLine: { show: false } },
		yAxis: { type: "value", ...g.value.eixo, axisLabel: { ...g.value.eixo.axisLabel, formatter: (v) => (v >= 1000 ? `${v / 1000}k` : v) } },
		series: [
			{
				type: "bar",
				barMaxWidth: 46,
				data: p.map((x) => ({ value: Math.round(x.valor), itemStyle: { color: x.ano === "Já vencidos" ? COR.vermelho : COR.violeta, borderRadius: [8, 8, 2, 2] } })),
				label: { show: true, position: "top", color: g.value.texto, fontSize: 11, formatter: (x) => `${p[x.dataIndex].quantidade} un.` },
			},
		],
	}
})

const grafGrupo = computed(() => {
	const cores = [COR.marca, COR.verde, COR.ambar, COR.violeta, COR.azul, COR.cinza]
	return {
		tooltip: { ...g.value.tooltip, trigger: "item", formatter: "{b}: <b>{c}</b> ({d}%)" },
		legend: { bottom: 0, icon: "circle", itemWidth: 8, textStyle: { color: g.value.texto, fontSize: 11 } },
		series: [
			{
				type: "pie",
				radius: ["55%", "78%"],
				center: ["50%", "42%"],
				padAngle: 2,
				itemStyle: { borderRadius: 6 },
				label: { show: false },
				data: d.value.por_grupo.map(([n, v], i) => ({ name: n, value: v, itemStyle: { color: cores[i % cores.length] } })),
			},
		],
	}
})
</script>

<template>
	<div class="space-y-6">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight text-tinta">Visão do gestor de TI</h1>
			<p class="mt-1 text-sm text-suave">O ciclo de vida do parque: o que temos, quanto custa, o que precisa ser trocado e quando.</p>
		</div>

		<div v-if="!d" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><div v-for="i in 8" :key="i" class="card p-5"><Esqueleto :linhas="3" /></div></div>
		<template v-else>
			<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
				<component :is="k.para ? 'RouterLink' : 'div'" v-for="k in kpis" :key="k.titulo" :to="k.para" class="card p-5" :class="k.para && 'transition hover:shadow-pop'">
					<div class="flex items-start justify-between"><p class="text-sm font-medium text-suave">{{ k.titulo }}</p><component :is="k.icone" class="size-4" :class="k.alerta ? 'text-rose-500' : 'text-suave'" /></div>
					<p class="mt-3 text-3xl font-semibold tracking-tight tabular-nums" :class="k.alerta ? 'text-rose-600 dark:text-rose-400' : 'text-tinta'">{{ k.valor }}</p>
					<p class="mt-1 text-xs text-suave">{{ k.texto }}</p>
				</component>
			</div>

			<div class="grid gap-4 lg:grid-cols-3">
				<section class="card p-5 lg:col-span-2">
					<h2 class="font-semibold text-tinta">Plano de renovação</h2>
					<p class="text-xs text-suave">Equipamentos que atingem a vida útil em cada ano e o valor estimado de reposição (preço pago). Use para montar o orçamento.</p>
					<Grafico class="mt-3" :opcoes="grafPlano" altura="250px" />
				</section>
				<section class="card p-5">
					<h2 class="font-semibold text-tinta">Composição do parque</h2>
					<Grafico class="mt-3" :opcoes="grafGrupo" altura="250px" />
				</section>
			</div>

			<div class="grid gap-4 lg:grid-cols-3">
				<section class="card p-5 lg:col-span-2">
					<h2 class="font-semibold text-tinta">Gastos de TI por ano</h2>
					<p class="text-xs text-suave">Compras (das Notas de Compra do ERP) + manutenções registradas.</p>
					<Grafico class="mt-3" :opcoes="grafGastos" altura="250px" />
				</section>
				<section class="card p-5 lg:col-span-2">
					<div class="flex flex-wrap items-start justify-between gap-2">
						<div>
							<h2 class="flex items-center gap-2 font-semibold text-tinta"><Target class="size-4 text-marca-600 dark:text-marca-300" /> Orçado x realizado</h2>
							<p class="text-xs text-suave">Barra vermelha = ano acima do orçamento. O percentual mostra quanto do orçamento já foi usado.</p>
						</div>
						<a href="/app/configuracao-central-ti" class="btn-secundario py-1.5 text-xs">Definir orçamento</a>
					</div>
					<Grafico v-if="d.orcamento.length" class="mt-3" :opcoes="grafOrcamento" altura="230px" />
					<p v-else class="mt-4 rounded-xl bg-realce p-4 text-sm text-texto">
						Cadastre o orçamento anual de TI em <b>Configurações → Orçamento de TI</b> (valores de compras e manutenções por ano) para comparar com o que foi realmente gasto.
					</p>
				</section>
				<section class="card overflow-hidden lg:row-span-2">
					<h2 class="px-5 pt-5 font-semibold text-tinta">Modelos que mais dão problema</h2>
					<p class="px-5 text-xs text-suave">(chamados + manutenções corretivas) por unidade</p>
					<ul class="mt-3 divide-y divide-borda border-t border-borda">
						<li v-for="m in d.modelos" :key="m.modelo" class="flex items-center gap-3 px-5 py-2.5 text-sm">
							<div class="min-w-0 flex-1"><p class="truncate text-tinta">{{ m.modelo }}</p><p class="text-xs text-suave">{{ m.unidades }} un. · {{ m.chamados }} chamados · {{ m.corretivas }} corretivas</p></div>
							<span class="rounded-md px-2 py-0.5 text-xs font-semibold tabular-nums" :class="m.indice >= 3 ? 'bg-rose-500/12 text-rose-700 dark:text-rose-300' : 'bg-realce text-texto'">{{ String(m.indice).replace(".", ",") }}</span>
						</li>
					</ul>
				</section>
			</div>

			<div class="grid gap-4 lg:grid-cols-2">
				<section class="card overflow-hidden">
					<h2 class="px-5 pt-5 font-semibold text-tinta">Maior custo total</h2>
					<p class="px-5 text-xs text-suave">Compra + manutenções. Quando manutenção passa de 50% da compra, costuma valer trocar.</p>
					<ul class="mt-3 divide-y divide-borda border-t border-borda">
						<li v-for="e in d.top_custo" :key="e.id">
							<RouterLink :to="`/inventario/${e.id}`" class="flex items-center gap-3 px-5 py-2.5 text-sm hover:bg-realce">
								<IconeEquipamento :nome="e.icone" class="size-4 text-suave" />
								<div class="min-w-0 flex-1"><p class="font-medium text-tinta">{{ e.nome }}</p><p class="truncate text-xs text-suave">{{ e.modelo }} · {{ e.responsavel_nome || e.localizacao || "—" }}</p></div>
								<span class="text-tinta tabular-nums">{{ reais(e.custo_total) }}</span>
							</RouterLink>
						</li>
					</ul>
				</section>
				<section class="card overflow-hidden">
					<h2 class="px-5 pt-5 font-semibold text-tinta">Vida útil vencida</h2>
					<p class="px-5 text-xs text-suave">Prioridade de troca: mais antigos primeiro.</p>
					<ul class="mt-3 divide-y divide-borda border-t border-borda">
						<li v-for="e in d.vida_util_vencida" :key="e.id">
							<RouterLink :to="`/inventario/${e.id}`" class="flex items-center gap-3 px-5 py-2.5 text-sm hover:bg-realce">
								<IconeEquipamento :nome="e.icone" class="size-4 text-suave" />
								<div class="min-w-0 flex-1"><p class="font-medium text-tinta">{{ e.nome }}</p><p class="truncate text-xs text-suave">{{ e.modelo }} · {{ e.responsavel_nome || "—" }}</p></div>
								<span class="text-xs text-rose-600 dark:text-rose-400">desde {{ data(e.fim_vida_util) }}</span>
							</RouterLink>
						</li>
						<li v-if="!d.vida_util_vencida.length" class="px-5 py-4 text-sm text-suave">Nenhum equipamento com vida útil vencida.</li>
					</ul>
				</section>
			</div>
		</template>
	</div>
</template>
