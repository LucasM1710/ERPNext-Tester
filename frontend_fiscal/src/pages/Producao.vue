<script setup>
import { CircleCheck, CircleDashed, ExternalLink, FlaskConical, Rocket } from "lucide-vue-next"
import { computed, onMounted, ref } from "vue"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"

const p = ref(null)
const feitos = computed(() => p.value?.passos.filter((x) => x.ok).length || 0)
onMounted(async () => (p.value = await api("prontidao")))

const AMBIENTES = [
	{ nome: "Simulação", texto: "Tudo acontece só aqui no ERP. Serve para treinar a equipe e validar o processo. Não precisa de nada contratado." },
	{ nome: "Homologação", texto: "Testes de verdade no provedor, na SEFAZ e no banco, mas sem valor fiscal. Precisa do certificado e das contas contratadas." },
	{ nome: "Produção", texto: "Notas e boletos reais. Só depois de alguns testes bem-sucedidos em homologação." },
]
</script>

<template>
	<div class="space-y-6">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight text-tinta">Ir para produção</h1>
			<p class="mt-1 text-sm text-suave">O que falta para emitir notas e boletos de verdade. Página para o gestor e o contador.</p>
		</div>

		<div class="grid gap-3 sm:grid-cols-3">
			<div v-for="(a, k) in AMBIENTES" :key="a.nome" class="card p-4" :class="p?.ambiente === a.nome && 'ring-2 ring-marca-500/40'">
				<p class="flex items-center gap-2 font-semibold text-tinta">
					<component :is="k === 0 ? FlaskConical : k === 1 ? CircleDashed : Rocket" class="size-4 text-marca-600" /> {{ a.nome }}
					<span v-if="p?.ambiente === a.nome" class="ml-auto rounded-full bg-marca-500/15 px-2 py-0.5 text-[10px] font-semibold text-marca-700 dark:text-marca-300">ATUAL</span>
				</p>
				<p class="mt-1 text-sm text-suave">{{ a.texto }}</p>
			</div>
		</div>

		<section class="card p-5">
			<div class="mb-4 flex flex-wrap items-center gap-3">
				<h2 class="text-sm font-semibold text-tinta">Checklist</h2>
				<div v-if="p" class="flex flex-1 items-center gap-3">
					<div class="h-2 flex-1 overflow-hidden rounded-full bg-realce"><div class="h-full rounded-full bg-marca-500 transition-all" :style="{ width: `${(feitos / p.passos.length) * 100}%` }" /></div>
					<span class="text-xs text-suave tabular-nums">{{ feitos }}/{{ p.passos.length }}</span>
				</div>
			</div>
			<Esqueleto v-if="!p" :linhas="6" />
			<ul v-else class="divide-y divide-borda">
				<li v-for="(x, k) in p.passos" :key="k" class="flex items-start gap-3 py-3">
					<CircleCheck v-if="x.ok" class="mt-0.5 size-5 shrink-0 text-emerald-500" /><CircleDashed v-else class="mt-0.5 size-5 shrink-0 text-suave" />
					<div><p class="text-sm" :class="x.ok ? 'text-suave line-through decoration-suave/40' : 'font-medium text-tinta'">{{ x.texto }}</p><p v-if="x.dica && !x.ok" class="text-xs text-suave">{{ x.dica }}</p></div>
				</li>
			</ul>
			<a v-if="p" :href="p.url_config" target="_blank" class="btn-secundario mt-4"><ExternalLink class="size-4" /> Abrir a configuração fiscal</a>
		</section>

		<section class="card space-y-2 p-5 text-sm text-suave">
			<h2 class="text-sm font-semibold text-tinta">Como a troca acontece</h2>
			<p>1. A empresa contrata um provedor de notas (Focus NFe, PlugNotas, Nuvem Fiscal ou NFE.io) e habilita a cobrança registrada com Pix no banco.</p>
			<p>2. A TI liga o adaptador do provedor escolhido (o restante do sistema não muda) e informa token, certificado e credenciais na configuração.</p>
			<p>3. O ambiente vai para <b>Homologação</b>: emitimos algumas notas e boletos de teste e conferimos com o contador.</p>
			<p>4. O ambiente vai para <b>Produção</b>. As telas e o jeito de trabalhar continuam exatamente os mesmos.</p>
		</section>
	</div>
</template>
