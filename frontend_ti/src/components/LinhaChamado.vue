<script setup>
import { ChevronRight, MessageCircleWarning } from "lucide-vue-next"
import Avatar from "@/components/Avatar.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import IconeCategoria from "@/components/IconeCategoria.vue"
import { relativo } from "@/format"

defineProps({ c: { type: Object, required: true } })
</script>

<template>
	<RouterLink :to="`/chamados/${c.id}`" class="group flex items-center gap-4 px-5 py-4 transition hover:bg-realce">
		<span class="grid size-10 shrink-0 place-items-center rounded-xl bg-marca-500/10 text-marca-600 dark:text-marca-300">
			<IconeCategoria :nome="c.icone" class="size-5" />
		</span>
		<div class="min-w-0 flex-1">
			<p class="truncate text-sm font-medium text-tinta">{{ c.assunto }}</p>
			<p class="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-suave">
				<span class="font-mono">{{ c.id }}</span><span>·</span><span>{{ c.categoria || "Sem categoria" }}</span><span>·</span><span>atualizado {{ relativo(c.atualizado_em) }}</span>
			</p>
		</div>
		<span v-if="c.status === 'Aguardando Usuário'" class="hidden items-center gap-1 text-xs font-medium text-amber-600 sm:flex dark:text-amber-400">
			<MessageCircleWarning class="size-4" /> Responda a TI
		</span>
		<Etiqueta :valor="c.status" />
		<Avatar v-if="c.responsavel_nome" :nome="c.responsavel_nome" tamanho="size-7" class="hidden sm:grid" />
		<ChevronRight class="size-4 text-suave transition group-hover:translate-x-0.5" />
	</RouterLink>
</template>
