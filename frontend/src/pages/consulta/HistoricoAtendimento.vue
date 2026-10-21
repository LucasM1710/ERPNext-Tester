<script setup>
import { MessagesSquare, Search } from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import { data, dataHora, relativo } from "@/format"
import { infoCliente, store } from "@/store"

// Histórico de atendimento: notas (aba Comentários) das oportunidades que a ER liberou para o
// Gestor/Líder no cadastro do acesso. O texto vem do ERP já sanitizado.
const lista = ref(null)
const aberta = ref(null)
const busca = ref("")

async function carregar() {
	lista.value = null
	lista.value = await api("consulta.historico_atendimento")
	if (!lista.value.some((o) => o.id === aberta.value)) aberta.value = lista.value[0]?.id || null
}
onMounted(carregar)
watch(() => store.cliente, carregar)

const filtradas = computed(() => {
	const q = busca.value.trim().toLowerCase()
	if (!q) return lista.value || []
	return (lista.value || []).filter((o) => [o.title, o.id, ...o.notas.map((n) => n.texto.replace(/<[^>]+>/g, " "))].some((v) => String(v || "").toLowerCase().includes(q)))
})
const atual = computed(() => (lista.value || []).find((o) => o.id === aberta.value) || null)
const variosClientes = computed(() => new Set((lista.value || []).map((o) => o.cliente)).size > 1)
const iniciais = (nome) => (nome || "ER").split(" ").filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase()
</script>

<template>
	<div class="space-y-5">
		<div class="relative overflow-hidden rounded-[28px] border border-slate-200 bg-white px-6 py-5 shadow-card">
			<div class="absolute top-1/2 -left-8 size-24 -translate-y-1/2 rounded-full bg-brand-100/60" />
			<div class="absolute -top-4 -right-4 size-20 rounded-full bg-cyan-100/70" />
			<span class="relative inline-flex items-center gap-1.5 rounded-full border border-brand-100 bg-brand-50 px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-brand-700 uppercase">
				<MessagesSquare class="size-3" /> Atendimento
			</span>
			<h1 class="relative mt-1.5 text-3xl font-semibold tracking-tight text-slate-900">Histórico de atendimento</h1>
			<p class="relative mt-1 text-sm text-slate-500">Os registros da ER Analítica sobre os seus contratos e serviços: o que foi combinado, agendado e realizado.</p>
		</div>

		<Esqueleto v-if="!lista" :linhas="6" />

		<div v-else-if="!lista.length" class="card grid place-items-center gap-2 p-10 text-center">
			<MessagesSquare class="size-8 text-slate-300" />
			<p class="font-medium text-slate-700">Nenhum histórico disponível</p>
			<p class="max-w-md text-sm text-slate-500">Quando a ER Analítica liberar o histórico de um atendimento para você, ele aparece aqui.</p>
		</div>

		<div v-else class="grid gap-5 lg:grid-cols-[340px_1fr]">
			<!-- Atendimentos -->
			<div class="card overflow-hidden">
				<div class="relative border-b border-slate-100 p-3">
					<Search class="pointer-events-none absolute top-1/2 left-6 size-4 -translate-y-1/2 text-slate-400" />
					<input v-model="busca" class="input pl-9" placeholder="Buscar nos registros…" />
				</div>
				<ul class="max-h-[640px] divide-y divide-slate-100 overflow-y-auto">
					<li v-if="!filtradas.length" class="px-4 py-6 text-center text-sm text-slate-500">Nada encontrado.</li>
					<li v-for="o in filtradas" :key="o.id">
						<button
							class="flex w-full flex-col gap-1 border-l-[3px] px-4 py-3 text-left transition"
							:class="o.id === aberta ? 'border-brand-600 bg-brand-50/60' : 'border-transparent hover:bg-slate-50'"
							@click="aberta = o.id"
						>
							<span class="font-medium text-slate-900">{{ o.title || o.id }}</span>
							<span v-if="variosClientes" class="text-xs text-slate-500">{{ infoCliente(o.cliente)?.nome || o.cliente }}</span>
							<span class="text-xs text-slate-400">
								{{ o.notas.length }} registro(s)<template v-if="o.ultima_nota"> · último {{ relativo(o.ultima_nota) }}</template>
							</span>
						</button>
					</li>
				</ul>
			</div>

			<!-- Linha do tempo -->
			<div v-if="atual" class="card p-5 sm:p-7">
				<div class="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-4">
					<div>
						<h2 class="text-lg font-semibold text-slate-900">{{ atual.title || atual.id }}</h2>
						<p class="text-xs text-slate-500">Atendimento {{ atual.id }} · aberto em {{ data(atual.transaction_date || atual.creation) }}</p>
					</div>
				</div>
				<p v-if="!atual.notas.length" class="py-10 text-center text-sm text-slate-500">Ainda não há registros neste atendimento.</p>
				<ol v-else class="relative mt-5 space-y-6 before:absolute before:top-2 before:bottom-2 before:left-[17px] before:w-px before:bg-slate-200">
					<li v-for="(n, i) in atual.notas" :key="i" class="relative flex gap-4">
						<span class="z-10 grid size-9 shrink-0 place-items-center rounded-full bg-brand-600 text-xs font-semibold text-white ring-4 ring-white">{{ iniciais(n.autor) }}</span>
						<div class="min-w-0 flex-1 rounded-2xl border border-slate-100 bg-slate-50/70 p-4">
							<p class="flex flex-wrap items-baseline justify-between gap-2 text-xs text-slate-500">
								<span><b class="font-semibold text-slate-800">{{ n.autor }}</b> · ER Analítica</span>
								<span :title="dataHora(n.data)">{{ dataHora(n.data) }}</span>
							</p>
							<div class="nota mt-2 text-sm text-slate-700" v-html="n.texto" />
						</div>
					</li>
				</ol>
			</div>
		</div>
	</div>
</template>

<style scoped>
.nota :deep(p) { margin: 0.25rem 0; line-height: 1.6; }
.nota :deep(ul), .nota :deep(ol) { margin: 0.4rem 0; padding-left: 1.3rem; }
.nota :deep(ul) { list-style: disc; }
.nota :deep(ol) { list-style: decimal; }
.nota :deep(li) { margin: 0.15rem 0; }
.nota :deep(strong), .nota :deep(b) { color: #0f172a; font-weight: 600; }
.nota :deep(em) { color: #64748b; }
.nota :deep(a) { color: #045a88; text-decoration: underline; }
</style>
