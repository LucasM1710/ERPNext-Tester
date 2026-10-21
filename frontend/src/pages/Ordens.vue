<script setup>
import { CalendarClock, ClipboardList, Plus, ReceiptText, TriangleAlert } from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import LinhaEtapas from "@/components/LinhaEtapas.vue"
import Vazio from "@/components/Vazio.vue"
import { data, relativo } from "@/format"
import { CONSULTA } from "@/modo"
import { podeEditar } from "@/store"

const route = useRoute()
const router = useRouter()
const lista = ref(null)
const aba = ref(route.query.aba || "andamento")

const ABAS = [
	{ id: "andamento", rotulo: "Em andamento", filtro: (o) => !o.finalizada },
	{ id: "aprovacao", rotulo: "Aguardando você", filtro: (o) => o.status_orcamento === "Aguardando Cliente" },
	{ id: "finalizadas", rotulo: "Finalizadas", filtro: (o) => o.finalizada },
	{ id: "todas", rotulo: "Todas", filtro: () => true },
]

onMounted(async () => (lista.value = await api("ordens")))
watch(aba, () => router.replace({ query: { aba: aba.value } }))

const contagem = computed(() => Object.fromEntries(ABAS.map((a) => [a.id, (lista.value || []).filter(a.filtro).length])))
const filtradas = computed(() => (lista.value || []).filter(ABAS.find((a) => a.id === aba.value).filtro))
</script>

<template>
	<div class="space-y-5">
		<div class="flex flex-wrap items-end justify-between gap-4">
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-slate-900">Ordens de Serviço</h1>
				<p class="mt-1 text-sm text-slate-500">Acompanhe cada equipamento desde o recebimento até a devolução.</p>
			</div>
			<RouterLink v-if="podeEditar() && !CONSULTA" to="/solicitar" class="btn-primary"><Plus class="size-4" /> Nova solicitação</RouterLink>
		</div>

		<nav class="flex gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1">
			<button
				v-for="a in ABAS"
				:key="a.id"
				class="flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium whitespace-nowrap transition"
				:class="aba === a.id ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'"
				@click="aba = a.id"
			>
				{{ a.rotulo }}
				<span
					class="rounded-full px-1.5 text-[11px] tabular-nums"
					:class="a.id === 'aprovacao' && contagem[a.id] ? 'bg-amber-500 text-white' : 'bg-slate-200/80 text-slate-600'"
					>{{ contagem[a.id] }}</span
				>
			</button>
		</nav>

		<div v-if="!lista" class="grid gap-4 md:grid-cols-2">
			<div v-for="i in 4" :key="i" class="card p-5"><Esqueleto :linhas="4" /></div>
		</div>

		<div v-else-if="!filtradas.length" class="card">
			<Vazio :icone="ClipboardList" titulo="Nenhuma ordem aqui" :texto="CONSULTA ? 'As ordens de serviço do laboratório aparecerão aqui.' : 'Quando você solicitar um serviço, ele aparecerá nesta lista.'">
				<RouterLink v-if="!CONSULTA" to="/solicitar" class="btn-primary"><Plus class="size-4" /> Solicitar serviço</RouterLink>
			</Vazio>
		</div>

		<div v-else class="grid gap-4 md:grid-cols-2">
			<RouterLink v-for="o in filtradas" :key="o.id" :to="`/ordens/${o.id}`" class="card group flex flex-col gap-4 p-5 transition hover:-translate-y-0.5 hover:shadow-pop">
				<div class="flex items-start justify-between gap-3">
					<div>
						<p class="font-semibold text-slate-900">{{ o.id }}</p>
						<p class="text-sm text-slate-500">{{ o.tipo }} · {{ o.qtd_itens }} equipamento(s)<span v-if="o.local_atendimento === 'In Loco'"> · in loco</span></p>
					</div>
					<Etiqueta :valor="o.status" />
				</div>

				<LinhaEtapas :etapas="o.etapas" :atual="o.etapa_atual" compacta />

				<div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
					<span>Aberta em {{ data(o.data_solicitacao) }}</span>
					<span v-if="o.data_prevista && !o.finalizada" class="flex items-center gap-1" :class="o.atrasada && 'font-medium text-rose-600'">
						<TriangleAlert v-if="o.atrasada" class="size-3.5" /><CalendarClock v-else class="size-3.5" />
						Previsão {{ data(o.data_prevista) }} ({{ relativo(o.data_prevista) }})
					</span>
					<span v-if="o.data_conclusao">Concluída em {{ data(o.data_conclusao) }}</span>
				</div>

				<div v-if="o.status_orcamento === 'Aguardando Cliente'" class="-mx-5 -mb-5 flex items-center gap-2 rounded-b-2xl border-t border-amber-100 bg-amber-50 px-5 py-3 text-sm font-medium text-amber-800">
					<ReceiptText class="size-4" /> Orçamento aguardando sua aprovação
				</div>
			</RouterLink>
		</div>
	</div>
</template>
