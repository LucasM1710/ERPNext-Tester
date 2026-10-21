<script setup>
import { FileSpreadsheet, FileText } from "lucide-vue-next"
import { computed, onMounted, reactive, ref, watch } from "vue"
import { api, urlApi } from "@/api"
import TabelaPaginada from "@/components/consulta/TabelaPaginada.vue"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import { data } from "@/format"
import { clienteAtual, store } from "@/store"

const STATUS = ["Vencido", "Crítico", "Alerta 60", "Agendado", "Calibrado", "Sem calibração"]
const filtros = reactive({ de: "", ate: "", owner: "", status_calibracao: "", origem: "" })
const r = ref(null)
const carregando = ref(false)
const owners = ref([])

async function carregar() {
	carregando.value = true
	try {
		r.value = await api("consulta.relatorio", { filtros: { ...filtros } })
		if (!owners.value.length) owners.value = [...new Set(r.value.equipamentos.map((e) => e.owner).filter(Boolean))].sort()
	} finally {
		carregando.value = false
	}
}
onMounted(carregar)
watch(filtros, carregar)

const distritoAtual = computed(() => (clienteAtual()?.distritos || []).find((d) => d.id === store.distrito)?.nome)

function exportar(formato) {
	window.open(urlApi("consulta.exportar", { formato, filtros: { ...filtros } }), "_blank")
}

const colEquip = [
	{ rotulo: "Status", valor: (e) => e.status_calibracao },
	{ rotulo: "Calibrado por", valor: (e) => e.vendor },
	{ rotulo: "Nº de série", valor: (e) => e.numero_serie || "—" },
	{ rotulo: "TAG", valor: (e) => e.tag },
	{ rotulo: "Equipamento", valor: (e) => e.descricao, classe: () => "font-semibold text-slate-900" },
	{ rotulo: "Marca", valor: (e) => e.fabricante || "—" },
	{ rotulo: "Modelo", valor: (e) => e.modelo || "—" },
	{ rotulo: "Últ. cal.", valor: (e) => data(e.ultima_calibracao) },
	{ rotulo: "Próx. cal.", valor: (e) => data(e.proxima_calibracao) },
	{ rotulo: "Certificado", valor: (e) => e.certificado || "—" },
	{ rotulo: "Responsável", valor: (e) => e.owner || "—" },
	{ rotulo: "Distrito", valor: (e) => e.distrito_nome || "—" },
	{ rotulo: "UF", valor: (e) => e.uf || "—" },
	{ rotulo: "Cidade", valor: (e) => e.cidade || "—" },
	{ rotulo: "Obs.", valor: (e) => e.observacao || "—" },
]
const colOwner = [
	{ rotulo: "Responsável", valor: (g) => g.owner, classe: () => "font-semibold text-slate-900" },
	{ rotulo: "Distrito", valor: (g) => g.distrito },
	{ rotulo: "Total", valor: (g) => g.total },
	{ rotulo: "Calibrado", valor: (g) => g.Calibrado + g["Alerta 60"] },
	{ rotulo: "Crítico", valor: (g) => g["Crítico"] },
	{ rotulo: "Vencido", valor: (g) => g.Vencido, classe: (g) => (g.Vencido ? "font-semibold text-rose-600" : "text-slate-700") },
	{ rotulo: "Agendado", valor: (g) => g.Agendado },
	{ rotulo: "Sem calibração", valor: (g) => g["Sem calibração"] },
]
const colVenc = [
	{ rotulo: "Faixa", valor: (e) => e.faixa },
	{ rotulo: "Nº de série", valor: (e) => e.numero_serie || "—" },
	{ rotulo: "Equipamento", valor: (e) => `${e.descricao} · ${e.tag}` },
	{ rotulo: "Responsável", valor: (e) => e.owner || "—" },
	{ rotulo: "Próx. cal.", valor: (e) => data(e.proxima_calibracao) },
	{ rotulo: "Dias p/ vencer", valor: (e) => e.dias_para_vencer, classe: (e) => (e.dias_para_vencer < 0 ? "font-semibold text-rose-600" : "font-semibold text-orange-600") },
	{ rotulo: "Status", valor: (e) => e.status_calibracao },
]
</script>

<template>
	<div class="space-y-5">
		<div class="flex flex-wrap items-end justify-between gap-4 border-b border-slate-200 pb-5">
			<div>
				<h1 class="text-xl font-semibold tracking-tight text-slate-900">Relatórios</h1>
				<p class="mt-0.5 text-sm text-slate-500">
					Consulta, filtro e exportação para Excel ou PDF{{ distritoAtual ? ` · distrito ${distritoAtual}` : "" }}.
				</p>
			</div>
			<div class="flex gap-2">
				<button class="btn-secondary" :disabled="!r" @click="exportar('xlsx')"><FileSpreadsheet class="size-4" /> Exportar Excel</button>
				<button class="btn-primary" :disabled="!r" @click="exportar('pdf')"><FileText class="size-4" /> Exportar PDF</button>
			</div>
		</div>

		<div class="grid gap-3 md:grid-cols-3 xl:grid-cols-5">
			<div><label class="label">Calibrado de</label><input v-model="filtros.de" type="date" class="input" /></div>
			<div><label class="label">Até</label><input v-model="filtros.ate" type="date" class="input" /></div>
			<div>
				<label class="label">Responsável</label>
				<select v-model="filtros.owner" class="input">
					<option value="">Todos os responsáveis</option>
					<option v-for="o in owners" :key="o" :value="o">{{ o }}</option>
				</select>
			</div>
			<div>
				<label class="label">Status</label>
				<select v-model="filtros.status_calibracao" class="input">
					<option value="">Todos os status</option>
					<option v-for="s in STATUS" :key="s" :value="s">{{ s }}</option>
				</select>
			</div>
			<div>
				<label class="label">Calibrado por</label>
				<select v-model="filtros.origem" class="input">
					<option value="">ER Analítica e terceiros</option>
					<option value="laboratorio">ER Analítica</option>
					<option value="cliente">Terceiros</option>
				</select>
			</div>
		</div>
		<p class="-mt-2 text-xs text-slate-500">O período filtra pela data da última calibração. O distrito segue o seletor do topo da página.</p>

		<div v-if="!r" class="card p-5"><Esqueleto :linhas="8" /></div>
		<div v-else class="space-y-5" :class="carregando && 'opacity-60'">
			<TabelaPaginada titulo="Calibrações e situação por equipamento" :colunas="colEquip" :linhas="r.equipamentos" :chave="(e) => e.id">
				<template #Status="{ linha }"><Etiqueta :valor="linha.status_calibracao" /></template>
			</TabelaPaginada>
			<TabelaPaginada titulo="Equipamentos por responsável" subtitulo="Responsável definido no distrito" :colunas="colOwner" :linhas="r.por_owner" />
			<TabelaPaginada titulo="Vencimentos 30 / 60 / 90 dias" subtitulo="Inclui os já vencidos" :colunas="colVenc" :linhas="r.vencimentos" :chave="(e) => e.id">
				<template #Faixa="{ linha }"><Etiqueta :valor="linha.dias_para_vencer < 0 ? 'Vencido' : linha.dias_para_vencer <= 45 ? 'Crítico' : 'Alerta 60'">{{ linha.faixa }}</Etiqueta></template>
				<template #Status="{ linha }"><Etiqueta :valor="linha.status_calibracao" /></template>
			</TabelaPaginada>
		</div>
	</div>
</template>
