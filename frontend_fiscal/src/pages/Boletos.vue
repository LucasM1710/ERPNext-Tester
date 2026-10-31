<script setup>
import { AlarmClock, Ban, CalendarClock, CircleCheck, FlaskConical, HandCoins, MoreHorizontal, Printer, Receipt, Search, Wallet } from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"
import { api, urlDocumento } from "@/api"
import Copiar from "@/components/Copiar.vue"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import Kpi from "@/components/Kpi.vue"
import Modal from "@/components/Modal.vue"
import Vazio from "@/components/Vazio.vue"
import { data, dataHora, hojeISO, moeda, moedaCurta, vencimento } from "@/format"
import { simulacao, toast } from "@/store"

const boletos = ref(null)
const aba = ref("abertos")
const busca = ref("")
const menu = ref(null)
const acao = ref(null) // { tipo: 'pagar'|'manual'|'prorrogar'|'cancelar'|'historico', b }
const form = ref({})
const ocupado = ref(false)

const ABAS = [["abertos", "A receber"], ["Vencido", "Vencidos"], ["Pago", "Pagos"], ["Cancelado", "Cancelados"], ["", "Todos"]]

const resumo = computed(() => {
	const l = boletos.value || []
	const soma = (f) => l.filter(f).reduce((s, b) => s + b.valor, 0)
	return {
		aVencer: soma((b) => b.status === "Em aberto"),
		vencidos: soma((b) => b.status === "Vencido"),
		semana: soma((b) => b.status === "Em aberto" && b.dias_para_vencer <= 7),
		pagos: l.filter((b) => b.status === "Pago").reduce((s, b) => s + (b.valor_pago || 0), 0),
	}
})

let espera
async function carregar() {
	boletos.value = await api("boletos", { status: aba.value, busca: busca.value })
}
watch(aba, carregar)
watch(busca, () => {
	clearTimeout(espera)
	espera = setTimeout(carregar, 300)
})

function abrir(tipo, b) {
	menu.value = null
	acao.value = { tipo, b }
	form.value = { valor: b.valor, data: hojeISO(), vencimento: hojeISO(7), motivo: "" }
	if (tipo === "historico") api("boleto", { id: b.id }).then((r) => (acao.value = { tipo, b: r }))
}

async function executar() {
	const { tipo, b } = acao.value
	ocupado.value = true
	try {
		if (tipo === "pagar") await api("simular_pagamento", { id: b.id, valor: form.value.valor, data: form.value.data }, { post: true })
		if (tipo === "manual") await api("marcar_como_pago", { id: b.id, valor: form.value.valor, data: form.value.data }, { post: true })
		if (tipo === "prorrogar") await api("prorrogar_boleto", { id: b.id, vencimento: form.value.vencimento }, { post: true })
		if (tipo === "cancelar") await api("cancelar_boleto", { id: b.id, motivo: form.value.motivo }, { post: true })
		toast(
			{
				pagar: "Pagamento registrado e baixado na fatura do ERP.",
				manual: "Baixa registrada e lançada na fatura do ERP.",
				prorrogar: "Novo boleto gerado com o novo vencimento.",
				cancelar: "Boleto cancelado.",
			}[tipo],
		)
		acao.value = null
		await carregar()
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		ocupado.value = false
	}
}

onMounted(carregar)
</script>

<template>
	<div class="space-y-5" @click="menu = null">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight text-tinta">Boletos</h1>
			<p class="mt-1 text-sm text-suave">Quando o cliente paga, o banco avisa e o sistema dá baixa na fatura sozinho. Aqui você acompanha e resolve as exceções.</p>
		</div>

		<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
			<Kpi rotulo="A vencer" :valor="moedaCurta(resumo.aVencer)" :detalhe="`${moedaCurta(resumo.semana)} nos próximos 7 dias`" :icone="Receipt" tom="ambar" />
			<Kpi rotulo="Vencidos" :valor="moedaCurta(resumo.vencidos)" detalhe="cobrança automática por e-mail" :icone="AlarmClock" tom="vermelho" />
			<Kpi v-if="aba === 'Pago' || aba === ''" rotulo="Recebidos (lista)" :valor="moedaCurta(resumo.pagos)" :icone="Wallet" tom="verde" />
		</div>

		<div class="flex flex-wrap items-center gap-2">
			<button v-for="[v, r] in ABAS" :key="v" class="chip" :class="aba === v ? 'border-marca-500 bg-marca-500/10 text-marca-700 dark:text-marca-300' : 'border-borda text-suave hover:bg-realce'" @click="aba = v">{{ r }}</button>
			<div class="relative ml-auto w-full sm:w-64">
				<Search class="absolute top-2.5 left-3 size-4 text-suave" />
				<input v-model="busca" class="campo pl-9" placeholder="Cliente, fatura ou nosso número" />
			</div>
		</div>

		<div v-if="!boletos" class="card p-5"><Esqueleto :linhas="6" /></div>
		<div v-else-if="!boletos.length" class="card"><Vazio :icone="Receipt" titulo="Nenhum boleto aqui" texto="Os boletos são gerados junto com a nota, em Para emitir." /></div>

		<div v-else class="space-y-2">
			<article v-for="b in boletos" :key="b.id" class="card flex flex-wrap items-center gap-x-4 gap-y-3 p-4">
				<div class="min-w-0 flex-1 basis-56">
					<p class="truncate font-semibold text-tinta">{{ b.nome_cliente }}</p>
					<p class="text-xs text-suave">{{ b.fatura }} · nosso número {{ b.nosso_numero }}</p>
				</div>
				<div class="w-40">
					<p class="font-semibold text-tinta tabular-nums">{{ moeda(b.valor) }}</p>
					<p v-if="b.valor_atualizado" class="text-xs text-rose-600 dark:text-rose-400" :title="b.aviso_multa">hoje: {{ moeda(b.valor_atualizado) }}</p>
					<p v-else-if="b.status === 'Pago'" class="text-xs text-emerald-600">pago {{ moeda(b.valor_pago) }}</p>
				</div>
				<div class="w-40 text-sm">
					<p class="text-tinta">{{ data(b.vencimento) }}</p>
					<p class="text-xs" :class="b.status === 'Vencido' ? 'font-medium text-rose-600' : 'text-suave'">
						{{ b.status === "Pago" ? `pago em ${data(b.pago_em)}` : ["Em aberto", "Vencido"].includes(b.status) ? vencimento(b.dias_para_vencer) : "" }}
					</p>
				</div>
				<Etiqueta :valor="b.status" />
				<div class="flex items-center gap-1.5">
					<Copiar v-if="['Em aberto', 'Vencido'].includes(b.status)" :texto="b.linha_digitavel" rotulo="Linha" />
					<Copiar v-if="['Em aberto', 'Vencido'].includes(b.status) && b.pix_copia_cola" :texto="b.pix_copia_cola" rotulo="Pix" />
					<a :href="urlDocumento('boleto', b.id)" target="_blank" class="btn-secundario px-2.5 py-1.5 text-xs"><Printer class="size-3.5" /></a>
					<div class="relative">
						<button class="btn-fantasma p-1.5" aria-label="Mais ações" @click.stop="menu = menu === b.id ? null : b.id"><MoreHorizontal class="size-4" /></button>
						<div v-if="menu === b.id" class="absolute right-0 z-10 mt-1 w-56 rounded-xl border border-borda bg-elevada p-1.5 shadow-pop" @click.stop>
							<template v-if="['Em aberto', 'Vencido'].includes(b.status)">
								<button v-if="simulacao()" class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-texto hover:bg-realce" @click="abrir('pagar', b)"><FlaskConical class="size-4 text-amber-500" /> Simular pagamento</button>
								<button class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-texto hover:bg-realce" @click="abrir('manual', b)"><HandCoins class="size-4 text-suave" /> Marcar como pago</button>
								<button class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-texto hover:bg-realce" @click="abrir('prorrogar', b)"><CalendarClock class="size-4 text-suave" /> Prorrogar (2ª via)</button>
								<button class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-rose-600 hover:bg-rose-500/10" @click="abrir('cancelar', b)"><Ban class="size-4" /> Cancelar boleto</button>
							</template>
							<button class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-texto hover:bg-realce" @click="abrir('historico', b)"><CircleCheck class="size-4 text-suave" /> Histórico</button>
							<RouterLink v-if="b.nota_fiscal" :to="`/notas/${b.nota_fiscal}`" class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-texto hover:bg-realce"><Receipt class="size-4 text-suave" /> Ver a nota</RouterLink>
						</div>
					</div>
				</div>
			</article>
		</div>

		<Modal v-if="acao && acao.tipo !== 'historico'" largura="max-w-md" @fechar="acao = null"
			:titulo="{ pagar: 'Simular pagamento', manual: 'Marcar como pago', prorrogar: 'Prorrogar boleto', cancelar: 'Cancelar boleto' }[acao.tipo]"
			:subtitulo="`${acao.b.nome_cliente} · ${moeda(acao.b.valor)}`">
			<div class="space-y-3 text-sm">
				<p v-if="acao.tipo === 'pagar'" class="rounded-xl bg-amber-500/10 px-3 py-2 text-amber-800 dark:text-amber-200">Faz o papel do banco avisando que o cliente pagou. O sistema marca o boleto como pago e lança o recebimento na fatura do ERP.</p>
				<p v-if="acao.tipo === 'manual'" class="text-suave">Use quando o cliente pagou por fora do boleto (transferência, depósito). O recebimento é lançado na fatura do ERP.</p>
				<p v-if="acao.tipo === 'prorrogar'" class="text-suave">O boleto atual é cancelado e sai um novo, com a nova data. Envie o novo ao cliente.</p>
				<p v-if="acao.tipo === 'cancelar'" class="text-suave">O banco deixa de aceitar este boleto. A fatura continua em aberto no ERP.</p>
				<template v-if="['pagar', 'manual'].includes(acao.tipo)">
					<div class="grid grid-cols-2 gap-3">
						<div><label class="rotulo">Valor pago</label><input v-model.number="form.valor" type="number" step="0.01" class="campo" /></div>
						<div><label class="rotulo">Data do pagamento</label><input v-model="form.data" type="date" class="campo" /></div>
					</div>
				</template>
				<div v-if="acao.tipo === 'prorrogar'"><label class="rotulo">Novo vencimento</label><input v-model="form.vencimento" type="date" :min="hojeISO()" class="campo" /></div>
				<div v-if="acao.tipo === 'cancelar'"><label class="rotulo">Motivo</label><input v-model="form.motivo" class="campo" placeholder="Ex.: cliente pagou por transferência" /></div>
			</div>
			<template #rodape>
				<button class="btn-secundario" @click="acao = null">Voltar</button>
				<button :class="acao.tipo === 'cancelar' ? 'btn-perigo' : 'btn-primario'" :disabled="ocupado" @click="executar">{{ ocupado ? "Aguarde…" : "Confirmar" }}</button>
			</template>
		</Modal>

		<Modal v-if="acao && acao.tipo === 'historico'" titulo="Histórico do boleto" :subtitulo="`${acao.b.nome_cliente} · ${moeda(acao.b.valor)}`" @fechar="acao = null">
			<div v-if="acao.b.linha_digitavel" class="mb-4 rounded-xl bg-realce/70 px-3 py-2"><p class="text-[11px] text-suave">Linha digitável</p><p class="font-mono text-sm break-all text-tinta">{{ acao.b.linha_digitavel }}</p></div>
			<Esqueleto v-if="!acao.b.eventos" :linhas="3" />
			<ol v-else class="relative space-y-3 border-l border-borda pl-4">
				<li v-for="(e, k) in acao.b.eventos" :key="k" class="relative">
					<span class="absolute top-1.5 -left-[21px] size-2.5 rounded-full bg-marca-500 ring-4 ring-elevada" />
					<p class="text-sm font-medium text-tinta">{{ e.evento }}</p>
					<p v-if="e.detalhe" class="text-xs text-suave">{{ e.detalhe }}</p>
					<p class="text-[11px] text-suave/80">{{ dataHora(e.data) }}</p>
				</li>
			</ol>
		</Modal>
	</div>
</template>
