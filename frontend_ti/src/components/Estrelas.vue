<script setup>
import { Star } from "lucide-vue-next"
import { ref } from "vue"

const modelo = defineModel({ type: Number, default: 0 })
const props = defineProps({ leitura: Boolean, tamanho: { type: String, default: "size-7" } })
const sobre = ref(0)
const ROTULOS = ["", "Muito ruim", "Ruim", "Ok", "Bom", "Excelente"]
</script>

<template>
	<div class="flex items-center gap-1" @mouseleave="sobre = 0">
		<button
			v-for="n in 5"
			:key="n"
			type="button"
			:disabled="props.leitura"
			class="transition disabled:cursor-default"
			:class="!props.leitura && 'hover:scale-110'"
			:aria-label="`${n} estrela(s)`"
			@mouseenter="!props.leitura && (sobre = n)"
			@click="modelo = n"
		>
			<Star :class="[tamanho, n <= (sobre || modelo) ? 'fill-amber-400 text-amber-400' : 'text-borda']" />
		</button>
		<span v-if="!props.leitura && (sobre || modelo)" class="ml-2 text-sm text-suave">{{ ROTULOS[sobre || modelo] }}</span>
	</div>
</template>
