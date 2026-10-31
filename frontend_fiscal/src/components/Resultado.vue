<script setup>
import { CircleAlert, CircleCheck, FileText, Mail, Printer, Receipt } from "lucide-vue-next"
import { computed } from "vue"
import { urlDocumento } from "@/api"
import Copiar from "@/components/Copiar.vue"
import Modal from "@/components/Modal.vue"
import { data, moeda } from "@/format"
import { simulacao } from "@/store"

const props = defineProps({ resultado: Object })
const emit = defineEmits(["fechar", "abrir-nota"])
const tudoOk = computed(() => props.resultado.notas.every((n) => n.status === "Autorizada"))
const boletos = computed(() => props.resultado.boletos?.length ? props.resultado.boletos : props.resultado.boleto ? [props.resultado.boleto] : [])
</script>

<template>
	<Modal :titulo="tudoOk ? 'Pronto! Tudo emitido' : 'Atenção: algo não foi autorizado'" largura="max-w-xl" @fechar="emit('fechar')">
		<div class="space-y-3">
			<div v-for="n in resultado.notas" :key="n.id" class="flex items-start gap-3 rounded-xl border p-3"
				:class="n.status === 'Autorizada' ? 'border-emerald-500/30 bg-emerald-500/6' : 'border-rose-500/30 bg-rose-500/6'">
				<CircleCheck v-if="n.status === 'Autorizada'" class="mt-0.5 size-5 shrink-0 text-emerald-500" />
				<CircleAlert v-else class="mt-0.5 size-5 shrink-0 text-rose-500" />
				<div class="min-w-0 flex-1">
					<p class="font-medium text-tinta">
						{{ n.tipo }} {{ n.status === "Autorizada" ? `nº ${n.numero} autorizada` : "rejeitada" }}
						<span class="font-normal text-suave">· {{ moeda(n.valor) }}</span>
					</p>
					<p class="text-sm text-suave">{{ n.mensagem }}</p>
					<p v-if="n.orientacao" class="mt-1 text-sm font-medium text-rose-700 dark:text-rose-300">O que fazer: {{ n.orientacao }}</p>
					<div class="mt-2 flex flex-wrap gap-2">
						<a v-if="n.status === 'Autorizada'" :href="urlDocumento('nota', n.id)" target="_blank" class="btn-secundario px-2.5 py-1.5 text-xs"><Printer class="size-3.5" /> Ver {{ n.tipo === "NF-e" ? "DANFE" : "DANFSe" }}</a>
						<button class="btn-fantasma px-2.5 py-1.5 text-xs" @click="emit('abrir-nota', n.id)"><FileText class="size-3.5" /> Detalhes</button>
					</div>
				</div>
			</div>

			<div v-for="b in boletos" :key="b.id" class="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/6 p-3">
				<Receipt class="mt-0.5 size-5 shrink-0 text-amber-500" />
				<div class="min-w-0 flex-1">
					<p class="font-medium text-tinta">Boleto{{ b.parcela ? ` ${b.parcela}` : "" }} de {{ moeda(b.valor) }} <span class="font-normal text-suave">· vence {{ data(b.vencimento) }}</span></p>
					<p class="mt-1 font-mono text-xs break-all text-suave">{{ b.linha_digitavel }}</p>
					<div class="mt-2 flex flex-wrap gap-2">
						<a :href="urlDocumento('boleto', b.id)" target="_blank" class="btn-secundario px-2.5 py-1.5 text-xs"><Printer class="size-3.5" /> Ver boleto</a>
						<Copiar :texto="b.linha_digitavel" rotulo="Copiar linha digitável" />
					</div>
				</div>
			</div>

			<p v-if="tudoOk" class="flex items-center gap-2 text-sm text-suave">
				<Mail class="size-4" /> {{ simulacao() ? "Na simulação o e-mail não sai: ficou registrado no histórico da nota." : "Nota e boleto enviados ao e-mail do cliente." }}
			</p>
		</div>
		<template #rodape><button class="btn-primario" @click="emit('fechar')">Entendi</button></template>
	</Modal>
</template>
