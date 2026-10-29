<script setup>
import { Inbox, Plus, RefreshCw, Search } from "lucide-vue-next"
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { useRouter } from "vue-router"
import { api } from "@/api"
import Avatar from "@/components/Avatar.vue"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import IconeCategoria from "@/components/IconeCategoria.vue"
import Vazio from "@/components/Vazio.vue"
import { COR_PRIORIDADE } from "@/cores"
import { prazo, relativo } from "@/format"
import { store } from "@/store"

const router = useRouter()
const aba = ref(sessionStorage.getItem("ti.fila.aba") || "minha")
const busca = ref("")
const categoria = ref("")
const prioridade = ref("")
const lista = ref(null)
const atualizando = ref(false)

const cont = computed(() => store.contexto.contadores)
const ABAS = computed(() => [
	{ id: "minha", rotulo: "Minha fila", n: cont.value.fila_minha },
	{ id: "sem_responsavel", rotulo: "Sem responsável", n: cont.value.fila_sem_responsavel, destaque: true },
	{ id: "risco", rotulo: "Em risco / atrasados", n: cont.value.fila_risco, perigo: true },
	{ id: "abertos", rotulo: "Todos abertos", n: cont.value.fila_abertos },
	{ id: "encerrados", rotulo: "Encerrados (60 dias)" },
])

async function carregar() {
	atualizando.value = true
	try {
		lista.value = await api("fila", { aba: aba.value, busca: busca.value, categoria: categoria.value, prioridade: prioridade.value })
		store.contexto = await api("contexto")
	} finally {
		atualizando.value = false
	}
}
let atraso, relogio
watch([aba, categoria, prioridade], () => {
	sessionStorage.setItem("ti.fila.aba", aba.value)
	lista.value = null
	carregar()
})
watch(busca, () => {
	clearTimeout(atraso)
	atraso = setTimeout(carregar, 300)
})
onMounted(() => {
	carregar()
	relogio = setInterval(() => document.visibilityState === "visible" && carregar(), 60000)
})
onBeforeUnmount(() => clearInterval(relogio))

// o prazo que importa agora: a 1ª resposta enquanto não houve resposta; depois, a resolução
function prazoAtual(c) {
	if (!c.aberto) return null
	return c.respondido ? { rotulo: "Resolução", data: c.prazo_resolucao, sla: c.sla_resolucao } : { rotulo: "1ª resposta", data: c.prazo_resposta, sla: c.sla_resposta }
}
const COR_TEXTO_SLA = { Violado: "text-rose-600 dark:text-rose-400", "Em Risco": "text-amber-600 dark:text-amber-400" }
</script>

<template>
	<div class="space-y-5">
		<div class="flex flex-wrap items-end justify-between gap-4">
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-tinta">Fila de atendimento</h1>
				<p class="mt-1 text-sm text-suave">Ordenada pelo que vence primeiro. Atualiza sozinha a cada minuto.</p>
			</div>
			<div class="flex gap-2">
				<button class="btn-secundario" :disabled="atualizando" title="Atualizar" @click="carregar"><RefreshCw class="size-4" :class="atualizando && 'animate-spin'" /></button>
				<RouterLink to="/novo" class="btn-primario"><Plus class="size-4" /> Registrar chamado</RouterLink>
			</div>
		</div>

		<nav class="flex gap-1 overflow-x-auto rounded-xl bg-realce p-1">
			<button
				v-for="a in ABAS"
				:key="a.id"
				class="flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium whitespace-nowrap transition"
				:class="aba === a.id ? 'bg-superficie text-tinta shadow-sm' : 'text-suave hover:text-tinta'"
				@click="aba = a.id"
			>
				{{ a.rotulo }}
				<span
					v-if="a.n !== undefined"
					class="rounded-full px-1.5 text-[11px] tabular-nums"
					:class="a.perigo && a.n ? 'bg-rose-500 text-white' : a.destaque && a.n ? 'bg-amber-500 text-white' : 'bg-borda text-suave'"
					>{{ a.n }}</span
				>
			</button>
		</nav>

		<div class="card overflow-hidden">
			<div class="flex flex-wrap items-center gap-3 border-b border-borda p-3">
				<div class="relative min-w-[220px] flex-1">
					<Search class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-suave" />
					<input v-model="busca" class="campo pl-9" placeholder="Buscar por número, título, pessoa, departamento…" />
				</div>
				<select v-model="categoria" class="campo w-auto">
					<option value="">Todas as categorias</option>
					<option v-for="c in store.contexto.categorias" :key="c.nome">{{ c.nome }}</option>
				</select>
				<select v-model="prioridade" class="campo w-auto">
					<option value="">Todas as prioridades</option><option>Crítica</option><option>Alta</option><option>Média</option><option>Baixa</option>
				</select>
			</div>

			<div v-if="!lista" class="p-5"><Esqueleto :linhas="7" classe="h-10" /></div>
			<Vazio v-else-if="!lista.length" :icone="Inbox" titulo="Fila vazia" texto="Nenhum chamado nesta visão. Bom trabalho!" />
			<div v-else class="overflow-x-auto">
				<table class="w-full min-w-[860px]">
					<thead class="border-b border-borda bg-realce/50">
						<tr>
							<th class="th w-2 p-0"></th>
							<th class="th">Chamado</th>
							<th class="th">Solicitante</th>
							<th class="th">Prazo</th>
							<th class="th">Status</th>
							<th class="th">Responsável</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-borda">
						<tr v-for="c in lista" :key="c.id" class="cursor-pointer transition hover:bg-realce" @click="router.push(`/chamados/${c.id}`)">
							<td class="w-1 p-0"><div class="h-12 w-1 rounded-r" :style="{ background: COR_PRIORIDADE[c.prioridade] }" :title="`Prioridade ${c.prioridade}`" /></td>
							<td class="td">
								<div class="flex items-center gap-3">
									<IconeCategoria :nome="c.icone" class="size-4 shrink-0 text-suave" />
									<div class="min-w-0">
										<p class="max-w-md truncate font-medium text-tinta">{{ c.assunto }}</p>
										<p class="text-xs text-suave"><span class="font-mono">{{ c.id }}</span> · {{ c.prioridade }} · {{ c.canal }} · {{ relativo(c.atualizado_em) }}</p>
									</div>
								</div>
							</td>
							<td class="td">
								<p class="text-tinta">{{ c.solicitante_nome }}</p>
								<p class="text-xs text-suave">{{ c.departamento || "—" }}</p>
							</td>
							<td class="td">
								<template v-if="prazoAtual(c)">
									<p class="text-xs text-suave">{{ prazoAtual(c).rotulo }}</p>
									<p class="font-medium whitespace-nowrap" :class="COR_TEXTO_SLA[prazoAtual(c).sla] || 'text-tinta'">
										{{ c.status === "Aguardando Usuário" && c.respondido ? "pausado" : prazo(prazoAtual(c).data) }}
									</p>
								</template>
								<Etiqueta v-else :valor="c.sla_resolucao" :ponto="false" />
							</td>
							<td class="td"><Etiqueta :valor="c.status" /></td>
							<td class="td">
								<div v-if="c.responsavel_nome" class="flex items-center gap-2"><Avatar :nome="c.responsavel_nome" tamanho="size-6" /><span class="text-texto">{{ c.responsavel_nome.split(" ")[0] }}</span></div>
								<span v-else class="text-xs font-medium text-amber-600 dark:text-amber-400">ninguém</span>
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</div>
	</div>
</template>
