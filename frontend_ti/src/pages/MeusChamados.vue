<script setup>
import { Plus, Ticket } from "lucide-vue-next"
import { onMounted, ref, watch } from "vue"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import LinhaChamado from "@/components/LinhaChamado.vue"
import Vazio from "@/components/Vazio.vue"

const aba = ref("abertos")
const lista = ref(null)
const ABAS = [
	{ id: "abertos", rotulo: "Em andamento" },
	{ id: "encerrados", rotulo: "Encerrados" },
	{ id: "todos", rotulo: "Todos" },
]
async function carregar() {
	lista.value = null
	lista.value = await api("meus_chamados", { filtro: aba.value })
}
onMounted(carregar)
watch(aba, carregar)
</script>

<template>
	<div class="space-y-5">
		<div class="flex flex-wrap items-end justify-between gap-4">
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-tinta">Meus chamados</h1>
				<p class="mt-1 text-sm text-suave">Acompanhe tudo o que você pediu à TI.</p>
			</div>
			<RouterLink to="/novo" class="btn-primario"><Plus class="size-4" /> Abrir chamado</RouterLink>
		</div>
		<nav class="flex gap-1 rounded-xl bg-realce p-1 sm:w-fit">
			<button
				v-for="a in ABAS"
				:key="a.id"
				class="flex-1 rounded-lg px-4 py-2 text-sm font-medium transition"
				:class="aba === a.id ? 'bg-superficie text-tinta shadow-sm' : 'text-suave hover:text-tinta'"
				@click="aba = a.id"
			>
				{{ a.rotulo }}
			</button>
		</nav>
		<div class="card overflow-hidden">
			<div v-if="!lista" class="p-5"><Esqueleto :linhas="5" classe="h-10" /></div>
			<Vazio v-else-if="!lista.length" :icone="Ticket" titulo="Nenhum chamado aqui" texto="Quando você abrir um chamado, ele aparece nesta lista." />
			<div v-else class="divide-y divide-borda"><LinhaChamado v-for="c in lista" :key="c.id" :c="c" /></div>
		</div>
	</div>
</template>
