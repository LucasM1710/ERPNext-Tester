<script setup>
defineProps({
	titulo: String,
	valor: [String, Number],
	sufixo: String,
	descricao: String,
	icone: [Object, Function],
	tom: { type: String, default: "brand" }, // brand | verde | ambar | vermelho | violeta
	para: [String, Object],
})

const TONS = {
	brand: "bg-brand-50 text-brand-600",
	verde: "bg-emerald-50 text-emerald-600",
	ambar: "bg-amber-50 text-amber-600",
	vermelho: "bg-rose-50 text-rose-600",
	violeta: "bg-violet-50 text-violet-600",
}
</script>

<template>
	<component
		:is="para ? 'RouterLink' : 'div'"
		:to="para"
		class="card group flex flex-col gap-4 p-5 transition"
		:class="para && 'hover:-translate-y-0.5 hover:shadow-pop'"
	>
		<div class="flex items-start justify-between gap-3">
			<p class="text-sm font-medium text-slate-500">{{ titulo }}</p>
			<span v-if="icone" class="grid size-9 shrink-0 place-items-center rounded-xl" :class="TONS[tom]">
				<component :is="icone" class="size-[18px]" />
			</span>
		</div>
		<div>
			<p class="text-3xl font-semibold tracking-tight text-slate-900 tabular-nums">
				{{ valor }}<span v-if="sufixo" class="ml-0.5 text-lg font-medium text-slate-400">{{ sufixo }}</span>
			</p>
			<p v-if="descricao" class="mt-1 text-xs text-slate-500">{{ descricao }}</p>
		</div>
		<slot />
	</component>
</template>
