<script setup>
import { Award, Download, FileCheck2, FileUp, Search } from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { api, urlDownloadCertificado } from "@/api"
import EnviarCertificado from "@/components/EnviarCertificado.vue"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import Vazio from "@/components/Vazio.vue"
import { data, exportarCsv } from "@/format"
import { CONSULTA } from "@/modo"
import { podeEditar, store } from "@/store"

const route = useRoute()
const router = useRouter()

const lista = ref(null)
const aba = ref(route.query.aba || "todos")
const busca = ref("")
const enviar = ref(false)

// Página de consulta: sem análise crítica (fase 2).
const ABAS = [
	{ id: "todos", rotulo: "Todos", filtro: () => true },
	!CONSULTA && { id: "pendentes", rotulo: "Análise pendente", filtro: (c) => c.status_analise === "Pendente" },
	// Fase 1 (/consulta): situação pela validade, sem resultado de medição.
	CONSULTA
		? { id: "vencidos", rotulo: "Vencidos", filtro: (c) => c.vigencia === "Vencido" }
		: { id: "reprovados", rotulo: "Reprovados", filtro: (c) => c.resultado === "Reprovado" },
	CONSULTA && { id: "vigentes", rotulo: "Vigentes", filtro: (c) => c.vigencia === "Vigente" },
	{ id: "externos", rotulo: "De terceiros", filtro: (c) => c.origem === "Externo" },
].filter(Boolean)

async function carregar() {
	lista.value = await api("certificados")
}
onMounted(carregar)
watch(aba, () => router.replace({ query: aba.value === "todos" ? {} : { aba: aba.value } }))

const contagem = computed(() => Object.fromEntries(ABAS.map((a) => [a.id, (lista.value || []).filter(a.filtro).length])))

const filtrados = computed(() => {
	const termo = busca.value.trim().toLowerCase()
	const filtro = ABAS.find((a) => a.id === aba.value).filtro
	return (lista.value || [])
		.filter(filtro)
		.filter((c) => !termo || [c.numero, c.tag, c.descricao_equipamento, c.laboratorio].some((v) => v?.toLowerCase().includes(termo)))
})

function exportar() {
	exportarCsv(
		"certificados.csv",
		[
			{ label: "Certificado", valor: (c) => c.numero },
			{ label: "TAG", valor: (c) => c.tag },
			{ label: "Equipamento", valor: (c) => c.descricao_equipamento },
			{ label: "Data calibração", valor: (c) => data(c.data_calibracao) },
			{ label: "Validade", valor: (c) => data(c.data_validade) },
			{ label: "Laboratório", valor: (c) => c.laboratorio },
			{ label: "Acreditado", valor: (c) => (c.acreditado ? "Sim" : "Não") },
			CONSULTA ? { label: "Situação", valor: (c) => c.vigencia } : { label: "Resultado", valor: (c) => c.resultado },
			{ label: "Análise crítica", valor: (c) => c.status_analise },
			{ label: "Analisado por", valor: (c) => c.analisado_por },
			{ label: "Data análise", valor: (c) => data(c.data_analise) },
		],
		filtrados.value,
	)
}

function aoEnviar(cert) {
	enviar.value = false
	router.push(`/certificados/${cert.id}`)
}
</script>

<template>
	<div class="space-y-5">
		<div class="flex flex-wrap items-end justify-between gap-4">
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-slate-900">Certificados</h1>
				<p class="mt-1 text-sm text-slate-500">Consulte, baixe e registre a análise crítica de cada calibração.</p>
			</div>
			<div class="flex gap-2">
				<button class="btn-secondary" :disabled="!filtrados.length" @click="exportar"><Download class="size-4" /> Exportar lista</button>
				<button v-if="store.contexto.config.permitir_certificado_externo && podeEditar()" class="btn-primary" @click="enviar = true">
					<FileUp class="size-4" /> Enviar certificado externo
				</button>
			</div>
		</div>

		<div class="card overflow-hidden">
			<div class="flex flex-wrap items-center gap-3 border-b border-slate-100 px-3 pt-3">
				<nav class="-mb-px flex gap-1 overflow-x-auto">
					<button
						v-for="a in ABAS"
						:key="a.id"
						class="flex items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium whitespace-nowrap transition"
						:class="aba === a.id ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-800'"
						@click="aba = a.id"
					>
						{{ a.rotulo }}
						<span class="rounded-full px-1.5 py-0.5 text-[11px] tabular-nums" :class="aba === a.id ? 'bg-brand-50 text-brand-700' : 'bg-slate-100 text-slate-500'">{{ contagem[a.id] }}</span>
					</button>
				</nav>
				<div class="relative mb-3 ml-auto w-full sm:w-72">
					<Search class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" />
					<input v-model="busca" class="input pl-9" placeholder="Nº, TAG, equipamento…" />
				</div>
			</div>

			<div v-if="!lista" class="p-5"><Esqueleto :linhas="8" classe="h-9" /></div>
			<Vazio v-else-if="!filtrados.length" :icone="FileCheck2" titulo="Nenhum certificado" texto="Nada encontrado para este filtro." />

			<div v-else class="overflow-x-auto">
				<table class="w-full min-w-[820px]">
					<thead class="border-b border-slate-100 bg-slate-50/60">
						<tr>
							<th class="th">Certificado</th>
							<th class="th">Equipamento</th>
							<th class="th">Calibração</th>
							<th class="th">Validade</th>
							<th class="th">Laboratório</th>
							<th class="th">{{ CONSULTA ? "Situação" : "Resultado" }}</th>
							<th v-if="!CONSULTA" class="th">Análise crítica</th>
							<th class="th w-12"></th>
						</tr>
					</thead>
					<tbody class="divide-y divide-slate-100">
						<tr v-for="c in filtrados" :key="c.id" class="cursor-pointer transition hover:bg-slate-50" @click="router.push(`/certificados/${c.id}`)">
							<td class="td">
								<p class="font-medium text-slate-900">{{ c.numero }}</p>
								<p v-if="c.origem === 'Externo'" class="text-[11px] font-medium text-violet-600">Externo</p>
							</td>
							<td class="td">
								<p class="font-medium text-slate-800">{{ c.tag }}</p>
								<p class="text-xs text-slate-500">{{ c.descricao_equipamento }}</p>
							</td>
							<td class="td text-slate-600 tabular-nums">{{ data(c.data_calibracao) }}</td>
							<td class="td text-slate-600 tabular-nums">{{ data(c.data_validade) }}</td>
							<td class="td">
								<p class="flex items-center gap-1.5 text-slate-700">
									{{ c.laboratorio }} <Award v-if="c.acreditado" class="size-3.5 text-brand-500" title="Acreditado" />
								</p>
							</td>
							<td class="td"><Etiqueta :valor="CONSULTA ? c.vigencia : c.resultado" /></td>
							<td v-if="!CONSULTA" class="td"><Etiqueta :valor="c.status_analise" :ponto="false" /></td>
							<td class="td" @click.stop>
								<a v-if="c.tem_arquivo" :href="urlDownloadCertificado(c.id)" class="btn-ghost p-1.5" title="Baixar PDF"><Download class="size-4" /></a>
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</div>

		<EnviarCertificado v-if="enviar" @fechar="enviar = false" @salvo="aoEnviar" />
	</div>
</template>
