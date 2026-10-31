<script setup>
import {
	ChevronDown,
	CircleAlert,
	CircleCheck,
	ExternalLink,
	FileText,
	Mail,
	PartyPopper,
	Receipt,
	RotateCcw,
	Search,
	Send,
	TriangleAlert,
	Wallet,
	AlarmClock,
	ArrowLeftRight,
} from "lucide-vue-next"
import { computed, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { api } from "@/api"
import CadastroFiscal from "@/components/CadastroFiscal.vue"
import Checagens from "@/components/Checagens.vue"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import Kpi from "@/components/Kpi.vue"
import Modal from "@/components/Modal.vue"
import Resultado from "@/components/Resultado.vue"
import Vazio from "@/components/Vazio.vue"
import { data, moeda, moedaCurta, plural } from "@/format"
import { store, toast } from "@/store"

const router = useRouter()
const dados = ref(null)
const aberta = ref(null)
const filtro = ref("todas")
const busca = ref("")
const cadastro = ref(null) // { tipo, parte } em edição
const confirmar = ref(null) // { faturas: [...] }
const emitindo = ref(false)
const resultado = ref(null)
const lote = ref(null)

const primeiroNome = computed(() => (store.contexto?.usuario.nome || "").split(" ")[0])
const saudacao = computed(() => {
	const h = new Date().getHours()
	return h < 12 ? "Bom dia" : h < 18 ? "Boa tarde" : "Boa noite"
})

const faturas = computed(() => {
	let l = dados.value?.faturas || []
	if (filtro.value === "prontas") l = l.filter((f) => f.pode_emitir)
	if (filtro.value === "pendentes") l = l.filter((f) => !f.pode_emitir)
	const b = busca.value.trim().toLowerCase()
	if (b) l = l.filter((f) => [f.nome, f.fatura, f.documento_cliente].some((t) => (t || "").toLowerCase().includes(b)))
	return l
})
const prontas = computed(() => (dados.value?.faturas || []).filter((f) => f.pode_emitir))

async function carregar() {
	dados.value = await api("para_emitir")
	if (aberta.value && !dados.value.faturas.some((f) => f.fatura === aberta.value)) aberta.value = null
	if (!aberta.value && dados.value.faturas.length) aberta.value = dados.value.faturas[0].fatura
}

function situacao(f) {
	if (!f.pode_emitir) return { rotulo: `Falta ajustar (${f.checagens.filter((c) => c.nivel === "erro").length})`, classe: "bg-rose-500/12 text-rose-700 dark:text-rose-300", icone: CircleAlert }
	if (f.checagens.some((c) => c.nivel === "aviso")) return { rotulo: "Pronta, com aviso", classe: "bg-amber-500/14 text-amber-700 dark:text-amber-300", icone: TriangleAlert }
	return { rotulo: "Pronta para emitir", classe: "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300", icone: CircleCheck }
}

function emailDe(f) {
	const aviso = f.checagens.find((c) => c.texto.includes("não tem e-mail"))
	return aviso ? null : "o e-mail fiscal do cliente"
}

function acao(f, a) {
	if (a === "cadastro") cadastro.value = { tipo: "Customer", parte: f.cliente }
	else if (a === "config") window.open("/app/configuracao-fiscal", "_blank")
	else if (a.startsWith("item:")) window.open("/app/item/" + encodeURIComponent(a.slice(5)), "_blank")
}

async function emitir() {
	emitindo.value = true
	const lista = confirmar.value.faturas
	try {
		if (lista.length === 1) {
			resultado.value = await api("emitir", { fatura: lista[0].fatura }, { post: true })
		} else {
			lote.value = await api("emitir_lote", { faturas: lista.map((f) => f.fatura) }, { post: true })
		}
		confirmar.value = null
		await carregar()
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		emitindo.value = false
	}
}

async function tentarDeNovo(n) {
	try {
		resultado.value = await api("tentar_de_novo", { id: n.id }, { post: true })
		await carregar()
	} catch (e) {
		toast(e.message, "erro")
	}
}

onMounted(carregar)
</script>

<template>
	<div class="space-y-6">
		<div class="flex flex-wrap items-end justify-between gap-4">
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-tinta">{{ saudacao }}, {{ primeiroNome }}</h1>
				<p class="mt-1 text-sm text-suave">Confira cada fatura e clique em <b>Emitir</b>. O sistema prepara a nota, o boleto e o e-mail.</p>
			</div>
			<div class="flex gap-2">
				<RouterLink to="/remessas/nova" class="btn-secundario"><ArrowLeftRight class="size-4" /> Remessa ou retorno</RouterLink>
				<button v-if="prontas.length > 1" class="btn-primario" @click="confirmar = { faturas: prontas }">
					<Send class="size-4" /> Emitir as {{ prontas.length }} prontas
				</button>
			</div>
		</div>

		<div v-if="!dados" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><div v-for="i in 4" :key="i" class="card p-4"><Esqueleto :linhas="2" /></div></div>
		<div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
			<Kpi rotulo="Esperando nota" :valor="dados.kpis.a_emitir" :detalhe="`${moedaCurta(dados.kpis.a_emitir_valor)} · ${dados.kpis.prontas} prontas`" :icone="Send" destaque />
			<Kpi rotulo="Emitidas neste mês" :valor="dados.kpis.emitidas_mes" :detalhe="moedaCurta(dados.kpis.emitidas_mes_valor)" :icone="FileText" tom="violeta" />
			<Kpi rotulo="Boletos a receber" :valor="moedaCurta(dados.kpis.boletos_abertos_valor)" :detalhe="dados.kpis.vencidos ? `${plural(dados.kpis.vencidos, 'vencido', 'vencidos')} · ${moedaCurta(dados.kpis.vencidos_valor)}` : plural(dados.kpis.boletos_abertos, 'boleto em aberto', 'boletos em aberto')"
				:icone="dados.kpis.vencidos ? AlarmClock : Receipt" :tom="dados.kpis.vencidos ? 'vermelho' : 'ambar'" />
			<Kpi rotulo="Recebido neste mês" :valor="moedaCurta(dados.kpis.recebido_mes)" detalhe="baixado sozinho no ERP" :icone="Wallet" tom="verde" />
		</div>

		<!-- Notas rejeitadas: o que fazer -->
		<section v-if="dados?.rejeitadas.length" class="space-y-2">
			<h2 class="flex items-center gap-2 text-sm font-semibold text-rose-700 dark:text-rose-300"><CircleAlert class="size-4" /> {{ plural(dados.rejeitadas.length, "nota voltou rejeitada", "notas voltaram rejeitadas") }}</h2>
			<div v-for="n in dados.rejeitadas" :key="n.id" class="card flex flex-wrap items-start gap-3 border-rose-500/30 p-4">
				<div class="min-w-0 flex-1">
					<p class="font-medium text-tinta">{{ n.tipo_documento }} · {{ n.nome_parte }} · {{ moeda(n.valor_total) }}</p>
					<p class="text-sm text-suave">{{ n.mensagem_retorno }}</p>
					<p v-if="n.orientacao" class="mt-1 text-sm font-medium text-rose-700 dark:text-rose-300">O que fazer: {{ n.orientacao }}</p>
				</div>
				<div class="flex gap-2">
					<button class="btn-secundario" @click="cadastro = { tipo: n.tipo_parte, parte: n.parte }"><FileText class="size-4" /> Corrigir cadastro</button>
					<button class="btn-primario" @click="tentarDeNovo(n)"><RotateCcw class="size-4" /> Tentar de novo</button>
				</div>
			</div>
		</section>

		<section v-if="dados" class="space-y-3">
			<div class="flex flex-wrap items-center gap-2">
				<button v-for="[k, r] in [['todas', `Todas (${dados.faturas.length})`], ['prontas', `Prontas (${prontas.length})`], ['pendentes', `Falta ajustar (${dados.faturas.length - prontas.length})`]]" :key="k"
					class="chip" :class="filtro === k ? 'border-marca-500 bg-marca-500/10 text-marca-700 dark:text-marca-300' : 'border-borda text-suave hover:bg-realce'" @click="filtro = k">{{ r }}</button>
				<div class="relative ml-auto w-full sm:w-64">
					<Search class="absolute top-2.5 left-3 size-4 text-suave" />
					<input v-model="busca" class="campo pl-9" placeholder="Cliente, fatura ou CNPJ" />
				</div>
			</div>

			<div v-if="!dados.faturas.length" class="card">
				<Vazio :icone="PartyPopper" titulo="Tudo em dia!" texto="Nenhuma fatura esperando nota ou boleto. Assim que uma fatura for confirmada no ERP, ela aparece aqui." />
			</div>

			<article v-for="f in faturas" :key="f.fatura" class="card overflow-hidden transition" :class="aberta === f.fatura && 'ring-2 ring-marca-500/25'">
				<button class="flex w-full flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3.5 text-left hover:bg-realce/60 sm:px-5" @click="aberta = aberta === f.fatura ? null : f.fatura">
					<div class="min-w-0 flex-1">
						<p class="truncate font-semibold text-tinta">{{ f.nome }}</p>
						<p class="truncate text-xs text-suave">{{ f.fatura }} · {{ data(f.data) }}<span v-if="f.documento_cliente"> · {{ f.documento_cliente }}</span></p>
					</div>
					<div class="flex flex-wrap gap-1.5">
						<Etiqueta v-for="d in f.documentos" :key="d.tipo" :valor="d.tipo" :ponto="false">{{ d.tipo }}{{ d.ja_emitida ? " ✓" : "" }}</Etiqueta>
						<Etiqueta v-if="f.boleto" valor="Boleto" :ponto="false">{{ f.boleto.parcelas?.length > 1 ? `Boleto ${f.boleto.parcelas.length}x` : "Boleto" }}</Etiqueta>
					</div>
					<p class="w-28 text-right font-semibold text-tinta tabular-nums">{{ moeda(f.valor) }}</p>
					<span class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold" :class="situacao(f).classe">
						<component :is="situacao(f).icone" class="size-3.5" /> {{ situacao(f).rotulo }}
					</span>
					<ChevronDown class="size-4 text-suave transition" :class="aberta === f.fatura && 'rotate-180'" />
				</button>

				<div v-if="aberta === f.fatura" class="grid gap-5 border-t border-borda px-4 py-5 sm:px-5 lg:grid-cols-5">
					<div class="lg:col-span-3">
						<p class="mb-3 text-xs font-semibold tracking-wider text-suave uppercase">O que vai acontecer</p>
						<ol class="relative space-y-4 border-l border-borda pl-6">
							<li v-for="d in f.documentos" :key="d.tipo" class="relative">
								<span class="absolute top-0 -left-[33px] grid size-6 place-items-center rounded-full bg-superficie ring-1 ring-borda"><FileText class="size-3.5" :class="d.tipo === 'NF-e' ? 'text-marca-600' : 'text-violet-600'" /></span>
								<p class="font-medium text-tinta">{{ d.ja_emitida ? `${d.tipo} nº ${d.ja_emitida.numero} já emitida` : `Emitir ${d.tipo}` }} <span class="text-sm font-normal text-suave">· {{ d.natureza }}</span></p>
								<p class="text-sm text-suave">{{ d.resumo }}</p>
								<table class="mt-2 w-full text-xs">
									<tr v-for="i in d.itens" :key="i.referencia" class="border-b border-borda/60 last:border-0">
										<td class="py-1 pr-2 text-texto">{{ i.descricao }}<span v-if="i.ncm" class="text-suave"> · NCM {{ i.ncm }}</span></td>
										<td class="py-1 text-right whitespace-nowrap text-suave tabular-nums">{{ i.quantidade }} × {{ moeda(i.valor_unitario) }}</td>
										<td class="w-24 py-1 text-right font-medium text-tinta tabular-nums">{{ moeda(i.valor_total) }}</td>
									</tr>
								</table>
								<p v-if="d.valores.valor_retencoes" class="mt-1.5 text-xs text-suave">
									Retido pelo cliente: <b class="text-tinta">{{ moeda(d.valores.valor_retencoes) }}</b> · líquido a receber <b class="text-tinta">{{ moeda(d.valores.valor_liquido) }}</b>
								</p>
							</li>
							<li v-if="f.boleto" class="relative">
								<span class="absolute top-0 -left-[33px] grid size-6 place-items-center rounded-full bg-superficie ring-1 ring-borda"><Receipt class="size-3.5 text-amber-600" /></span>
								<p class="font-medium text-tinta">{{ f.boleto.ja_emitido ? "Boleto já emitido" : f.boleto.parcelas?.length > 1 ? `Gerar ${f.boleto.parcelas.length} boletos com Pix (parcelado)` : "Gerar boleto com Pix" }}</p>
								<p class="text-sm text-suave">{{ f.boleto.resumo }}</p>
								<table v-if="f.boleto.parcelas?.length > 1" class="mt-2 w-full text-xs">
									<tr v-for="p in f.boleto.parcelas" :key="p.parcela" class="border-b border-borda/60 last:border-0">
										<td class="py-1 pr-2 font-medium text-texto">Parcela {{ p.parcela }}</td>
										<td class="py-1 text-suave">vence {{ data(p.vencimento) }}</td>
										<td v-if="p.valor_retencao" class="py-1 text-right text-suave tabular-nums">− {{ moeda(p.valor_retencao) }} retido</td>
										<td class="w-24 py-1 text-right font-medium text-tinta tabular-nums">{{ moeda(p.valor) }}</td>
									</tr>
								</table>
							</li>
							<li class="relative">
								<span class="absolute top-0 -left-[33px] grid size-6 place-items-center rounded-full bg-superficie ring-1 ring-borda"><Mail class="size-3.5 text-blue-600" /></span>
								<p class="font-medium text-tinta">Enviar ao cliente</p>
								<p class="text-sm text-suave">{{ emailDe(f) ? `PDF, XML e boleto vão para ${emailDe(f)}.` : "Sem e-mail no cadastro: você precisará enviar manualmente." }}</p>
							</li>
						</ol>
					</div>
					<div class="lg:col-span-2">
						<p class="mb-3 text-xs font-semibold tracking-wider text-suave uppercase">Conferência</p>
						<Checagens :itens="f.checagens" @acao="(a) => acao(f, a)" />
					</div>
					<div class="flex flex-wrap items-center gap-2 border-t border-borda pt-4 lg:col-span-5">
						<a :href="`/app/sales-invoice/${f.fatura}`" target="_blank" class="btn-fantasma"><ExternalLink class="size-4" /> Abrir fatura no ERP</a>
						<button class="btn-fantasma" @click="cadastro = { tipo: 'Customer', parte: f.cliente }"><FileText class="size-4" /> Cadastro fiscal do cliente</button>
						<button class="btn-primario ml-auto" :disabled="!f.pode_emitir" @click="confirmar = { faturas: [f] }">
							<Send class="size-4" /> {{ f.documentos.every((d) => d.ja_emitida) ? "Gerar boleto" : f.boleto ? (f.boleto.parcelas?.length > 1 ? "Emitir nota e boletos" : "Emitir nota e boleto") : "Emitir nota" }}
						</button>
					</div>
				</div>
			</article>
		</section>

		<CadastroFiscal v-if="cadastro" :tipo-parte="cadastro.tipo" :parte="cadastro.parte" @fechar="cadastro = null" @salvo="cadastro = null; carregar()" />

		<Modal v-if="confirmar" :titulo="confirmar.faturas.length === 1 ? 'Confirmar emissão' : `Emitir ${confirmar.faturas.length} faturas`" largura="max-w-lg" @fechar="confirmar = null">
			<div class="space-y-3">
				<div v-for="f in confirmar.faturas" :key="f.fatura" class="rounded-xl border border-borda p-3">
					<p class="font-medium text-tinta">{{ f.nome }} <span class="font-normal text-suave">· {{ f.fatura }}</span></p>
					<ul class="mt-1 space-y-0.5 text-sm text-suave">
						<li v-for="d in f.documentos.filter((x) => !x.ja_emitida)" :key="d.tipo">• {{ d.tipo }} de {{ moeda(d.valores.valor_total) }}</li>
						<template v-if="f.boleto && !f.boleto.ja_emitido">
							<li v-for="p in f.boleto.parcelas" :key="p.parcela || 'unico'">• Boleto{{ p.parcela ? ` ${p.parcela}` : "" }} de {{ moeda(p.valor) }}, vence {{ data(p.vencimento) }}</li>
						</template>
					</ul>
				</div>
				<p class="text-sm text-suave" v-if="!store.contexto.simulacao">Depois de autorizada, a NF-e só pode ser cancelada em até 24 horas.</p>
				<p class="text-sm text-amber-700 dark:text-amber-300" v-else>Simulação: nada tem valor fiscal e nada sai daqui.</p>
			</div>
			<template #rodape>
				<button class="btn-secundario" @click="confirmar = null">Voltar</button>
				<button class="btn-primario" :disabled="emitindo" @click="emitir"><Send class="size-4" /> {{ emitindo ? "Emitindo…" : "Confirmar e emitir" }}</button>
			</template>
		</Modal>

		<Resultado v-if="resultado" :resultado="resultado" @fechar="resultado = null" @abrir-nota="(id) => router.push(`/notas/${id}`)" />

		<Modal v-if="lote" titulo="Resultado da emissão" largura="max-w-lg" @fechar="lote = null">
			<ul class="space-y-2">
				<li v-for="r in lote" :key="r.fatura" class="flex items-start gap-2.5 text-sm">
					<CircleCheck v-if="r.ok" class="mt-0.5 size-4 shrink-0 text-emerald-500" /><CircleAlert v-else class="mt-0.5 size-4 shrink-0 text-rose-500" />
					<span>
						<b class="text-tinta">{{ r.fatura }}</b>:
						<template v-if="r.erro">{{ r.erro }}</template>
						<template v-else>{{ r.notas.map((n) => `${n.tipo} ${n.status === "Autorizada" ? "nº " + n.numero : "rejeitada"}`).join(", ") }}{{ r.boletos?.length > 1 ? ` · ${r.boletos.length} boletos` : r.boleto ? ` · boleto ${moeda(r.boleto.valor)}` : "" }}</template>
					</span>
				</li>
			</ul>
			<template #rodape><button class="btn-primario" @click="lote = null">Entendi</button></template>
		</Modal>
	</div>
</template>
