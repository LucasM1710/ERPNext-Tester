<script setup>
import { ArrowLeft, CalendarClock, FileCheck2, History, ReceiptText, ThumbsDown, ThumbsUp } from "lucide-vue-next"
import { onMounted, ref } from "vue"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import LinhaEtapas from "@/components/LinhaEtapas.vue"
import Modal from "@/components/Modal.vue"
import { data, dataHora } from "@/format"
import { CONSULTA } from "@/modo"
import { podeEditar, toast } from "@/store"

const props = defineProps({ id: String })
const o = ref(null)
const erro = ref(null)
const confirmar = ref(null) // true = aprovar, false = recusar
const enviando = ref(false)

onMounted(async () => {
	try {
		o.value = await api("ordem", { id: props.id })
	} catch (e) {
		erro.value = e.message
	}
})

async function responder() {
	enviando.value = true
	try {
		o.value = await api("responder_orcamento", { id: props.id, aprovado: confirmar.value ? 1 : 0 }, { post: true })
		toast(confirmar.value ? "Orçamento aprovado. O serviço será iniciado." : "Orçamento recusado.")
		confirmar.value = null
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		enviando.value = false
	}
}
</script>

<template>
	<div class="space-y-6">
		<RouterLink to="/ordens" class="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800">
			<ArrowLeft class="size-4" /> Ordens de Serviço
		</RouterLink>

		<div v-if="erro" class="card p-6 text-sm text-rose-600">{{ erro }}</div>
		<div v-else-if="!o" class="card p-6"><Esqueleto :linhas="8" /></div>

		<template v-else>
			<div class="card p-6">
				<div class="flex flex-wrap items-start justify-between gap-4">
					<div>
						<div class="flex items-center gap-2">
							<h1 class="text-2xl font-semibold tracking-tight text-slate-900">{{ o.id }}</h1>
							<Etiqueta :valor="o.status" />
						</div>
						<p class="mt-1 text-sm text-slate-500">
							{{ o.tipo }} · {{ o.local_atendimento === "In Loco" ? "Atendimento in loco" : "No laboratório" }} · aberta em {{ data(o.data_solicitacao) }}
						</p>
					</div>
					<div v-if="o.data_prevista && !o.finalizada" class="rounded-xl px-4 py-2 text-right" :class="o.atrasada ? 'bg-rose-50' : 'bg-slate-50'">
						<p class="flex items-center justify-end gap-1.5 text-xs" :class="o.atrasada ? 'text-rose-600' : 'text-slate-500'">
							<CalendarClock class="size-3.5" /> {{ o.atrasada ? "Previsão (atrasada)" : "Previsão de entrega" }}
						</p>
						<p class="font-semibold tabular-nums" :class="o.atrasada ? 'text-rose-700' : 'text-slate-900'">{{ data(o.data_prevista) }}</p>
					</div>
				</div>
				<div class="mt-8"><LinhaEtapas :etapas="o.etapas" :atual="o.etapa_atual" /></div>
			</div>

			<div v-if="o.status_orcamento === 'Aguardando Cliente'" class="flex flex-wrap items-center gap-4 rounded-2xl border border-amber-200 bg-gradient-to-r from-amber-50 to-white p-5">
				<span class="grid size-11 place-items-center rounded-xl bg-amber-100 text-amber-700"><ReceiptText class="size-5" /></span>
				<div class="min-w-0 flex-1">
					<p class="font-semibold text-amber-900">Orçamento aguardando sua aprovação</p>
					<p class="text-sm text-amber-800/80">
						{{ o.orcamento ? `Orçamento ${o.orcamento}. ` : "" }}{{ CONSULTA ? "Responda ao laboratório pelo canal comercial de costume." : "O laboratório só inicia o serviço após a sua resposta." }}
					</p>
				</div>
				<div v-if="podeEditar(o.cliente) && !CONSULTA" class="flex gap-2">
					<button class="btn-secondary" @click="confirmar = false"><ThumbsDown class="size-4" /> Recusar</button>
					<button class="btn-success" @click="confirmar = true"><ThumbsUp class="size-4" /> Aprovar</button>
				</div>
			</div>

			<div class="grid gap-6 lg:grid-cols-3">
				<section class="card overflow-hidden lg:col-span-2">
					<h2 class="px-6 pt-6 pb-3 font-semibold text-slate-900">Equipamentos ({{ o.itens.length }})</h2>
					<p v-if="o.itens_outros_distritos" class="mx-6 mb-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
						Esta ordem também tem {{ o.itens_outros_distritos }} equipamento(s) de outros distritos, que não aparecem para você.
					</p>
					<ul class="divide-y divide-slate-100">
						<li v-for="i in o.itens" :key="i.equipamento_id" class="flex flex-wrap items-center gap-4 px-6 py-4">
							<RouterLink :to="`/equipamentos/${i.equipamento_id}`" class="min-w-0 flex-1">
								<p class="font-medium text-slate-900 hover:text-brand-700">{{ i.tag }}</p>
								<p class="text-sm text-slate-500">{{ i.descricao }} · {{ i.servico }}</p>
								<p v-if="i.laudo" class="mt-1 rounded-lg bg-slate-50 px-2.5 py-1.5 text-xs text-slate-600">{{ i.laudo }}</p>
							</RouterLink>
							<Etiqueta :valor="i.status" />
							<RouterLink v-if="i.certificado_id" :to="`/certificados/${i.certificado_id}`" class="btn-secondary py-1.5 text-xs">
								<FileCheck2 class="size-3.5" /> Certificado
							</RouterLink>
						</li>
					</ul>
					<div v-if="o.observacoes_cliente" class="border-t border-slate-100 px-6 py-4">
						<p class="text-xs font-medium text-slate-500">Suas observações</p>
						<p class="mt-1 text-sm whitespace-pre-line text-slate-700">{{ o.observacoes_cliente }}</p>
					</div>
				</section>

				<section class="card p-6">
					<h2 class="flex items-center gap-2 font-semibold text-slate-900"><History class="size-4 text-brand-600" /> Histórico</h2>
					<ol class="mt-5 space-y-0">
						<li v-for="(h, idx) in [...o.historico].reverse()" :key="idx" class="relative flex gap-3 pb-5 last:pb-0">
							<span v-if="idx < o.historico.length - 1" class="absolute top-4 left-[5px] h-full w-px bg-slate-200" />
							<span class="relative z-10 mt-1.5 size-[11px] shrink-0 rounded-full ring-4 ring-white" :class="idx === 0 ? 'bg-brand-600' : 'bg-slate-300'" />
							<div>
								<p class="text-sm font-medium" :class="idx === 0 ? 'text-slate-900' : 'text-slate-600'">{{ h.status }}</p>
								<p class="text-xs text-slate-400">{{ dataHora(h.data) }}</p>
							</div>
						</li>
					</ol>
				</section>
			</div>
		</template>

		<Modal
			v-if="confirmar !== null"
			:titulo="confirmar ? 'Aprovar orçamento?' : 'Recusar orçamento?'"
			:subtitulo="confirmar ? 'O laboratório iniciará o serviço imediatamente.' : 'A ordem será cancelada e os equipamentos devolvidos sem o serviço.'"
			largura="max-w-md"
			@fechar="confirmar = null"
		>
			<p class="text-sm text-slate-600">Esta resposta fica registrada com seu usuário e a data/hora.</p>
			<template #rodape>
				<button class="btn-secondary" @click="confirmar = null">Voltar</button>
				<button :class="confirmar ? 'btn-success' : 'btn-danger'" :disabled="enviando" @click="responder">
					{{ enviando ? "Enviando…" : confirmar ? "Sim, aprovar" : "Sim, recusar" }}
				</button>
			</template>
		</Modal>
	</div>
</template>
