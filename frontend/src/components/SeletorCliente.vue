<script setup>
import { Building2 } from "lucide-vue-next"
import { definirCliente, store } from "@/store"

// Necessário antes de gravar quando o usuário tem vários clientes e está vendo "Todos".
const modelo = defineModel({ type: String })
</script>

<template>
	<div class="rounded-xl border border-amber-200 bg-amber-50/60 p-3">
		<label class="label flex items-center gap-1.5 text-amber-800"><Building2 class="size-3.5" /> Para qual cliente?</label>
		<select v-model="modelo" class="input" @change="definirCliente(modelo)">
			<option disabled value="">Selecione…</option>
			<option v-for="c in store.contexto.clientes" :key="c.id" :value="c.id">{{ c.nome }}</option>
		</select>
	</div>
</template>
