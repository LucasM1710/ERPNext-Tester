<script setup>
import { CheckCircle2, ExternalLink, PackagePlus, Settings2 } from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import Grafico from "@/components/Grafico.vue"
import IconeEquipamento from "@/components/IconeEquipamento.vue"
import Modal from "@/components/Modal.vue"
import { baseGrafico, COR } from "@/cores"
import { data } from "@/format"
import { store, toast } from "@/store"

const ano = ref(null)
const d = ref(null)
const cadastro = ref(null) // { item, nomes: [] }
const salvando = ref(false)

async function carregar() {
	d.value = null
	d.value = await api("inventario.compras", { ano: ano.value })
	ano.value = d.value.ano
}
onMounted(carregar)
watch(ano, (novo, velho) => velho && carregar())

const reais = (v) => Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
const porNota = computed(() => {
	const g = {}
	for (const i of d.value?.itens || []) (g[i.nota] ||= { nota: i.nota, data: i.data, fornecedor: i.fornecedor, itens: [], total: 0 }).itens.push(i)
	for (const n of Object.values(g)) n.total = n.itens.reduce((s, i) => s + i.valor_total, 0)
	return Object.values(g)
})

const grafMes = computed(() => {
	const g = baseGrafico(store.escuro)
	return {
		grid: { left: 8, right: 8, top: 16, bottom: 4, containLabel: true },
		tooltip: { ...g.tooltip, trigger: "axis", valueFormatter: (v) => reais(v) },
		xAxis: { type: "category", data: ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"], ...g.eixo, splitLine: { show: false } },
		yAxis: { type: "value", ...g.eixo, axisLabel: { ...g.eixo.axisLabel, formatter: (v) => (v >= 1000 ? `${v / 1000}k` : v) } },
		series: [{ type: "bar", data: d.value.resumo.por_mes, barMaxWidth: 26, itemStyle: { color: COR.marca, borderRadius: [6, 6, 2, 2] } }],
	}
})

function abrirCadastro(item) {
	const prefixo = { Notebook: "NB", Desktop: "DT", Monitor: "MN", Impressora: "IMP", Celular: "CEL", Switch: "SW", Servidor: "SRV", Nobreak: "NBK" }[item.tipo] || "EQ"
	cadastro.value = { item, nomes: Array.from({ length: item.pendentes }, () => ""), prefixo }
}
async function cadastrar() {
	const { item, nomes } = cadastro.value
	salvando.value = true
	try {
		const r = await api("inventario.cadastrar_da_compra", { linha: item.linha, nomes: item.controla_estoque ? undefined : nomes.filter((n) => n.trim()) }, { post: true })
		toast(r.estoque ? `+${r.quantidade} em "${r.estoque}" no estoque.` : `${r.equipamentos.length} equipamento(s) cadastrado(s): ${r.equipamentos.join(", ")}`)
		cadastro.value = null
		await carregar()
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		salvando.value = false
	}
}
</script>

<template>
	<div class="space-y-5">
		<div class="flex flex-wrap items-end justify-between gap-4">
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-tinta">Compras de TI</h1>
				<p class="mt-1 text-sm text-suave">Lidas das Notas de Compra lançadas no ERP. Cada item comprado vira equipamento (ou entrada no estoque) com um clique.</p>
			</div>
			<nav v-if="d?.anos?.length" class="flex flex-wrap gap-1 rounded-xl bg-realce p-1">
				<button v-for="a in d.anos" :key="a" class="rounded-lg px-3 py-1.5 text-sm font-medium transition" :class="ano === a ? 'bg-superficie text-tinta shadow-sm' : 'text-suave hover:text-tinta'" @click="ano = a">{{ a }}</button>
			</nav>
		</div>

		<div v-if="!d" class="card p-6"><Esqueleto :linhas="6" /></div>
		<div v-else-if="!d.configurado" class="card p-6">
			<p class="flex items-center gap-2 font-semibold text-tinta"><Settings2 class="size-5 text-marca-600" /> Ligue os tipos de equipamento aos Grupos de Item do ERP</p>
			<p class="mt-2 text-sm text-texto">Em <b>Tipo Equipamento TI</b>, preencha "Grupo de Item no ERP" (ex.: Notebook → TI &gt; Notebooks). A partir daí, as compras desses grupos aparecem aqui.</p>
			<a href="/app/tipo-equipamento-ti" class="btn-secundario mt-4">Abrir tipos de equipamento</a>
		</div>
		<template v-else>
			<div class="grid gap-4 lg:grid-cols-3">
				<div class="space-y-4">
					<div class="card p-5"><p class="text-sm text-suave">Total comprado em {{ d.ano }}</p><p class="mt-1 text-3xl font-semibold tracking-tight text-tinta tabular-nums">{{ reais(d.resumo.total) }}</p><p class="mt-1 text-xs text-suave">{{ d.resumo.notas }} nota(s) de compra</p></div>
					<div class="card p-5">
						<p class="text-sm text-suave">Por categoria</p>
						<ul class="mt-3 space-y-2">
							<li v-for="[g, v] in d.resumo.por_grupo" :key="g" class="text-sm">
								<div class="flex justify-between"><span class="text-texto">{{ g }}</span><span class="font-medium text-tinta tabular-nums">{{ reais(v) }}</span></div>
								<div class="mt-1 h-1.5 overflow-hidden rounded-full bg-realce"><div class="h-full rounded-full bg-marca-500" :style="{ width: (100 * v) / d.resumo.total + '%' }" /></div>
							</li>
						</ul>
					</div>
				</div>
				<section class="card p-5 lg:col-span-2">
					<h2 class="font-semibold text-tinta">Gasto por mês</h2>
					<Grafico class="mt-3" :opcoes="grafMes" altura="240px" />
					<p v-if="d.resumo.pendentes" class="mt-3 rounded-lg bg-amber-500/10 p-3 text-sm text-amber-800 dark:text-amber-300">{{ d.resumo.pendentes }} item(ns) comprado(s) ainda sem cadastro no inventário.</p>
				</section>
			</div>

			<section v-for="n in porNota" :key="n.nota" class="card overflow-hidden">
				<div class="flex flex-wrap items-center gap-3 border-b border-borda px-5 py-3">
					<p class="font-semibold text-tinta">{{ n.fornecedor }}</p>
					<p class="text-sm text-suave">{{ data(n.data) }}</p>
					<a :href="`/app/purchase-invoice/${n.nota}`" target="_blank" class="inline-flex items-center gap-1 text-xs text-marca-600 dark:text-marca-300">{{ n.nota }} <ExternalLink class="size-3" /></a>
					<p class="ml-auto font-semibold text-tinta tabular-nums">{{ reais(n.total) }}</p>
				</div>
				<ul class="divide-y divide-borda">
					<li v-for="i in n.itens" :key="i.linha" class="flex flex-wrap items-center gap-3 px-5 py-3">
						<span class="grid size-9 shrink-0 place-items-center rounded-xl bg-marca-500/10 text-marca-600 dark:text-marca-300"><IconeEquipamento :nome="i.icone" class="size-4" /></span>
						<div class="min-w-0 flex-1">
							<p class="text-sm font-medium text-tinta">{{ i.item_name }}</p>
							<p class="text-xs text-suave">{{ i.qtd }} × {{ reais(i.valor_unitario) }} · {{ i.tipo }}</p>
						</div>
						<p class="text-sm text-tinta tabular-nums">{{ reais(i.valor_total) }}</p>
						<span v-if="!i.pendentes" class="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400"><CheckCircle2 class="size-4" /> {{ i.controla_estoque ? "no estoque" : "cadastrado" }}</span>
						<button v-else class="btn-primario py-1.5 text-xs" @click="abrirCadastro(i)">
							<PackagePlus class="size-4" /> {{ i.controla_estoque ? `Dar entrada (${i.pendentes})` : `Cadastrar ${i.pendentes}` }}
						</button>
					</li>
				</ul>
			</section>
		</template>

		<Modal v-if="cadastro" :titulo="cadastro.item.controla_estoque ? 'Entrada no estoque' : 'Cadastrar equipamentos'" :subtitulo="cadastro.item.item_name" @fechar="cadastro = null">
			<form id="form-cad" class="space-y-3" @submit.prevent="cadastrar">
				<p v-if="cadastro.item.controla_estoque" class="text-sm text-texto">Serão lançadas <b>{{ cadastro.item.pendentes }}</b> unidade(s) no item de estoque "{{ cadastro.item.item_name }}".</p>
				<template v-else>
					<p class="text-sm text-texto">Dê um nome (hostname/identificação) para cada unidade. Modelo, valor, fornecedor e data vêm da nota.</p>
					<div v-for="(n, idx) in cadastro.nomes" :key="idx" class="flex items-center gap-2">
						<span class="w-6 text-right text-xs text-suave">{{ idx + 1 }}</span>
						<input v-model="cadastro.nomes[idx]" class="campo uppercase" :placeholder="`${cadastro.prefixo}-0${idx + 1}`" :required="idx === 0" />
					</div>
				</template>
			</form>
			<template #rodape>
				<button class="btn-secundario" @click="cadastro = null">Cancelar</button>
				<button class="btn-primario" form="form-cad" type="submit" :disabled="salvando">{{ salvando ? "Salvando…" : "Confirmar" }}</button>
			</template>
		</Modal>
	</div>
</template>
