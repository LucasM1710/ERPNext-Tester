<script setup>
import { Download, Gauge, Plus, Search, Send, X } from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import FormEquipamento from "@/components/FormEquipamento.vue"
import Vazio from "@/components/Vazio.vue"
import { COR_SITUACAO } from "@/cores"
import { data, exportarCsv, relativo } from "@/format"
import { algumComDistritos, podeEditar, store } from "@/store"

const route = useRoute()
const router = useRouter()

const todos = ref(null)
const busca = ref(route.query.busca || "")
const situacao = ref(route.query.situacao || "")
const grandeza = ref("")
const calibradoPor = ref("")
const mostrarInativos = ref(false)
const verificacaoPendente = ref(route.query.verificacao === "pendente")
const hoje = new Date().toISOString().slice(0, 10)
const precisaVerificar = (e) => e.resultado_ultima_verificacao === "Não Conforme" || (e.proxima_verificacao && e.proxima_verificacao < hoje)
const selecionados = ref(new Set())
const novo = ref(false)

const SITUACOES = ["Vencido", "A Vencer", "Em Dia", "Sem Calibração"]

async function carregar() {
	todos.value = await api("equipamentos")
}
onMounted(carregar)

watch([situacao, busca], () => router.replace({ query: { ...(situacao.value && { situacao: situacao.value }), ...(busca.value && { busca: busca.value }) } }))

const base = computed(() => (todos.value || []).filter((e) => mostrarInativos.value || !["Inativo", "Sucateado"].includes(e.status)))

const contagem = computed(() => Object.fromEntries(SITUACOES.map((s) => [s, base.value.filter((e) => e.situacao === s).length])))
const grandezas = computed(() => [...new Set(base.value.map((e) => e.grandeza).filter(Boolean))].sort())

const filtrados = computed(() => {
	const termo = busca.value.trim().toLowerCase()
	return base.value
		.filter((e) => !situacao.value || e.situacao === situacao.value)
		.filter((e) => !grandeza.value || e.grandeza === grandeza.value)
		.filter((e) => !calibradoPor.value || e.calibrado_por === calibradoPor.value)
		.filter((e) => !verificacaoPendente.value || precisaVerificar(e))
		.filter(
			(e) =>
				!termo ||
				[e.tag, e.descricao, e.numero_serie, e.localizacao, e.distrito_nome, e.fabricante, e.modelo, e.responsavel].some((v) => v?.toLowerCase().includes(termo)),
		)
		.sort((a, b) => (a.proxima_calibracao || "9999") < (b.proxima_calibracao || "9999") ? -1 : 1)
})

const todosMarcados = computed(() => filtrados.value.length > 0 && filtrados.value.every((e) => selecionados.value.has(e.id)))

function alternar(id) {
	const s = new Set(selecionados.value)
	s.has(id) ? s.delete(id) : s.add(id)
	selecionados.value = s
}
function alternarTodos() {
	selecionados.value = todosMarcados.value ? new Set() : new Set(filtrados.value.map((e) => e.id))
}

function solicitar() {
	router.push({ path: "/solicitar", query: { equipamentos: [...selecionados.value].join(",") } })
}

function exportar() {
	exportarCsv(
		"equipamentos.csv",
		[
			{ label: "TAG", valor: (e) => e.tag },
			{ label: "Descrição", valor: (e) => e.descricao },
			{ label: "Grandeza", valor: (e) => e.grandeza },
			{ label: "Fabricante", valor: (e) => e.fabricante },
			{ label: "Modelo", valor: (e) => e.modelo },
			{ label: "Nº Série", valor: (e) => e.numero_serie },
			{ label: "Distrito", valor: (e) => e.distrito_nome },
			{ label: "Localização", valor: (e) => e.localizacao },
			{ label: "Responsável", valor: (e) => e.responsavel },
			{ label: "Status", valor: (e) => e.status },
			{ label: "Calibrado por", valor: (e) => (e.calibrado_por === "Terceiro" ? e.fornecedor_externo : e.calibrado_por) },
			{ label: "Última calibração", valor: (e) => data(e.ultima_calibracao) },
			{ label: "Próxima calibração", valor: (e) => data(e.proxima_calibracao) },
			{ label: "Situação", valor: (e) => e.situacao },
		],
		filtrados.value,
	)
}

function aoSalvar(eqp) {
	novo.value = false
	router.push(`/equipamentos/${eqp.id}`)
}
</script>

<template>
	<div class="space-y-5">
		<div class="flex flex-wrap items-end justify-between gap-4">
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-slate-900">Equipamentos</h1>
				<p class="mt-1 text-sm text-slate-500">Todo o seu parque de instrumentos, inclusive os calibrados por terceiros.</p>
			</div>
			<div class="flex gap-2">
				<button class="btn-secondary" :disabled="!filtrados.length" @click="exportar"><Download class="size-4" /> Exportar</button>
				<button v-if="store.contexto.config.permitir_cadastro_cliente && podeEditar()" class="btn-primary" @click="novo = true">
					<Plus class="size-4" /> Novo equipamento
				</button>
			</div>
		</div>

		<!-- Filtros de situação -->
		<div class="flex flex-wrap gap-2">
			<button class="chip" :class="!situacao ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'" @click="situacao = ''">
				Todos <span class="tabular-nums opacity-70">{{ base.length }}</span>
			</button>
			<button
				v-for="s in SITUACOES"
				:key="s"
				class="chip"
				:class="situacao === s ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'"
				@click="situacao = situacao === s ? '' : s"
			>
				<span class="size-2 rounded-full" :style="{ background: COR_SITUACAO[s] }" />
				{{ s }} <span class="tabular-nums opacity-70">{{ contagem[s] }}</span>
			</button>
		</div>

		<div class="card overflow-hidden">
			<!-- Barra de busca -->
			<div class="flex flex-wrap items-center gap-3 border-b border-slate-100 p-3">
				<div class="relative min-w-[220px] flex-1">
					<Search class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" />
					<input v-model="busca" class="input pl-9" placeholder="Buscar por TAG, descrição, nº de série, setor…" />
				</div>
				<select v-model="grandeza" class="input w-auto">
					<option value="">Todas as grandezas</option>
					<option v-for="g in grandezas" :key="g">{{ g }}</option>
				</select>
				<select v-model="calibradoPor" class="input w-auto">
					<option value="">Qualquer laboratório</option>
					<option value="Nosso Laboratório">{{ store.contexto.empresa }}</option>
					<option value="Terceiro">Terceiros</option>
				</select>
				<label class="flex items-center gap-2 px-1 text-sm text-slate-600">
					<input v-model="mostrarInativos" type="checkbox" class="accent-brand-600" /> Inativos
				</label>
				<label class="flex items-center gap-2 px-1 text-sm text-slate-600">
					<input v-model="verificacaoPendente" type="checkbox" class="accent-brand-600" /> Verificação pendente
				</label>
			</div>

			<!-- Barra de seleção -->
			<Transition name="fade">
				<div v-if="selecionados.size" class="flex items-center gap-3 border-b border-brand-100 bg-brand-50/70 px-4 py-2.5">
					<p class="text-sm font-medium text-brand-800">{{ selecionados.size }} selecionado(s)</p>
					<button class="btn-ghost px-2 py-1 text-xs" @click="selecionados = new Set()"><X class="size-3.5" /> Limpar</button>
					<button v-if="podeEditar()" class="btn-primary ml-auto py-1.5" @click="solicitar"><Send class="size-4" /> Solicitar calibração</button>
				</div>
			</Transition>

			<div v-if="!todos" class="p-5"><Esqueleto :linhas="8" classe="h-9" /></div>

			<Vazio v-else-if="!filtrados.length" :icone="Gauge" titulo="Nenhum equipamento encontrado" texto="Ajuste os filtros ou cadastre um novo equipamento." />

			<template v-else>
				<!-- Tabela (desktop) -->
				<div class="hidden overflow-x-auto md:block">
					<table class="w-full">
						<thead class="border-b border-slate-100 bg-slate-50/60">
							<tr>
								<th class="th w-10"><input type="checkbox" class="accent-brand-600" :checked="todosMarcados" @change="alternarTodos" /></th>
								<th class="th">Equipamento</th>
								<th class="th">Fabricante / Modelo</th>
								<th v-if="algumComDistritos()" class="th">Distrito</th>
								<th class="th">Localização</th>
								<th class="th">Laboratório</th>
								<th class="th">Próxima calibração</th>
								<th class="th">Situação</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-slate-100">
							<tr
								v-for="e in filtrados"
								:key="e.id"
								class="cursor-pointer transition hover:bg-slate-50"
								:class="selecionados.has(e.id) && 'bg-brand-50/40'"
								@click="router.push(`/equipamentos/${e.id}`)"
							>
								<td class="td" @click.stop><input type="checkbox" class="accent-brand-600" :checked="selecionados.has(e.id)" @change="alternar(e.id)" /></td>
								<td class="td">
									<p class="font-semibold text-slate-900">{{ e.tag }}</p>
									<p class="text-xs text-slate-500">{{ e.descricao }}<span v-if="e.numero_serie"> · SN {{ e.numero_serie }}</span></p>
								</td>
								<td class="td text-slate-600">{{ [e.fabricante, e.modelo].filter(Boolean).join(" · ") || "—" }}</td>
								<td v-if="algumComDistritos()" class="td">
									<span v-if="e.distrito_nome" class="inline-flex items-center gap-1 rounded-md bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-800">{{ e.distrito_nome }}</span>
									<span v-else class="text-xs text-amber-600">Sem distrito</span>
								</td>
								<td class="td text-slate-600">{{ e.localizacao || "—" }}</td>
								<td class="td">
									<Etiqueta v-if="e.calibrado_por === 'Terceiro'" valor="Terceiro" :ponto="false">{{ e.fornecedor_externo || "Terceiro" }}</Etiqueta>
									<span v-else class="text-sm text-slate-600">{{ store.contexto.empresa }}</span>
								</td>
								<td class="td">
									<p class="text-slate-700 tabular-nums">{{ data(e.proxima_calibracao) }}</p>
									<p v-if="e.proxima_calibracao" class="text-xs" :class="e.situacao === 'Vencido' ? 'text-rose-600' : e.situacao === 'A Vencer' ? 'text-amber-600' : 'text-slate-400'">
										{{ relativo(e.proxima_calibracao) }}
									</p>
								</td>
								<td class="td">
									<div class="flex flex-col items-start gap-1">
										<Etiqueta :valor="e.situacao" />
										<span v-if="e.resultado_ultima_verificacao === 'Não Conforme'" class="text-[11px] font-medium text-rose-600">Verificação NC</span>
										<span v-else-if="e.proxima_verificacao && e.proxima_verificacao < hoje" class="text-[11px] font-medium text-amber-600">Verificar</span>
									</div>
								</td>
							</tr>
						</tbody>
					</table>
				</div>

				<!-- Cartões (celular) -->
				<ul class="divide-y divide-slate-100 md:hidden">
					<li v-for="e in filtrados" :key="e.id" class="flex items-start gap-3 p-4">
						<input type="checkbox" class="mt-1 accent-brand-600" :checked="selecionados.has(e.id)" @change="alternar(e.id)" />
						<RouterLink :to="`/equipamentos/${e.id}`" class="min-w-0 flex-1">
							<div class="flex items-start justify-between gap-2">
								<p class="font-semibold text-slate-900">{{ e.tag }}</p>
								<Etiqueta :valor="e.situacao" />
							</div>
							<p class="text-sm text-slate-600">{{ e.descricao }}</p>
							<p class="mt-1 text-xs text-slate-500">{{ [e.distrito_nome, e.localizacao].filter(Boolean).join(" · ") || "—" }} · vence {{ data(e.proxima_calibracao) }}</p>
						</RouterLink>
					</li>
				</ul>

				<p class="border-t border-slate-100 px-4 py-3 text-xs text-slate-500">{{ filtrados.length }} de {{ base.length }} equipamentos</p>
			</template>
		</div>

		<FormEquipamento v-if="novo" @fechar="novo = false" @salvo="aoSalvar" />
	</div>
</template>
