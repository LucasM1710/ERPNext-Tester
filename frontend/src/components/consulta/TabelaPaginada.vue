<script setup>
import { computed, ref, watch } from "vue"

// Tabela com paginação local. colunas: [{ rotulo, valor: (linha) => texto, classe?: (linha) => string }]
const props = defineProps({
	titulo: String,
	subtitulo: String,
	colunas: { type: Array, required: true },
	linhas: { type: Array, default: () => [] },
	vazio: { type: String, default: "Sem resultados para os filtros aplicados." },
	chave: { type: Function, default: (l, i) => i },
})

const porPagina = ref(10)
const pagina = ref(1)
const total = computed(() => Math.max(1, Math.ceil(props.linhas.length / porPagina.value)))
const visiveis = computed(() => props.linhas.slice((pagina.value - 1) * porPagina.value, pagina.value * porPagina.value))
watch([() => props.linhas, porPagina], () => (pagina.value = 1))
</script>

<template>
	<section class="card overflow-hidden">
		<div class="flex flex-wrap items-start justify-between gap-3 p-5 pb-3">
			<div>
				<h2 class="font-semibold text-slate-900">{{ titulo }}</h2>
				<p class="text-xs text-slate-500">
					{{ subtitulo ? subtitulo + " · " : "" }}Exibindo {{ linhas.length ? (pagina - 1) * porPagina + 1 : 0 }}–{{ Math.min(pagina * porPagina, linhas.length) }} de
					{{ linhas.length }} registro(s)
				</p>
			</div>
			<div class="flex flex-wrap items-center gap-2 text-xs text-slate-500">
				<span>Por página</span>
				<select v-model.number="porPagina" class="input h-8 w-20 py-0 text-xs">
					<option v-for="n in [10, 25, 50, 100]" :key="n" :value="n">{{ n }}</option>
				</select>
				<button class="btn-ghost px-2.5 py-1 text-xs" :disabled="pagina <= 1" @click="pagina--">Anterior</button>
				<span class="font-semibold text-slate-800">Página {{ pagina }} de {{ total }}</span>
				<button class="btn-ghost px-2.5 py-1 text-xs" :disabled="pagina >= total" @click="pagina++">Próxima</button>
			</div>
		</div>
		<div class="overflow-x-auto">
			<table class="w-full text-[13px]">
				<thead>
					<tr class="bg-brand-700 text-left text-[11px] tracking-wider text-white uppercase">
						<th v-for="c in colunas" :key="c.rotulo" class="px-3 py-2.5 font-semibold whitespace-nowrap">{{ c.rotulo }}</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-100">
					<tr v-if="!linhas.length"><td :colspan="colunas.length" class="px-3 py-8 text-center text-slate-500">{{ vazio }}</td></tr>
					<tr v-for="(l, i) in visiveis" :key="chave(l, i)" class="hover:bg-slate-50/80">
						<td v-for="c in colunas" :key="c.rotulo" class="px-3 py-2 whitespace-nowrap" :class="c.classe ? c.classe(l) : 'text-slate-700'">
							<slot :name="c.rotulo" :linha="l">{{ c.valor(l) }}</slot>
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</section>
</template>
