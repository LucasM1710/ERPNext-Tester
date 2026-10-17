<script setup>
import { ArrowLeft, CalendarCheck2, CircleCheck, CircleX, ClipboardCheck, Download, FileCheck2, FileUp, Pencil, QrCode, Send, Sparkles } from "lucide-vue-next"
import { computed, onMounted, ref } from "vue"
import { api, urlDownloadCertificado } from "@/api"
import EnviarCertificado from "@/components/EnviarCertificado.vue"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import FormEquipamento from "@/components/FormEquipamento.vue"
import Grafico from "@/components/Grafico.vue"
import Modal from "@/components/Modal.vue"
import RegistrarVerificacao from "@/components/RegistrarVerificacao.vue"
import Vazio from "@/components/Vazio.vue"
import { COR, COR_SITUACAO, eixoBase, tooltipBase } from "@/cores"
import { data, dataHora, diasAte, numero, relativo } from "@/format"
import { podeEditar, store, toast } from "@/store"

const props = defineProps({ id: String })
const e = ref(null)
const erro = ref(null)
const editar = ref(false)
const enviarCert = ref(false)
const qr = ref(false)
const verificar = ref(false)
const aplicando = ref(false)

// Periodicidade inteligente: o cliente decide; aqui só aplica a sugestão com um clique
async function aplicarSugestao() {
	aplicando.value = true
	try {
		await api("atualizar_equipamento", { id: props.id, dados: { periodicidade_meses: e.value.periodicidade_sugerida.sugerida } }, { post: true })
		toast(`Periodicidade alterada para ${e.value.periodicidade_sugerida.sugerida} meses.`)
		await carregar()
	} catch (err) {
		toast(err.message, "erro")
	} finally {
		aplicando.value = false
	}
}

const verificacaoAtrasada = computed(() => e.value?.proxima_verificacao && diasAte(e.value.proxima_verificacao) < 0)
const mostrarVerificacao = computed(() => e.value && (e.value.verificacao_intervalo_dias || e.value.verificacoes.length))

async function carregar() {
	try {
		e.value = await api("equipamento", { id: props.id })
	} catch (err) {
		erro.value = err.message
	}
}
onMounted(carregar)

const progresso = computed(() => {
	if (!e.value?.ultima_calibracao || !e.value?.proxima_calibracao) return null
	const total = diasAte(e.value.proxima_calibracao) - diasAte(e.value.ultima_calibracao)
	const passados = -diasAte(e.value.ultima_calibracao)
	return Math.min(100, Math.max(0, Math.round((100 * passados) / (total || 1))))
})

const campos = computed(() => [
	["Grandeza", e.value.grandeza],
	["Fabricante", e.value.fabricante],
	["Modelo", e.value.modelo],
	["Nº de série", e.value.numero_serie],
	["Faixa de medição", e.value.faixa_medicao],
	["Resolução", e.value.resolucao],
	...(e.value.distrito ? [["Distrito", e.value.distrito_nome]] : []),
	["Localização", e.value.localizacao],
	["Responsável", e.value.responsavel],
	["Periodicidade", e.value.periodicidade_meses ? `${e.value.periodicidade_meses} meses` : null],
	["Tolerância (±)", e.value.tolerancia ? `${numero(e.value.tolerancia)} ${e.value.unidade || ""}` : null],
	["Laboratório", e.value.calibrado_por === "Terceiro" ? e.value.fornecedor_externo : store.contexto.empresa],
	["Origem do cadastro", e.value.origem_cadastro === "Cliente" ? "Cadastrado por você" : "Laboratório"],
])

const grafTendencia = computed(() => {
	const t = e.value.tendencia
	return {
		grid: { left: 8, right: 16, top: 30, bottom: 4, containLabel: true },
		legend: { top: 0, right: 0, icon: "roundRect", itemWidth: 10, itemHeight: 10, textStyle: { color: COR.texto, fontSize: 12 } },
		tooltip: { ...tooltipBase, trigger: "axis", valueFormatter: (v) => numero(v) },
		xAxis: { type: "category", data: t.map((p) => data(p.data)), ...eixoBase, splitLine: { show: false } },
		yAxis: { type: "value", ...eixoBase, axisLabel: { ...eixoBase.axisLabel, formatter: (v) => numero(v) } },
		series: [
			{
				name: "|Erro| + U",
				type: "line",
				smooth: 0.3,
				symbolSize: 9,
				data: t.map((p) => ({ value: +(p.erro_max + p.incerteza).toFixed(6), itemStyle: { color: p.resultado === "Reprovado" ? COR.vermelho : COR.brand } })),
				lineStyle: { color: COR.brand, width: 2.5 },
				areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "rgba(59,103,245,.22)" }, { offset: 1, color: "rgba(59,103,245,0)" }] } },
			},
			{
				name: "Tolerância",
				type: "line",
				symbol: "none",
				data: t.map((p) => p.tolerancia),
				lineStyle: { color: COR.vermelho, type: "dashed", width: 1.5 },
				itemStyle: { color: COR.vermelho },
			},
		],
	}
})

const linkPublico = computed(() => `${location.origin}/cliente/equipamentos/${props.id}`)
</script>

<template>
	<div class="space-y-6">
		<RouterLink to="/equipamentos" class="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800">
			<ArrowLeft class="size-4" /> Equipamentos
		</RouterLink>

		<div v-if="erro" class="card p-6 text-sm text-rose-600">{{ erro }}</div>
		<div v-else-if="!e" class="card p-6"><Esqueleto :linhas="8" /></div>

		<template v-else>
			<!-- Cabeçalho -->
			<div class="card overflow-hidden">
				<div class="h-1.5" :style="{ background: COR_SITUACAO[e.situacao] }" />
				<div class="flex flex-wrap items-start justify-between gap-4 p-6">
					<div class="min-w-0">
						<div class="flex flex-wrap items-center gap-2">
							<h1 class="text-2xl font-semibold tracking-tight text-slate-900">{{ e.tag }}</h1>
							<Etiqueta :valor="e.situacao" />
							<Etiqueta :valor="e.status" :ponto="false" />
							<Etiqueta v-if="e.calibrado_por === 'Terceiro'" valor="Terceiro" :ponto="false">Calibrado por terceiro</Etiqueta>
						</div>
						<p class="mt-1 text-slate-600">{{ e.descricao }}</p>
						<p v-if="store.contexto.clientes.length > 1" class="mt-0.5 text-xs text-slate-400">{{ e.cliente }}</p>
					</div>
					<div class="flex flex-wrap gap-2">
						<button class="btn-secondary" title="QR Code para etiqueta" @click="qr = true"><QrCode class="size-4" /></button>
						<template v-if="podeEditar(e.cliente)">
							<button class="btn-secondary" @click="editar = true"><Pencil class="size-4" /> Editar</button>
							<button v-if="store.contexto.config.permitir_certificado_externo" class="btn-secondary" @click="enviarCert = true">
								<FileUp class="size-4" /> Certificado externo
							</button>
							<button class="btn-secondary" @click="verificar = true"><ClipboardCheck class="size-4" /> Verificação</button>
							<RouterLink :to="{ path: '/solicitar', query: { equipamentos: e.id } }" class="btn-primary"><Send class="size-4" /> Solicitar calibração</RouterLink>
						</template>
					</div>
				</div>
			</div>

			<div
				v-if="e.resultado_ultima_verificacao === 'Não Conforme'"
				class="flex flex-wrap items-center gap-4 rounded-2xl border border-rose-200 bg-rose-50 p-4"
			>
				<CircleX class="size-6 text-rose-600" />
				<p class="flex-1 text-sm text-rose-900">
					<b>A última verificação intermediária ({{ data(e.ultima_verificacao) }}) foi NÃO conforme.</b>
					Retire o equipamento de uso e solicite calibração.
				</p>
				<RouterLink v-if="podeEditar(e.cliente)" :to="{ path: '/solicitar', query: { equipamentos: e.id } }" class="btn-danger">Solicitar calibração</RouterLink>
			</div>

			<div class="grid gap-6 lg:grid-cols-3">
				<div class="space-y-6">
				<!-- Calibração -->
				<section class="card p-6">
					<h2 class="flex items-center gap-2 font-semibold text-slate-900"><CalendarCheck2 class="size-4 text-brand-600" /> Calibração</h2>
					<div class="mt-5 grid grid-cols-2 gap-4">
						<div>
							<p class="text-xs text-slate-500">Última</p>
							<p class="mt-0.5 font-semibold text-slate-900 tabular-nums">{{ data(e.ultima_calibracao) }}</p>
						</div>
						<div>
							<p class="text-xs text-slate-500">Próxima</p>
							<p class="mt-0.5 font-semibold tabular-nums" :class="e.situacao === 'Vencido' ? 'text-rose-600' : 'text-slate-900'">{{ data(e.proxima_calibracao) }}</p>
						</div>
					</div>
					<div v-if="progresso !== null" class="mt-5">
						<div class="mb-1.5 flex justify-between text-xs text-slate-500">
							<span>Ciclo de calibração</span>
							<span>{{ relativo(e.proxima_calibracao) }}</span>
						</div>
						<div class="h-2.5 overflow-hidden rounded-full bg-slate-100">
							<div class="h-full rounded-full transition-all" :style="{ width: progresso + '%', background: COR_SITUACAO[e.situacao] }" />
						</div>
					</div>
					<p v-else class="mt-5 rounded-xl bg-slate-50 p-3 text-sm text-slate-500">Nenhuma calibração registrada para este equipamento.</p>

					<dl class="mt-6 divide-y divide-slate-100 border-t border-slate-100">
						<div v-for="[k, v] in campos" :key="k" class="flex justify-between gap-4 py-2.5 text-sm">
							<dt class="text-slate-500">{{ k }}</dt>
							<dd class="text-right font-medium text-slate-800">{{ v || "—" }}</dd>
						</div>
					</dl>
				</section>

				<!-- Verificação intermediária -->
				<section v-if="mostrarVerificacao" class="card p-6">
					<div class="flex items-start justify-between gap-3">
						<h2 class="flex items-center gap-2 font-semibold text-slate-900"><ClipboardCheck class="size-4 text-brand-600" /> Verificação intermediária</h2>
						<button v-if="podeEditar(e.cliente)" class="btn-secondary -mt-1 px-2.5 py-1 text-xs" @click="verificar = true">Registrar</button>
					</div>
					<div class="mt-4 grid grid-cols-2 gap-4">
						<div>
							<p class="text-xs text-slate-500">Última</p>
							<p class="mt-0.5 flex items-center gap-1.5 font-semibold text-slate-900 tabular-nums">
								{{ data(e.ultima_verificacao) }}
								<CircleCheck v-if="e.resultado_ultima_verificacao === 'Conforme'" class="size-4 text-emerald-600" />
								<CircleX v-else-if="e.resultado_ultima_verificacao" class="size-4 text-rose-600" />
							</p>
						</div>
						<div>
							<p class="text-xs text-slate-500">Próxima</p>
							<p class="mt-0.5 font-semibold tabular-nums" :class="verificacaoAtrasada ? 'text-rose-600' : 'text-slate-900'">{{ data(e.proxima_verificacao) }}</p>
							<p v-if="e.proxima_verificacao" class="text-xs" :class="verificacaoAtrasada ? 'text-rose-600' : 'text-slate-400'">{{ relativo(e.proxima_verificacao) }}</p>
						</div>
					</div>
					<p class="mt-3 text-xs text-slate-500">
						A cada {{ e.verificacao_intervalo_dias || "—" }} dias · tolerância ± {{ numero(e.tolerancia_verificacao || e.tolerancia, 6) }}
					</p>
					<ul v-if="e.verificacoes.length" class="mt-4 divide-y divide-slate-100 border-t border-slate-100">
						<li v-for="v in e.verificacoes.slice(0, 6)" :key="v.id" class="flex items-center justify-between gap-3 py-2.5 text-sm">
							<div class="min-w-0">
								<p class="text-slate-800">{{ dataHora(v.data) }}</p>
								<p class="truncate text-xs text-slate-500">{{ v.realizado_por }} · desvio {{ v.pontos.map((p) => numero(p.desvio, 6)).join(" / ") }}</p>
							</div>
							<Etiqueta :valor="v.resultado === 'Conforme' ? 'Aprovado' : 'Reprovado'">{{ v.resultado }}</Etiqueta>
						</li>
					</ul>
				</section>
				</div>

				<div class="space-y-6 lg:col-span-2">
					<!-- Periodicidade inteligente -->
					<section v-if="e.periodicidade_sugerida" class="card overflow-hidden">
						<div class="flex flex-wrap items-start gap-4 p-6">
							<span class="grid size-10 shrink-0 place-items-center rounded-xl bg-violet-50 text-violet-600"><Sparkles class="size-5" /></span>
							<div class="min-w-0 flex-1">
								<h2 class="font-semibold text-slate-900">Periodicidade inteligente</h2>
								<p class="text-xs text-slate-500">
									{{ e.periodicidade_sugerida.metodo }} · {{ e.periodicidade_sugerida.calibracoes_analisadas }} calibração(ões) analisada(s) ·
									confiança {{ e.periodicidade_sugerida.confianca }}
								</p>
							</div>
							<div class="flex items-center gap-3 text-center">
								<div>
									<p class="text-[11px] text-slate-500">Atual</p>
									<p class="text-xl font-semibold text-slate-400 tabular-nums">{{ e.periodicidade_sugerida.atual }}<span class="text-xs"> m</span></p>
								</div>
								<span class="text-slate-300">→</span>
								<div>
									<p class="text-[11px] text-slate-500">Sugerida</p>
									<p
										class="text-xl font-semibold tabular-nums"
										:class="{ aumentar: 'text-emerald-600', reduzir: 'text-rose-600', manter: 'text-slate-900' }[e.periodicidade_sugerida.acao]"
									>
										{{ e.periodicidade_sugerida.sugerida }}<span class="text-xs"> m</span>
									</p>
								</div>
							</div>
						</div>
						<div class="border-t border-slate-100 bg-slate-50/60 px-6 py-4">
							<p class="text-sm text-slate-700">{{ e.periodicidade_sugerida.justificativa }}</p>
							<div class="mt-3 flex flex-wrap items-center justify-between gap-3">
								<p class="text-xs text-slate-500">
									Uso da tolerância na última calibração: <b>{{ e.periodicidade_sugerida.uso_ultimo_pct }}%</b>. A decisão final é sua (ILAC-G24).
								</p>
								<button
									v-if="e.periodicidade_sugerida.acao !== 'manter' && podeEditar(e.cliente)"
									class="btn-primary py-1.5"
									:disabled="aplicando"
									@click="aplicarSugestao"
								>
									Aplicar {{ e.periodicidade_sugerida.sugerida }} meses
								</button>
								<span v-else-if="e.periodicidade_sugerida.acao === 'manter'" class="text-xs font-medium text-emerald-700">Periodicidade atual adequada ✓</span>
							</div>
						</div>
					</section>

					<!-- Tendência -->
					<section class="card p-6">
						<h2 class="font-semibold text-slate-900">Tendência do erro</h2>
						<p class="text-xs text-slate-500">Pior ponto de cada calibração (|erro| + incerteza) frente à tolerância. Ajuda a decidir a periodicidade.</p>
						<Grafico v-if="e.tendencia.length > 1" class="mt-4" :opcoes="grafTendencia" altura="240px" />
						<p v-else class="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">São necessárias ao menos duas calibrações com pontos de medição para exibir a tendência.</p>
					</section>

					<!-- Histórico -->
					<section class="card overflow-hidden">
						<div class="px-6 pt-6 pb-3">
							<h2 class="font-semibold text-slate-900">Histórico de calibrações</h2>
						</div>
						<Vazio v-if="!e.certificados.length" :icone="FileCheck2" titulo="Sem certificados" texto="Os certificados emitidos aparecerão aqui." />
						<ol v-else class="relative px-6 pb-6">
							<li v-for="(c, i) in e.certificados" :key="c.id" class="relative flex gap-4 pb-5 last:pb-0">
								<span v-if="i < e.certificados.length - 1" class="absolute top-6 left-[11px] h-full w-px bg-slate-200" />
								<span class="relative z-10 mt-1 grid size-6 shrink-0 place-items-center rounded-full ring-4 ring-white" :class="c.resultado === 'Reprovado' ? 'bg-rose-100' : 'bg-emerald-100'">
									<span class="size-2 rounded-full" :class="c.resultado === 'Reprovado' ? 'bg-rose-500' : 'bg-emerald-500'" />
								</span>
								<RouterLink :to="`/certificados/${c.id}`" class="flex flex-1 flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-100 p-3 transition hover:border-slate-200 hover:bg-slate-50">
									<div>
										<p class="text-sm font-medium text-slate-900">{{ c.numero }}</p>
										<p class="text-xs text-slate-500">{{ data(c.data_calibracao) }} · {{ c.laboratorio }}<span v-if="c.acreditado"> · RBC</span></p>
									</div>
									<div class="flex items-center gap-2">
										<Etiqueta :valor="c.resultado" />
										<a v-if="c.tem_arquivo" :href="urlDownloadCertificado(c.id)" class="btn-ghost p-1.5" title="Baixar PDF" @click.stop><Download class="size-4" /></a>
									</div>
								</RouterLink>
							</li>
						</ol>
					</section>

					<!-- OS -->
					<section v-if="e.ordens.length" class="card overflow-hidden">
						<h2 class="px-6 pt-6 pb-3 font-semibold text-slate-900">Ordens de serviço</h2>
						<ul class="divide-y divide-slate-100">
							<li v-for="o in e.ordens" :key="o.id">
								<RouterLink :to="`/ordens/${o.id}`" class="flex items-center justify-between gap-3 px-6 py-3 hover:bg-slate-50">
									<div>
										<p class="text-sm font-medium text-slate-900">{{ o.id }}</p>
										<p class="text-xs text-slate-500">{{ o.tipo }} · {{ data(o.data_solicitacao) }}</p>
									</div>
									<Etiqueta :valor="o.status" />
								</RouterLink>
							</li>
						</ul>
					</section>
				</div>
			</div>
		</template>

		<RegistrarVerificacao v-if="verificar" :equipamento="e" @fechar="verificar = false" @salvo="(verificar = false), carregar()" />
		<FormEquipamento v-if="editar" :equipamento="e" @fechar="editar = false" @salvo="(editar = false), carregar()" />
		<EnviarCertificado v-if="enviarCert" :equipamento="e" @fechar="enviarCert = false" @salvo="(enviarCert = false), carregar()" />
		<Modal v-if="qr" titulo="QR Code do equipamento" subtitulo="Imprima e cole no instrumento: ao escanear, abre esta ficha." largura="max-w-sm" @fechar="qr = false">
			<div class="flex flex-col items-center gap-3">
				<img :src="`/api/method/solucoes.api.portal.qrcode?id=${encodeURIComponent(id)}`" class="size-56 rounded-xl border border-slate-100" alt="QR Code" />
				<p class="text-center text-lg font-semibold text-slate-900">{{ e.tag }}</p>
				<p class="text-center text-xs break-all text-slate-400">{{ linkPublico }}</p>
				<button class="btn-secondary" onclick="window.print()">Imprimir</button>
			</div>
		</Modal>
	</div>
</template>
