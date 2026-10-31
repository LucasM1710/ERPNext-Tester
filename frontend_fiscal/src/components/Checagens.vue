<script setup>
import { CircleAlert, CircleCheck, Info, TriangleAlert } from "lucide-vue-next"
import { NIVEL } from "@/cores"

defineProps({ itens: { type: Array, default: () => [] }, compacto: Boolean })
const emit = defineEmits(["acao"])
const ICONE = { erro: CircleAlert, aviso: TriangleAlert, info: Info, ok: CircleCheck }
const BOTAO = { cadastro: "Completar cadastro", config: "Abrir configuração" }
</script>

<template>
	<ul class="space-y-1.5">
		<li v-for="(c, i) in itens" :key="i" class="flex items-start gap-2.5 rounded-xl border px-3 py-2 text-sm" :class="NIVEL[c.nivel].fundo">
			<component :is="ICONE[c.nivel]" class="mt-0.5 size-4 shrink-0" :class="NIVEL[c.nivel].cor" />
			<div class="min-w-0 flex-1">
				<p class="text-tinta">{{ c.texto }}</p>
				<p v-if="c.dica && !compacto" class="mt-0.5 text-xs text-suave">{{ c.dica }}</p>
			</div>
			<button v-if="c.acao && (BOTAO[c.acao] || c.acao.startsWith('item:'))" class="shrink-0 text-xs font-semibold text-marca-700 hover:underline dark:text-marca-300" @click="emit('acao', c.acao)">
				{{ BOTAO[c.acao] || "Abrir item" }}
			</button>
		</li>
	</ul>
</template>
