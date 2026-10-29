<script setup>
import { ArrowRight, CircleCheckBig, Inbox, MessageCircleWarning, Search } from "lucide-vue-next"
import { computed, onMounted, ref } from "vue"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import IconeCategoria from "@/components/IconeCategoria.vue"
import IconeEquipamento from "@/components/IconeEquipamento.vue"
import LinhaChamado from "@/components/LinhaChamado.vue"
import { eTecnico, store } from "@/store"

const chamados = ref(null)
const equipamentos = ref([])
const busca = ref("")
onMounted(async () => {
	chamados.value = await api("meus_chamados", { filtro: "abertos" })
	equipamentos.value = await api("inventario.meus_equipamentos")
})

const primeiroNome = computed(() => (store.contexto.usuario.nome || "").split(" ")[0])
const saudacao = (() => {
	const h = new Date().getHours()
	return h < 12 ? "Bom dia" : h < 18 ? "Boa tarde" : "Boa noite"
})()
const aguardando = computed(() => (chamados.value || []).filter((c) => c.status === "Aguardando Usuário"))
const categorias = computed(() => {
	const t = busca.value.trim().toLowerCase()
	return store.contexto.categorias.filter((c) => !t || (c.nome + " " + (c.descricao || "")).toLowerCase().includes(t))
})
const fila = computed(() => store.contexto.contadores)
</script>

<template>
	<div class="space-y-8">
		<!-- Cabeçalho -->
		<section class="relative overflow-hidden rounded-3xl border border-borda bg-gradient-to-br from-marca-600 via-marca-700 to-violet-800 p-6 text-white shadow-pop sm:p-8">
			<div class="pointer-events-none absolute -top-24 -right-24 size-72 rounded-full bg-white/10 blur-3xl" />
			<p class="text-sm text-marca-100">{{ saudacao }}, {{ primeiroNome }}</p>
			<h1 class="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">Como a TI pode ajudar hoje?</h1>
			<div class="relative mt-5 max-w-xl">
				<Search class="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-marca-200" />
				<input
					v-model="busca"
					class="w-full rounded-2xl border border-white/20 bg-white/10 py-3 pr-4 pl-12 text-white placeholder:text-marca-200 backdrop-blur focus:bg-white/15 focus:outline-none"
					placeholder="Descreva o problema: senha, impressora, Outlook…"
				/>
			</div>
		</section>

		<!-- Aguardando o colaborador -->
		<RouterLink
			v-for="c in aguardando"
			:key="c.id"
			:to="`/chamados/${c.id}`"
			class="flex items-center gap-4 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 transition hover:bg-amber-500/15"
		>
			<MessageCircleWarning class="size-6 shrink-0 text-amber-600 dark:text-amber-400" />
			<div class="min-w-0 flex-1">
				<p class="font-medium text-tinta">A TI está aguardando sua resposta</p>
				<p class="truncate text-sm text-suave">{{ c.id }} · {{ c.assunto }}</p>
			</div>
			<ArrowRight class="size-4 text-suave" />
		</RouterLink>

		<!-- Resumo da fila para a TI -->
		<RouterLink v-if="eTecnico()" to="/fila" class="card flex flex-wrap items-center gap-6 p-5 transition hover:shadow-pop">
			<span class="grid size-11 place-items-center rounded-xl bg-marca-500/10 text-marca-600 dark:text-marca-300"><Inbox class="size-5" /></span>
			<div class="flex-1">
				<p class="font-semibold text-tinta">Sua fila de atendimento</p>
				<p class="text-sm text-suave">{{ fila.fila_minha }} com você · {{ fila.fila_sem_responsavel }} sem responsável · {{ fila.fila_abertos }} abertos no total</p>
			</div>
			<span v-if="fila.fila_risco" class="rounded-full bg-rose-500 px-3 py-1 text-xs font-semibold text-white">{{ fila.fila_risco }} em risco/atrasados</span>
			<ArrowRight class="size-4 text-suave" />
		</RouterLink>

		<!-- Categorias -->
		<section>
			<h2 class="mb-3 text-sm font-semibold text-tinta">Abrir um chamado sobre…</h2>
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
				<RouterLink
					v-for="c in categorias"
					:key="c.nome"
					:to="{ path: '/novo', query: { categoria: c.nome } }"
					class="card group flex items-start gap-3 p-4 transition hover:-translate-y-0.5 hover:border-marca-300 hover:shadow-pop dark:hover:border-marca-700"
				>
					<span class="grid size-10 shrink-0 place-items-center rounded-xl bg-marca-500/10 text-marca-600 transition group-hover:bg-marca-600 group-hover:text-white dark:text-marca-300">
						<IconeCategoria :nome="c.icone" class="size-5" />
					</span>
					<span class="min-w-0">
						<span class="block text-sm font-semibold text-tinta">{{ c.nome }}</span>
						<span class="mt-0.5 line-clamp-2 block text-xs text-suave">{{ c.descricao }}</span>
					</span>
				</RouterLink>
				<RouterLink v-if="!categorias.length" :to="{ path: '/novo', query: { assunto: busca } }" class="card p-4 text-sm text-suave sm:col-span-2">
					Nenhuma categoria encontrada. <span class="font-medium text-marca-600 dark:text-marca-300">Abrir chamado sobre "{{ busca }}" →</span>
				</RouterLink>
			</div>
		</section>

		<!-- Equipamentos que estão com a pessoa -->
		<section v-if="equipamentos.length">
			<h2 class="mb-3 text-sm font-semibold text-tinta">Equipamentos com você</h2>
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
				<div v-for="e in equipamentos" :key="e.id" class="card flex items-center gap-3 p-4">
					<span class="grid size-10 shrink-0 place-items-center rounded-xl bg-realce text-suave"><IconeEquipamento :nome="e.icone" class="size-5" /></span>
					<div class="min-w-0 flex-1">
						<p class="text-sm font-semibold text-tinta">{{ e.nome }}</p>
						<p class="truncate text-xs text-suave">{{ e.modelo || e.tipo }}</p>
					</div>
					<RouterLink :to="{ path: '/novo', query: { equipamento: e.id } }" class="btn-fantasma px-2 py-1 text-xs">Pedir ajuda</RouterLink>
				</div>
			</div>
		</section>

		<!-- Meus chamados em andamento -->
		<section class="card overflow-hidden">
			<div class="flex items-center justify-between px-5 pt-5 pb-3">
				<h2 class="font-semibold text-tinta">Seus chamados em andamento</h2>
				<RouterLink to="/chamados" class="text-sm font-medium text-marca-600 hover:text-marca-700 dark:text-marca-300">Ver todos</RouterLink>
			</div>
			<div v-if="!chamados" class="px-5 pb-5"><Esqueleto :linhas="3" classe="h-10" /></div>
			<div v-else-if="!chamados.length" class="flex items-center gap-3 px-5 pb-6 text-sm text-emerald-700 dark:text-emerald-400">
				<CircleCheckBig class="size-5" /> Nenhum chamado em aberto. Tudo funcionando!
			</div>
			<div v-else class="divide-y divide-borda border-t border-borda">
				<LinhaChamado v-for="c in chamados" :key="c.id" :c="c" />
			</div>
		</section>
	</div>
</template>
