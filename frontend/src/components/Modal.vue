<script setup>
import { X } from "lucide-vue-next"
import { onBeforeUnmount, onMounted } from "vue"

const props = defineProps({ titulo: String, subtitulo: String, largura: { type: String, default: "max-w-lg" } })
const emit = defineEmits(["fechar"])

function tecla(e) {
	if (e.key === "Escape") emit("fechar")
}
onMounted(() => document.addEventListener("keydown", tecla))
onBeforeUnmount(() => document.removeEventListener("keydown", tecla))
</script>

<template>
	<Teleport to="body">
		<div class="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-4">
			<div class="absolute inset-0 bg-slate-900/40 backdrop-blur-[2px]" @click="emit('fechar')" />
			<div
				class="relative flex max-h-[92vh] w-full flex-col rounded-t-2xl bg-white shadow-pop sm:rounded-2xl"
				:class="props.largura"
			>
				<div class="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-4">
					<div>
						<h2 class="text-base font-semibold text-slate-900">{{ titulo }}</h2>
						<p v-if="subtitulo" class="mt-0.5 text-sm text-slate-500">{{ subtitulo }}</p>
					</div>
					<button class="btn-ghost -mr-2 p-2" aria-label="Fechar" @click="emit('fechar')"><X class="size-4" /></button>
				</div>
				<div class="overflow-y-auto px-6 py-5"><slot /></div>
				<div v-if="$slots.rodape" class="flex justify-end gap-2 border-t border-slate-100 px-6 py-4">
					<slot name="rodape" />
				</div>
			</div>
		</div>
	</Teleport>
</template>
