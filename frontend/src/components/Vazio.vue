<script setup>
import { Inbox } from "lucide-vue-next"

defineProps({ titulo: { type: String, default: "Nada por aqui" }, texto: String, icone: [Object, Function] })
</script>

<template>
	<div class="flex flex-col items-center justify-center px-6 py-14 text-center">
		<span class="mb-4 grid size-12 place-items-center rounded-2xl bg-slate-100 text-slate-400">
			<component :is="icone || Inbox" class="size-6" />
		</span>
		<p class="font-medium text-slate-700">{{ titulo }}</p>
		<p v-if="texto" class="mt-1 max-w-sm text-sm text-slate-500">{{ texto }}</p>
		<div v-if="$slots.default" class="mt-5"><slot /></div>
	</div>
</template>
