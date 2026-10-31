<script setup>
defineProps({ rotulo: String, valor: [String, Number], detalhe: String, icone: [Object, Function], tom: { type: String, default: "marca" }, destaque: Boolean })
const TONS = {
	marca: "bg-marca-500/12 text-marca-600 dark:text-marca-300",
	verde: "bg-emerald-500/12 text-emerald-600 dark:text-emerald-300",
	ambar: "bg-amber-500/14 text-amber-600 dark:text-amber-300",
	vermelho: "bg-rose-500/12 text-rose-600 dark:text-rose-300",
	azul: "bg-blue-500/12 text-blue-600 dark:text-blue-300",
	violeta: "bg-violet-500/12 text-violet-600 dark:text-violet-300",
}
</script>

<template>
	<div class="card flex items-start gap-3 p-4" :class="destaque && 'ring-2 ring-marca-500/30'">
		<span class="grid size-10 shrink-0 place-items-center rounded-xl" :class="TONS[tom]"><component :is="icone" class="size-5" /></span>
		<div class="min-w-0">
			<p class="text-xs font-medium text-suave">{{ rotulo }}</p>
			<p class="mt-0.5 truncate text-xl font-semibold text-tinta tabular-nums">{{ valor }}</p>
			<p v-if="detalhe" class="truncate text-xs text-suave">{{ detalhe }}</p>
		</div>
	</div>
</template>
