<script setup>
import { ArrowLeft, Award, CircleCheck, CircleX, Download, ShieldCheck, ThumbsDown, ThumbsUp } from "lucide-vue-next"
import { computed, onMounted, ref } from "vue"
import { api, urlApi, urlDownloadCertificado } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import Grafico from "@/components/Grafico.vue"
import { COR, eixoBase, tooltipBase } from "@/cores"
import { data, dataHora, numero } from "@/format"
import { CONSULTA } from "@/modo"
import { podeEditar, toast } from "@/store"

const props = defineProps({ id: String })
const c = ref(null)
const erro = ref(null)
const observacao = ref("")
const salvando = ref(false)

onMounted(async () => {
	try {
		c.value = await api("certificado", { id: props.id })
		observacao.value = c.value.observacao_analise || ""
	} catch (e) {
		erro.value = e.message
	}
})

async function analisar(status) {
	salvando.value = true
	try {
		c.value = await api("analisar_certificado", { id: props.id, status, observacao: observacao.value }, { post: true })
		toast(`Análise crítica registrada: ${status}.`)
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		salvando.value = false
	}
}

// Fase 1 (/consulta): situação pela validade; resultado de medição é da fase 2.
const situacao = computed(() => (CONSULTA ? c.value?.vigencia : c.value?.resultado))
const temCriterio = computed(() => c.value?.pontos.some((p) => p.tolerancia))

// Gráfico de calibração: erro de cada ponto com barra de incerteza (±U), dentro da faixa de tolerância.
const grafPontos = computed(() => {
	const pts = c.value.pontos
	const nominais = pts.map((p) => numero(p.valor_nominal))
	const tol = pts.map((p) => p.tolerancia || null)
	const un = c.value.unidade ? ` ${c.value.unidade}` : ""
	return {
		grid: { left: 8, right: 16, top: 34, bottom: 24, containLabel: true },
		legend: { top: 0, right: 0, icon: "roundRect", itemWidth: 10, itemHeight: 10, textStyle: { color: COR.texto, fontSize: 12 } },
		tooltip: {
			...tooltipBase,
			trigger: "axis",
			formatter: (params) => {
				const p = pts[params[0].dataIndex]
				return `<b>Nominal ${numero(p.valor_nominal)}${un}</b><br/>Medido: ${numero(p.valor_medido)}<br/>Erro: ${numero(p.erro)}<br/>U: ±${numero(p.incerteza)}<br/>Tolerância: ±${numero(p.tolerancia)}<br/>${p.conforme ? "✅ Conforme" : "❌ Não conforme"}`
			},
		},
		xAxis: { type: "category", data: nominais, name: `Valor nominal${un}`, nameLocation: "middle", nameGap: 28, nameTextStyle: { color: COR.texto, fontSize: 11 }, ...eixoBase, splitLine: { show: false } },
		yAxis: { type: "value", ...eixoBase, axisLabel: { ...eixoBase.axisLabel, formatter: (v) => numero(v) } },
		series: [
			{
				name: "Tolerância",
				type: "line",
				step: "middle",
				symbol: "none",
				data: tol,
				lineStyle: { color: COR.vermelho, type: "dashed", width: 1.5 },
				itemStyle: { color: COR.vermelho },
				areaStyle: { color: "rgba(16,185,129,.07)", origin: 0 },
			},
			{
				name: "Tolerância ",
				type: "line",
				step: "middle",
				symbol: "none",
				data: tol.map((t) => (t === null ? null : -t)),
				lineStyle: { color: COR.vermelho, type: "dashed", width: 1.5 },
				areaStyle: { color: "rgba(16,185,129,.07)", origin: 0 },
				legendHoverLink: false,
				tooltip: { show: false },
			},
			{
				name: "Incerteza (±U)",
				type: "custom",
				itemStyle: { color: COR.texto },
				renderItem: (params, api) => {
					const i = api.value(0)
					const baixo = api.coord([i, api.value(1)])
					const alto = api.coord([i, api.value(2)])
					const w = 6
					const estilo = { stroke: "#64748b", lineWidth: 1.5 }
					return {
						type: "group",
						children: [
							{ type: "line", shape: { x1: baixo[0], y1: baixo[1], x2: alto[0], y2: alto[1] }, style: estilo },
							{ type: "line", shape: { x1: baixo[0] - w, y1: baixo[1], x2: baixo[0] + w, y2: baixo[1] }, style: estilo },
							{ type: "line", shape: { x1: alto[0] - w, y1: alto[1], x2: alto[0] + w, y2: alto[1] }, style: estilo },
						],
					}
				},
				encode: { x: 0, y: [1, 2] },
				data: pts.map((p, i) => [i, p.erro - (p.incerteza || 0), p.erro + (p.incerteza || 0)]),
				z: 3,
			},
			{
				name: "Erro",
				type: "line",
				symbolSize: 11,
				lineStyle: { color: COR.brandClaro, width: 1.5 },
				data: pts.map((p) => ({ value: p.erro, itemStyle: { color: p.conforme || !p.tolerancia ? COR.brand : COR.vermelho, borderColor: "#fff", borderWidth: 2 } })),
				itemStyle: { color: COR.brand },
				z: 4,
			},
		],
	}
})
</script>

<template>
	<div class="space-y-6">
		<RouterLink to="/certificados" class="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800">
			<ArrowLeft class="size-4" /> Certificados
		</RouterLink>

		<div v-if="erro" class="card p-6 text-sm text-rose-600">{{ erro }}</div>
		<div v-else-if="!c" class="card p-6"><Esqueleto :linhas="8" /></div>

		<template v-else>
			<div class="card flex flex-wrap items-center gap-5 p-6">
				<span
					class="grid size-14 shrink-0 place-items-center rounded-2xl"
					:class="situacao === 'Reprovado' || situacao === 'Vencido' ? 'bg-rose-50 text-rose-600' : situacao === 'Aprovado' || situacao === 'Vigente' ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-500'"
				>
					<CircleX v-if="situacao === 'Reprovado' || situacao === 'Vencido'" class="size-7" />
					<CircleCheck v-else class="size-7" />
				</span>
				<div class="min-w-0 flex-1">
					<div class="flex flex-wrap items-center gap-2">
						<h1 class="text-2xl font-semibold tracking-tight text-slate-900">{{ c.numero }}</h1>
						<Etiqueta :valor="situacao" />
						<Etiqueta v-if="c.origem === 'Externo'" valor="Externo" :ponto="false">Emitido por terceiro</Etiqueta>
					</div>
					<RouterLink :to="`/equipamentos/${c.equipamento_id}`" class="mt-1 inline-block text-slate-600 hover:text-brand-700">
						{{ c.tag }} · {{ c.descricao_equipamento }}
					</RouterLink>
				</div>
				<a v-if="c.tem_arquivo" :href="urlDownloadCertificado(c.id)" class="btn-primary"><Download class="size-4" /> Baixar PDF</a>
				<span v-else class="text-sm text-slate-400">PDF ainda não anexado</span>
			</div>

			<div class="grid gap-6 lg:grid-cols-3">
				<div class="space-y-6 lg:col-span-2">
					<!-- Fase 1: rastreabilidade em destaque (os resultados de medição ficam no PDF) -->
					<section v-if="CONSULTA" class="card p-6">
						<h2 class="flex items-center gap-2 font-semibold text-slate-900"><ShieldCheck class="size-4 text-brand-600" /> Rastreabilidade — padrões utilizados</h2>
						<p class="text-xs text-slate-500">Padrões de referência usados nesta calibração. Os resultados das medições estão no PDF do certificado.</p>
						<p v-if="!c.padroes?.length" class="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
							{{ c.origem === "Externo" ? "Certificado de outro laboratório: a rastreabilidade consta no PDF." : "Nenhum padrão registrado para esta calibração." }}
						</p>
						<ul v-else class="mt-4 grid gap-3 sm:grid-cols-2">
							<li v-for="p in c.padroes" :key="p.linha || p.codigo" class="flex items-start justify-between gap-3 rounded-xl border border-slate-100 p-3.5">
								<div class="min-w-0">
									<p class="text-sm font-semibold text-slate-900">{{ p.codigo }}</p>
									<p class="text-xs text-slate-500">{{ p.descricao }}</p>
									<p class="mt-1 text-xs text-slate-600">Cert. {{ p.numero_certificado || "—" }} · válido até {{ data(p.validade) }}</p>
								</div>
								<a v-if="p.tem_arquivo" :href="urlApi('consulta.baixar_certificado_padrao', { os: c.id, linha: p.linha })" target="_blank" class="btn-secondary shrink-0 px-2.5 py-1 text-xs">
									<Download class="size-3.5" /> PDF
								</a>
							</li>
						</ul>
					</section>
					<section v-if="!CONSULTA" class="card p-6">
						<h2 class="font-semibold text-slate-900">Resultados da calibração</h2>
						<p class="text-xs text-slate-500">
							Critério: o ponto é conforme quando |erro| + U ≤ tolerância. Área verde = faixa aceitável.
						</p>
						<Grafico v-if="c.pontos.length" class="mt-4" :opcoes="grafPontos" altura="300px" />
						<p v-else class="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">Este certificado não possui pontos de medição registrados no portal. Consulte o PDF.</p>
					</section>

					<section v-if="!CONSULTA && c.pontos.length" class="card overflow-hidden">
						<div class="overflow-x-auto">
							<table class="w-full min-w-[620px]">
								<thead class="border-b border-slate-100 bg-slate-50/60">
									<tr>
										<th class="th">Nominal</th>
										<th v-if="c.ajustado" class="th">Antes do ajuste</th>
										<th class="th">Medido</th>
										<th class="th">Erro</th>
										<th class="th">Incerteza (U)</th>
										<th class="th">Tolerância (±)</th>
										<th class="th">Conformidade</th>
									</tr>
								</thead>
								<tbody class="divide-y divide-slate-100 tabular-nums">
									<tr v-for="(p, i) in c.pontos" :key="i">
										<td class="td font-medium text-slate-900">{{ numero(p.valor_nominal) }} <span class="text-xs text-slate-400">{{ c.unidade }}</span></td>
										<td v-if="c.ajustado" class="td text-slate-500">{{ numero(p.valor_encontrado) }}</td>
										<td class="td">{{ numero(p.valor_medido, 6) }}</td>
										<td class="td" :class="p.conforme || !p.tolerancia ? 'text-slate-700' : 'font-semibold text-rose-600'">{{ numero(p.erro, 6) }}</td>
										<td class="td text-slate-600">± {{ numero(p.incerteza, 6) }}</td>
										<td class="td text-slate-600">{{ p.tolerancia ? `± ${numero(p.tolerancia, 6)}` : "—" }}</td>
										<td class="td">
											<Etiqueta v-if="p.tolerancia" :valor="p.conforme ? 'Aprovado' : 'Reprovado'">{{ p.conforme ? "Conforme" : "Não conforme" }}</Etiqueta>
											<span v-else class="text-xs text-slate-400">Sem critério</span>
										</td>
									</tr>
								</tbody>
							</table>
						</div>
					</section>
				</div>

				<div class="space-y-6">
					<!-- Análise crítica -->
					<section v-if="!CONSULTA" class="card p-6">
						<h2 class="flex items-center gap-2 font-semibold text-slate-900"><ShieldCheck class="size-4 text-brand-600" /> Análise crítica</h2>
						<p class="mt-1 text-xs text-slate-500">Registro exigido pela ISO 9001 / IATF 16949: o cliente avalia se o equipamento atende ao uso pretendido.</p>

						<div v-if="c.status_analise !== 'Pendente'" class="mt-4 rounded-xl p-3 text-sm" :class="c.status_analise === 'Aprovado' ? 'bg-emerald-50 text-emerald-800' : 'bg-rose-50 text-rose-800'">
							<p class="font-semibold">{{ c.status_analise === "Aprovado" ? "Aprovado para uso" : "Reprovado para uso" }}</p>
							<p class="mt-0.5 text-xs opacity-80">por {{ c.analisado_por }} em {{ dataHora(c.data_analise) }}</p>
						</div>
						<div v-else-if="temCriterio" class="mt-4 rounded-xl bg-brand-50 p-3 text-sm text-brand-800">
							Sugestão automática: <b>{{ c.resultado === "Reprovado" ? "reprovar" : "aprovar" }}</b>, com base na tolerância cadastrada.
						</div>

						<template v-if="podeEditar(c.cliente)">
							<label class="label mt-4">Observação</label>
							<textarea v-model="observacao" rows="3" class="input" placeholder="Ex.: apto para uso no controle dimensional da linha 2" />
							<div class="mt-3 grid grid-cols-2 gap-2">
								<button class="btn-success" :disabled="salvando" @click="analisar('Aprovado')"><ThumbsUp class="size-4" /> Aprovar</button>
								<button class="btn-danger" :disabled="salvando" @click="analisar('Reprovado')"><ThumbsDown class="size-4" /> Reprovar</button>
							</div>
						</template>
						<p v-else-if="observacao" class="mt-4 rounded-xl bg-slate-50 p-3 text-sm text-slate-600">{{ observacao }}</p>
					</section>

					<section class="card p-6">
						<h2 class="font-semibold text-slate-900">Dados do certificado</h2>
						<dl class="mt-3 divide-y divide-slate-100 text-sm">
							<div class="flex justify-between gap-4 py-2.5"><dt class="text-slate-500">Data da calibração</dt><dd class="font-medium">{{ data(c.data_calibracao) }}</dd></div>
							<div v-if="CONSULTA" class="flex justify-between gap-4 py-2.5"><dt class="text-slate-500">Situação</dt><dd><Etiqueta :valor="c.vigencia" /></dd></div>
							<div class="flex justify-between gap-4 py-2.5"><dt class="text-slate-500">Válido até</dt><dd class="font-medium">{{ data(c.data_validade) }}</dd></div>
							<div class="flex justify-between gap-4 py-2.5">
								<dt class="text-slate-500">Laboratório</dt>
								<dd class="flex items-center gap-1 text-right font-medium">{{ c.laboratorio }} <Award v-if="c.acreditado" class="size-3.5 text-brand-500" /></dd>
							</div>
							<div class="flex justify-between gap-4 py-2.5"><dt class="text-slate-500">Acreditação</dt><dd class="font-medium">{{ c.acreditado ? "RBC / ISO/IEC 17025" : "Rastreável" }}</dd></div>
							<div v-if="c.tecnico" class="flex justify-between gap-4 py-2.5"><dt class="text-slate-500">Técnico</dt><dd class="font-medium">{{ c.tecnico }}</dd></div>
							<div v-if="!CONSULTA" class="flex justify-between gap-4 py-2.5"><dt class="text-slate-500">Ajustado</dt><dd class="font-medium">{{ c.ajustado ? "Sim" : "Não" }}</dd></div>
						</dl>
						<div v-if="!CONSULTA && c.padroes?.length" class="mt-4">
							<p class="text-xs font-medium text-slate-500">Rastreabilidade — padrões utilizados</p>
							<ul class="mt-2 space-y-2">
								<li v-for="p in c.padroes" :key="p.linha || p.codigo" class="flex items-start justify-between gap-3 rounded-xl border border-slate-100 p-3">
									<div class="min-w-0">
										<p class="flex items-center gap-1.5 text-sm font-medium text-slate-900">
											{{ p.codigo }} <Award v-if="p.acreditado" class="size-3.5 text-brand-500" />
										</p>
										<p class="text-xs text-slate-500">{{ p.descricao }}</p>
										<p class="mt-1 text-xs text-slate-600">{{ ["Cert. " + (p.numero_certificado || "—"), p.laboratorio, "válido até " + data(p.validade)].filter(Boolean).join(" · ") }}</p>
									</div>
									<a
										v-if="CONSULTA && p.tem_arquivo"
										:href="urlApi('consulta.baixar_certificado_padrao', { os: c.id, linha: p.linha })"
										target="_blank"
										class="btn-secondary shrink-0 px-2.5 py-1 text-xs"
										title="Certificado de calibração do padrão"
									>
										<Download class="size-3.5" /> PDF
									</a>
								</li>
							</ul>
						</div>
						<div v-else-if="!CONSULTA && c.padroes_utilizados" class="mt-3 rounded-xl bg-slate-50 p-3">
							<p class="text-xs font-medium text-slate-500">Padrões / rastreabilidade</p>
							<p class="mt-1 text-sm whitespace-pre-line text-slate-700">{{ c.padroes_utilizados }}</p>
						</div>
					</section>
				</div>
			</div>
		</template>
	</div>
</template>
