<script setup>
import { computed } from "vue"
import { classeTom } from "@/cores"

const props = defineProps({ valor: String, ponto: { type: Boolean, default: true } })
const classe = computed(() => classeTom(props.valor))
</script>

<template>
	<span
		v-if="valor"
		class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ring-1 ring-inset"
		:class="classe"
	>
		<span v-if="ponto" class="size-1.5 rounded-full bg-current opacity-80" />
		<slot>{{ valor }}</slot>
	</span>
</template>
