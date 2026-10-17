<script setup>
import { Check, X } from "lucide-vue-next"

// Linha do tempo das etapas de uma OS. compacta = só a barra (para listas).
defineProps({ etapas: Array, atual: Number, compacta: Boolean })
</script>

<template>
	<div v-if="atual === -1" class="flex items-center gap-2 text-sm font-medium text-rose-600">
		<X class="size-4" /> Ordem cancelada
	</div>

	<div v-else-if="compacta" class="flex gap-1" :title="etapas[atual]">
		<span
			v-for="(e, i) in etapas"
			:key="e"
			class="h-1.5 flex-1 rounded-full"
			:class="i < atual ? 'bg-brand-500' : i === atual ? 'bg-brand-300' : 'bg-slate-200'"
		/>
	</div>

	<ol v-else class="flex w-full items-start overflow-x-auto pb-2">
		<li v-for="(e, i) in etapas" :key="e" class="flex min-w-[92px] flex-1 flex-col items-center text-center">
			<div class="flex w-full items-center">
				<span class="h-0.5 flex-1" :class="i === 0 ? 'opacity-0' : i <= atual ? 'bg-brand-500' : 'bg-slate-200'" />
				<span
					class="grid size-8 shrink-0 place-items-center rounded-full text-xs font-semibold ring-4 ring-white transition"
					:class="
						i < atual
							? 'bg-brand-600 text-white'
							: i === atual
								? 'bg-brand-600 text-white shadow-[0_0_0_6px] shadow-brand-100'
								: 'bg-slate-100 text-slate-400'
					"
				>
					<Check v-if="i < atual" class="size-4" />
					<span v-else>{{ i + 1 }}</span>
				</span>
				<span
					class="h-0.5 flex-1"
					:class="i === etapas.length - 1 ? 'opacity-0' : i < atual ? 'bg-brand-500' : 'bg-slate-200'"
				/>
			</div>
			<span
				class="mt-2 px-1 text-xs leading-tight"
				:class="i === atual ? 'font-semibold text-slate-900' : i < atual ? 'text-slate-600' : 'text-slate-400'"
				>{{ e }}</span
			>
		</li>
	</ol>
</template>
