<script setup>
import { computed } from "vue"
import { iniciais } from "@/format"

const props = defineProps({ nome: String, tamanho: { type: String, default: "size-8" } })
// cor estável por pessoa
const PALETA = ["bg-marca-500", "bg-emerald-500", "bg-amber-500", "bg-rose-500", "bg-sky-500", "bg-violet-500", "bg-teal-500"]
const cor = computed(() => PALETA[[...(props.nome || "")].reduce((s, c) => s + c.charCodeAt(0), 0) % PALETA.length])
</script>

<template>
	<span class="grid shrink-0 place-items-center rounded-full text-[11px] font-semibold text-white" :class="[tamanho, nome ? cor : 'bg-slate-400']" :title="nome">
		{{ nome ? iniciais(nome) : "?" }}
	</span>
</template>
