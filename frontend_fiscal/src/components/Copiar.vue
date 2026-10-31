<script setup>
import { Check, Copy } from "lucide-vue-next"
import { ref } from "vue"

const props = defineProps({ texto: String, rotulo: { type: String, default: "Copiar" } })
const copiado = ref(false)

async function copiar() {
	try {
		await navigator.clipboard.writeText(props.texto)
	} catch {
		// navegador sem permissão de área de transferência (http): cópia pelo método antigo
		const t = document.createElement("textarea")
		t.value = props.texto
		document.body.appendChild(t)
		t.select()
		document.execCommand("copy")
		t.remove()
	}
	copiado.value = true
	setTimeout(() => (copiado.value = false), 1800)
}
</script>

<template>
	<button class="btn-secundario px-2.5 py-1.5 text-xs" :disabled="!texto" @click="copiar">
		<Check v-if="copiado" class="size-3.5 text-emerald-500" /><Copy v-else class="size-3.5" />
		{{ copiado ? "Copiado!" : rotulo }}
	</button>
</template>
