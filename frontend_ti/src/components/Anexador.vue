<script setup>
import { Paperclip, X } from "lucide-vue-next"
import { onBeforeUnmount, onMounted, ref } from "vue"
import { tamanho } from "@/format"

// Arquivos para enviar: clique, arraste e solte, ou cole um print (Ctrl+V) em qualquer lugar da página.
const arquivos = defineModel({ type: Array, default: () => [] })
const props = defineProps({ compacto: Boolean })
const arrastando = ref(false)
const entrada = ref(null)

function adicionar(lista) {
	for (const f of lista) {
		if (f.size > 25 * 1024 * 1024) continue
		const nome = f.name && f.name !== "image.png" ? f.name : `print-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.png`
		arquivos.value = [...arquivos.value, new File([f], nome, { type: f.type })]
	}
}
function colar(e) {
	const itens = [...(e.clipboardData?.items || [])].filter((i) => i.kind === "file").map((i) => i.getAsFile())
	if (itens.length) adicionar(itens)
}
onMounted(() => document.addEventListener("paste", colar))
onBeforeUnmount(() => document.removeEventListener("paste", colar))
</script>

<template>
	<div>
		<input ref="entrada" type="file" multiple class="hidden" @change="adicionar($event.target.files)" />
		<button v-if="props.compacto" type="button" class="btn-fantasma p-2" title="Anexar arquivo (ou cole um print com Ctrl+V)" @click="entrada.click()">
			<Paperclip class="size-4" />
		</button>
		<div
			v-else
			class="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-4 py-5 text-center transition"
			:class="arrastando ? 'border-marca-400 bg-marca-500/5' : 'border-borda hover:bg-realce'"
			@click="entrada.click()"
			@dragover.prevent="arrastando = true"
			@dragleave="arrastando = false"
			@drop.prevent="(arrastando = false), adicionar($event.dataTransfer.files)"
		>
			<Paperclip class="mb-1.5 size-5 text-suave" />
			<p class="text-sm font-medium text-texto">Arraste arquivos, clique para escolher ou cole um print (Ctrl+V)</p>
			<p class="text-xs text-suave">Fotos, prints, PDFs · até 25 MB cada</p>
		</div>
		<ul v-if="arquivos.length" class="mt-2 flex flex-wrap gap-2">
			<li v-for="(a, i) in arquivos" :key="i" class="flex items-center gap-2 rounded-lg border border-borda bg-realce px-2.5 py-1 text-xs text-texto">
				<span class="max-w-48 truncate">{{ a.name }}</span>
				<span class="text-suave">{{ tamanho(a.size) }}</span>
				<button type="button" class="text-suave hover:text-rose-500" aria-label="Remover" @click="arquivos = arquivos.filter((_, j) => j !== i)"><X class="size-3.5" /></button>
			</li>
		</ul>
	</div>
</template>
