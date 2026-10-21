<script setup>
import { ChevronRight, Gauge, MapPin, Plus, Search, Upload } from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"
import { useRouter } from "vue-router"
import { api } from "@/api"
import EnviarCertificado from "@/components/EnviarCertificado.vue"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import FormEquipamento from "@/components/FormEquipamento.vue"
import Vazio from "@/components/Vazio.vue"
import { COR_STATUS } from "@/cores"
import { data } from "@/format"
import { podeEditar, store } from "@/store"

// Parque de equipamentos: calibrados pela ER Analítica (ERP) e por terceiros (cadastro do cliente).
const router = useRouter()
const lista = ref(null)
const busca = ref("")
const status = ref("")
const owner = ref("")
const fonte = ref("")
const pagina = ref(1)
const POR_PAGINA = 20
const novo = ref(false)
const enviarCert = ref(false)

const STATUS = ["Vencido", "Crítico", "Alerta 60", "Agendado", "Calibrado", "Sem calibração"]
const podeCadastrar = computed(() => store.contexto?.config.permitir_cadastro_cliente && podeEditar())
const variosClientes = computed(() => (store.contexto?.clientes.length || 0) > 1)

async function carregar() {
	lista.value = await api("equipamentos")
}
onMounted(carregar)

const contagem = computed(() => {
	const c = Object.fromEntries(STATUS.map((s) => [s, 0]))
	for (const e of lista.value || []) c[e.status_calibracao]++
	return c
})
const owners = computed(() => [...new Set((lista.value || []).map((e) => e.owner).filter(Boolean))].sort())
const filtrados = computed(() => {
	const q = busca.value.trim().toLowerCase()
	return (lista.value || []).filter(
		(e) =>
			(!status.value || e.status_calibracao === status.value) &&
			(!owner.value || e.owner === owner.value) &&
			(!fonte.value || e.origem === fonte.value) &&
			(!q || ["tag", "descricao", "numero_serie", "modelo", "fabricante", "certificado", "owner", "vendor", "distrito_nome"].some((c) => String(e[c] || "").toLowerCase().includes(q))),
	)
})
const totalPaginas = computed(() => Math.max(1, Math.ceil(filtrados.value.length / POR_PAGINA)))
const visiveis = computed(() => filtrados.value.slice((pagina.value - 1) * POR_PAGINA, pagina.value * POR_PAGINA))
watch([busca, status, owner, fonte], () => (pagina.value = 1))

// Barra de validade restante (0–100%).
function restante(e) {
	if (!e.ultima_calibracao || !e.proxima_calibracao) return null
	const total = (new Date(e.proxima_calibracao) - new Date(e.ultima_calibracao)) / 86400000
	return Math.max(0, Math.min(100, Math.round((e.dias_para_vencer / total) * 100)))
}
function prazo(e) {
	const d = e.dias_para_vencer
	if (d === null || d === undefined) return "sem calibração registrada"
	if (d < 0) return `vencido há ${-d} dia(s)`
	if (d === 0) return "vence hoje"
	return `vence em ${d} dia(s)`
}
</script>

<template>
	<div class="space-y-6">
		<div class="flex flex-wrap items-end justify-between gap-4">
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-slate-900">Equipamentos</h1>
				<p class="mt-1 text-sm text-slate-500">Todo o parque num só lugar — calibrados pela ER Analítica e por outros laboratórios.</p>
			</div>
			<div v-if="podeCadastrar" class="flex flex-wrap gap-2">
				<button class="btn-secondary" @click="enviarCert = true"><Upload class="size-4" /> Enviar certificado de terceiro</button>
				<button class="btn-primary" @click="novo = true"><Plus class="size-4" /> Equipamento de terceiro</button>
			</div>
		</div>

		<!-- Filtro por status -->
		<div class="flex flex-wrap gap-2">
			<button class="chip" :class="!status ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'" @click="status = ''">
				Todos <span class="tabular-nums opacity-80">{{ lista?.length ?? "—" }}</span>
			</button>
			<button
				v-for="s in STATUS"
				:key="s"
				class="chip"
				:class="status === s ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'"
				@click="status = status === s ? '' : s"
			>
				<span class="size-2 rounded-full" :style="{ background: COR_STATUS[s] }" /> {{ s }} <span class="tabular-nums opacity-70">{{ contagem[s] }}</span>
			</button>
		</div>

		<div class="grid gap-3 md:grid-cols-[1fr_220px_240px]">
			<label class="relative">
				<Search class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" />
				<input v-model="busca" class="input pl-9" placeholder="Buscar por série, TAG, equipamento, certificado, distrito…" autocomplete="off" />
			</label>
			<select v-model="owner" class="input">
				<option value="">Todos os responsáveis</option>
				<option v-for="o in owners" :key="o" :value="o">{{ o }}</option>
			</select>
			<select v-model="fonte" class="input">
				<option value="">ER Analítica e terceiros</option>
				<option value="laboratorio">Calibrados pela ER Analítica</option>
				<option value="cliente">Calibrados por terceiros</option>
			</select>
		</div>

		<div v-if="!lista" class="card p-6"><Esqueleto :linhas="10" /></div>
		<div v-else-if="!filtrados.length" class="card"><Vazio :icone="Gauge" titulo="Nenhum equipamento encontrado" texto="Ajuste a busca ou os filtros." /></div>

		<section v-else class="card overflow-hidden">
			<div class="hidden grid-cols-[minmax(0,2.2fr)_minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1.3fr)_minmax(0,1.4fr)_24px] gap-4 border-b border-slate-100 bg-slate-50/70 px-5 py-3 text-[11px] font-semibold tracking-wider text-slate-500 uppercase lg:grid">
				<span>Equipamento</span><span>Situação</span><span>Próxima calibração</span><span>Calibração</span><span>Local e responsável</span><span />
			</div>
			<ul class="divide-y divide-slate-100">
				<li
					v-for="e in visiveis"
					:key="e.id"
					class="group grid cursor-pointer gap-3 px-5 py-4 transition hover:bg-brand-50/40 lg:grid-cols-[minmax(0,2.2fr)_minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1.3fr)_minmax(0,1.4fr)_24px] lg:items-center lg:gap-4"
					@click="router.push(`/equipamentos/${e.id}`)"
				>
					<div class="min-w-0">
						<p class="truncate font-semibold text-slate-900 group-hover:text-brand-700">{{ e.descricao }}</p>
						<p class="truncate text-xs text-slate-500">
							<b class="font-medium text-slate-700">{{ e.tag }}</b> · série {{ e.numero_serie || "—" }}<template v-if="e.fabricante || e.modelo"> · {{ [e.fabricante, e.modelo].filter(Boolean).join(" ") }}</template>
						</p>
						<p v-if="e.observacao" class="mt-0.5 truncate text-xs text-amber-700/90 italic">“{{ e.observacao }}”</p>
					</div>
					<div class="min-w-0">
						<Etiqueta :valor="e.status_calibracao" />
						<div v-if="restante(e) !== null" class="mt-2 h-1.5 w-full max-w-[160px] overflow-hidden rounded-full bg-slate-100">
							<div class="h-full rounded-full" :style="{ width: restante(e) + '%', background: COR_STATUS[e.status_calibracao] }" />
						</div>
					</div>
					<div>
						<p class="text-sm font-medium text-slate-800">{{ data(e.proxima_calibracao) }}</p>
						<p class="text-xs" :class="e.dias_para_vencer < 0 ? 'font-medium text-rose-600' : e.dias_para_vencer <= 45 ? 'font-medium text-orange-600' : 'text-slate-500'">{{ prazo(e) }}</p>
					</div>
					<div class="min-w-0">
						<span class="inline-flex max-w-full truncate rounded-full px-2.5 py-0.5 text-[11px] font-semibold" :class="e.origem === 'laboratorio' ? 'bg-brand-50 text-brand-700' : 'bg-violet-50 text-violet-700'">{{ e.vendor }}</span>
						<p class="mt-1 truncate text-xs text-slate-500">{{ e.certificado ? `Cert. ${e.certificado} · ${data(e.ultima_calibracao)}` : "Sem certificado" }}</p>
					</div>
					<div class="min-w-0 text-sm">
						<p class="flex items-center gap-1 truncate text-slate-700"><MapPin class="size-3.5 shrink-0 text-slate-400" /> {{ e.distrito_nome || "Sem distrito" }}</p>
						<p class="truncate text-xs text-slate-500">
							{{ e.owner || "Sem responsável" }}<template v-if="e.cidade || e.uf"> · {{ [e.cidade, e.uf].filter(Boolean).join("/") }}</template><template v-if="variosClientes"> · {{ e.cliente_nome }}</template>
						</p>
					</div>
					<ChevronRight class="hidden size-4 text-slate-300 group-hover:text-brand-500 lg:block" />
				</li>
			</ul>
			<div class="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
				<span>{{ filtrados.length }} equipamento(s){{ filtrados.length !== lista.length ? ` de ${lista.length}` : "" }}</span>
				<div v-if="totalPaginas > 1" class="flex items-center gap-2">
					<button class="btn-ghost px-2.5 py-1 text-xs" :disabled="pagina <= 1" @click="pagina--">Anterior</button>
					<span class="font-medium text-slate-700">{{ pagina }} / {{ totalPaginas }}</span>
					<button class="btn-ghost px-2.5 py-1 text-xs" :disabled="pagina >= totalPaginas" @click="pagina++">Próxima</button>
				</div>
			</div>
		</section>

		<p class="text-xs leading-relaxed text-slate-500">
			Faixas do laboratório: <b>Calibrado</b> (mais de 60 dias de validade) · <b>Alerta 60</b> (46 a 60 dias) · <b>Crítico</b> (até 45 dias) · <b>Vencido</b> ·
			<b>Agendado</b> (em atendimento no laboratório) · <b>Sem calibração</b> (nenhum certificado registrado). A planilha completa está em Relatórios.
		</p>

		<FormEquipamento v-if="novo" @fechar="novo = false" @salvo="(novo = false), carregar()" />
		<EnviarCertificado v-if="enviarCert" @fechar="enviarCert = false" @salvo="(enviarCert = false), carregar()" />
	</div>
</template>
