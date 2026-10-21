<script setup>
import {
	ArrowLeft,
	Award,
	Building2,
	CalendarClock,
	CircleCheck,
	ClipboardList,
	Download,
	FileText,
	FlaskConical,
	MapPin,
	NotebookPen,
	Pencil,
	Printer,
	ShieldCheck,
	TriangleAlert,
	Upload,
	UserRound,
} from "lucide-vue-next"
import { computed, onMounted, ref } from "vue"
import { api, urlApi, urlDownloadCertificado } from "@/api"
import EnviarCertificado from "@/components/EnviarCertificado.vue"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import FormEquipamento from "@/components/FormEquipamento.vue"
import LinhaEtapas from "@/components/LinhaEtapas.vue"
import Modal from "@/components/Modal.vue"
import { COR_STATUS } from "@/cores"
import { data, diasAte, relativo } from "@/format"
import { podeEditar, toast } from "@/store"

// Ficha completa de um equipamento: situação, histórico de calibrações, rastreabilidade e OS.
const props = defineProps({ id: { type: String, required: true } })

const h = ref(null)
const erro = ref(null)
const editar = ref(false)
const enviar = ref(false)
const obs = ref(null)

async function carregar() {
	try {
		h.value = await api("consulta.rastreabilidade", { id: props.id })
	} catch (e) {
		erro.value = e.message
	}
}
onMounted(carregar)

const e = computed(() => h.value?.equipamento)
const cor = computed(() => COR_STATUS[e.value?.status_calibracao] || "#94a3b8")
const pode = computed(() => e.value && podeEditar(e.value.cliente))

// Quanto da validade da calibração já foi consumido (anel do topo).
const validade = computed(() => {
	if (!e.value?.ultima_calibracao || !e.value?.proxima_calibracao) return null
	const ini = new Date(e.value.ultima_calibracao)
	const fim = new Date(e.value.proxima_calibracao)
	const total = (fim - ini) / 86400000
	const restante = diasAte(e.value.proxima_calibracao)
	const consumido = Math.min(100, Math.max(0, Math.round(((total - restante) / total) * 100)))
	return { consumido, restante, total: Math.round(total) }
})
const ANEL = 2 * Math.PI * 52

const situacaoTexto = computed(() => {
	const d = e.value?.dias_para_vencer
	if (d === null || d === undefined) return "Nenhuma calibração registrada"
	if (d < 0) return `Vencido há ${-d} dia(s)`
	if (d === 0) return "Vence hoje"
	return `Vence ${relativo(e.value.proxima_calibracao)}`
})

function validadePadrao(p) {
	const d = diasAte(p.validade)
	if (d === null) return { texto: "Validade não informada", classe: "text-slate-400" }
	if (d < 0) return { texto: `Vencido em ${data(p.validade)}`, classe: "text-rose-600" }
	if (d <= 60) return { texto: `Válido até ${data(p.validade)} · vence em ${d} dias`, classe: "text-amber-600" }
	return { texto: `Válido até ${data(p.validade)}`, classe: "text-emerald-700" }
}

function urlPadrao(p) {
	return urlApi("consulta.baixar_certificado_padrao", { os: h.value.os_padroes, linha: p.linha })
}

function imprimirEtiqueta() {
	const q = urlApi("portal.qrcode", { id: e.value.id })
	const w = window.open("", "_blank", "width=420,height=560")
	w.document.write(`<!doctype html><html><head><title>Etiqueta ${e.value.tag}</title><style>
		body{font-family:Inter,Arial,sans-serif;margin:0;display:grid;place-items:center;min-height:100vh}
		.e{width:62mm;border:1.5px solid #045a88;border-radius:10px;padding:10px 12px;text-align:center}
		.m{font-size:9px;letter-spacing:.14em;color:#045a88;font-weight:700;text-transform:uppercase}
		h1{font-size:14px;margin:4px 0 2px} p{margin:2px 0;font-size:10px;color:#334155} img{width:34mm;height:34mm;margin:6px auto}
		.v{margin-top:4px;padding-top:6px;border-top:1px dashed #cbd5e1;font-size:10px}
		.l{height:9mm;margin:0 auto 4px;display:block}
	</style></head><body><div class="e"><img class="l" src="/assets/solucoes/img/er-analitica.png"/><div class="m">Calibração</div><h1>${e.value.tag}</h1>
		<p>${e.value.descricao}</p><p>Série ${e.value.numero_serie || "—"}</p><img src="${q}" onload="setTimeout(()=>print(),300)"/>
		<div class="v">Próxima calibração: <b>${data(e.value.proxima_calibracao)}</b></div></div></body></html>`)
	w.document.close()
}

async function salvarObs() {
	try {
		await api("atualizar_equipamento", { id: e.value.id, dados: { observacao: obs.value || null } }, { post: true })
		toast("Observação salva.")
		obs.value = null
		carregar()
	} catch (err) {
		toast(err.message, "erro")
	}
}
</script>

<template>
	<div class="space-y-6">
		<RouterLink to="/equipamentos" class="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-brand-700">
			<ArrowLeft class="size-4" /> Equipamentos
		</RouterLink>

		<div v-if="erro" class="card flex items-center gap-3 p-6 text-sm text-rose-700"><TriangleAlert class="size-5" /> {{ erro }}</div>
		<template v-else-if="!h">
			<div class="card p-8"><Esqueleto :linhas="4" /></div>
			<div class="grid gap-6 lg:grid-cols-3"><div class="card p-6 lg:col-span-2"><Esqueleto :linhas="6" /></div><div class="card p-6"><Esqueleto :linhas="6" /></div></div>
		</template>

		<template v-else>
			<!-- Cabeçalho -->
			<section class="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-900 via-brand-700 to-brand-600 p-6 text-white shadow-pop sm:p-8">
				<div class="pointer-events-none absolute -top-24 -right-16 size-72 rounded-full bg-white/5" />
				<div class="pointer-events-none absolute -bottom-28 left-1/3 size-72 rounded-full bg-cyan-300/10" />
				<div class="relative flex flex-wrap items-center gap-8">
					<div class="min-w-0 flex-1">
						<div class="flex flex-wrap items-center gap-2">
							<span class="rounded-full bg-white/15 px-3 py-1 text-xs font-medium ring-1 ring-white/20 backdrop-blur">
								{{ e.origem === "laboratorio" ? "Calibrado pela ER Analítica" : `Calibrado por ${e.vendor}` }}
							</span>
							<span class="rounded-full px-3 py-1 text-xs font-semibold text-white ring-1 ring-white/25" :style="{ background: cor }">{{ e.status_calibracao }}</span>
						</div>
						<h1 class="mt-3 text-2xl font-semibold tracking-tight sm:text-3xl">{{ e.descricao }}</h1>
						<p class="mt-1 text-sm text-white/75">
							TAG <b class="text-white">{{ e.tag }}</b> · Série <b class="text-white">{{ e.numero_serie || "—" }}</b>
							<template v-if="e.fabricante || e.modelo"> · {{ [e.fabricante, e.modelo].filter(Boolean).join(" ") }}</template>
						</p>
						<div class="mt-5 flex flex-wrap gap-2">
							<template v-if="pode && e.editavel">
								<button class="inline-flex items-center gap-2 rounded-xl bg-white px-3.5 py-2 text-sm font-medium text-brand-800 hover:bg-brand-50" @click="enviar = true"><Upload class="size-4" /> Enviar certificado</button>
								<button class="inline-flex items-center gap-2 rounded-xl bg-white/10 px-3.5 py-2 text-sm font-medium ring-1 ring-white/25 hover:bg-white/20" @click="editar = true"><Pencil class="size-4" /> Editar</button>
							</template>
							<button v-else-if="pode" class="inline-flex items-center gap-2 rounded-xl bg-white/10 px-3.5 py-2 text-sm font-medium ring-1 ring-white/25 hover:bg-white/20" @click="obs = e.observacao || ''">
								<NotebookPen class="size-4" /> Observação
							</button>
							<button class="inline-flex items-center gap-2 rounded-xl bg-white/10 px-3.5 py-2 text-sm font-medium ring-1 ring-white/25 hover:bg-white/20" @click="imprimirEtiqueta"><Printer class="size-4" /> Etiqueta com QR</button>
						</div>
					</div>

					<!-- Anel de validade -->
					<div class="flex items-center gap-5 rounded-2xl bg-white/10 p-5 ring-1 ring-white/15 backdrop-blur">
						<svg viewBox="0 0 120 120" class="size-28 -rotate-90">
							<circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="10" />
							<circle
								v-if="validade"
								cx="60" cy="60" r="52" fill="none" :stroke="cor" stroke-width="10" stroke-linecap="round"
								:stroke-dasharray="ANEL" :stroke-dashoffset="ANEL * (1 - Math.max(0, 100 - validade.consumido) / 100)"
							/>
						</svg>
						<div>
							<p class="text-[11px] tracking-[0.16em] text-white/60 uppercase">Próxima calibração</p>
							<p class="text-2xl font-semibold">{{ data(e.proxima_calibracao) }}</p>
							<p class="text-sm text-white/80">{{ situacaoTexto }}</p>
							<p v-if="validade" class="mt-1 text-xs text-white/60">{{ Math.max(0, 100 - validade.consumido) }}% da validade restante</p>
						</div>
					</div>
				</div>
			</section>

			<div class="grid gap-6 lg:grid-cols-3">
				<div class="space-y-6 lg:col-span-2">
					<!-- Linha do tempo -->
					<section class="card p-6">
						<div class="flex items-center justify-between gap-2">
							<h2 class="flex items-center gap-2 font-semibold text-slate-900"><FileText class="size-4 text-brand-600" /> Histórico de calibrações</h2>
							<span class="text-xs text-slate-500">{{ h.certificados.length }} certificado(s)</span>
						</div>
						<p v-if="!h.certificados.length" class="mt-4 rounded-xl bg-slate-50 p-5 text-center text-sm text-slate-500">
							Nenhum certificado registrado.
							<template v-if="e.editavel"> Envie o certificado do laboratório externo para acompanhar a validade.</template>
						</p>
						<ol v-else class="relative mt-5 space-y-5 border-l-2 border-slate-100 pl-6">
							<li v-for="(c, i) in h.certificados" :key="c.id" class="relative">
								<span class="absolute top-1 -left-[33px] grid size-4 place-items-center rounded-full ring-4 ring-white" :class="i === 0 ? 'bg-brand-600' : 'bg-slate-300'" />
								<div class="flex flex-wrap items-start justify-between gap-3 rounded-2xl border border-slate-100 bg-slate-50/50 p-4 transition hover:border-brand-200 hover:bg-white">
									<div class="min-w-0">
										<p class="text-sm font-semibold text-slate-900">
											{{ data(c.data_calibracao) }}

										</p>
										<p class="mt-0.5 text-sm text-slate-600">Certificado <b class="font-medium text-slate-800">{{ c.numero }}</b> · válido até {{ data(c.data_validade) }}</p>
										<p class="mt-1 flex items-center gap-1.5 text-xs text-slate-500">
											<Award v-if="c.acreditado" class="size-3.5 text-brand-600" />
											{{ c.laboratorio }}{{ c.acreditado ? " · RBC" : "" }} · {{ c.fonte }}
										</p>
									</div>
									<div class="flex items-center gap-2">
										<Etiqueta :valor="c.vigencia" />
										<a v-if="c.tem_arquivo" :href="urlDownloadCertificado(c.id)" target="_blank" class="btn-secondary px-3 py-1.5 text-xs"><Download class="size-3.5" /> PDF</a>
									</div>
								</div>
							</li>
						</ol>
					</section>

					<!-- OS -->
					<section v-if="e.origem === 'laboratorio'" class="card p-6">
						<h2 class="flex items-center gap-2 font-semibold text-slate-900"><ClipboardList class="size-4 text-brand-600" /> Ordens de serviço no laboratório</h2>
						<p v-if="!h.ordens.length" class="mt-3 text-sm text-slate-500">Nenhuma ordem de serviço para este equipamento.</p>
						<div v-else class="mt-4 grid gap-3 sm:grid-cols-2">
							<RouterLink v-for="o in h.ordens" :key="o.id" :to="`/ordens/${o.id}`" class="group rounded-2xl border border-slate-100 p-4 transition hover:border-brand-200 hover:shadow-card">
								<div class="flex items-center justify-between gap-2">
									<p class="font-semibold text-slate-900 group-hover:text-brand-700">{{ o.id }}</p>
									<Etiqueta :valor="o.status" :ponto="false" />
								</div>
								<p class="mb-3 text-xs text-slate-500">{{ o.tipo }} · aberta em {{ data(o.data_solicitacao) }}</p>
								<LinhaEtapas :etapas="o.etapas" :atual="o.etapa_atual" compacta />
							</RouterLink>
						</div>
					</section>
				</div>

				<div class="space-y-6">
					<!-- Dados -->
					<section class="card p-6">
						<h2 class="font-semibold text-slate-900">Dados do equipamento</h2>
						<dl class="mt-4 space-y-3 text-sm">
							<div class="flex items-start gap-3"><FlaskConical class="mt-0.5 size-4 text-slate-400" /><div><dt class="text-xs text-slate-500">Grandeza · faixa</dt><dd class="font-medium text-slate-800">{{ e.grandeza || "—" }}{{ e.faixa_medicao ? ` · ${e.faixa_medicao}` : "" }}</dd></div></div>
							<div class="flex items-start gap-3"><CalendarClock class="mt-0.5 size-4 text-slate-400" /><div><dt class="text-xs text-slate-500">Periodicidade · última calibração</dt><dd class="font-medium text-slate-800">{{ e.periodicidade_meses ? `${e.periodicidade_meses} meses` : "—" }} · {{ data(e.ultima_calibracao) }}</dd></div></div>
							<div class="flex items-start gap-3"><MapPin class="mt-0.5 size-4 text-slate-400" /><div><dt class="text-xs text-slate-500">Distrito</dt><dd class="font-medium text-slate-800">{{ e.distrito_nome || "Sem distrito" }}<span v-if="e.cidade || e.uf" class="font-normal text-slate-500"> · {{ [e.cidade, e.uf].filter(Boolean).join("/") }}</span></dd></div></div>
							<div class="flex items-start gap-3"><UserRound class="mt-0.5 size-4 text-slate-400" /><div><dt class="text-xs text-slate-500">Responsável</dt><dd class="font-medium text-slate-800">{{ e.owner || "—" }}</dd><dd v-if="e.owner_email" class="text-xs text-slate-500">{{ e.owner_email }}</dd></div></div>
							<div class="flex items-start gap-3"><Building2 class="mt-0.5 size-4 text-slate-400" /><div><dt class="text-xs text-slate-500">Cliente</dt><dd class="font-medium text-slate-800">{{ e.cliente_nome }}</dd></div></div>
						</dl>
						<div class="mt-5 rounded-xl bg-amber-50/60 p-3 text-sm">
							<p class="text-xs font-medium text-amber-800">Observação da sua empresa</p>
							<p class="mt-0.5 text-slate-700">{{ e.observacao || "Nenhuma observação." }}</p>
						</div>
					</section>

					<!-- Rastreabilidade -->
					<section class="card p-6">
						<h2 class="flex items-center gap-2 font-semibold text-slate-900"><ShieldCheck class="size-4 text-brand-600" /> Rastreabilidade</h2>
						<p class="mt-0.5 text-xs text-slate-500">
							{{ h.os_padroes ? `Padrões usados na calibração vigente (${h.os_padroes})` : "Padrões de referência da calibração" }}
						</p>
						<p v-if="e.origem === 'cliente'" class="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">Calibração de outro laboratório: a rastreabilidade consta no certificado enviado.</p>
						<p v-else-if="!h.padroes.length" class="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">Nenhum padrão registrado na OS deste equipamento.</p>
						<ul v-else class="mt-4 space-y-3">
							<li v-for="p in h.padroes" :key="p.linha" class="rounded-2xl border border-slate-100 p-3.5">
								<div class="flex items-start justify-between gap-2">
									<div class="min-w-0">
										<p class="flex items-center gap-1.5 text-sm font-semibold text-slate-900"><CircleCheck class="size-3.5 text-emerald-600" /> {{ p.codigo }}</p>
										<p class="text-xs text-slate-500">{{ p.descricao }}</p>
									</div>
									<a v-if="p.tem_arquivo" :href="urlPadrao(p)" target="_blank" class="btn-ghost shrink-0 px-2 py-1 text-xs" title="Certificado do padrão"><Download class="size-3.5" /> PDF</a>
								</div>
								<p class="mt-2 text-xs text-slate-500">Certificado {{ p.numero_certificado || "—" }}</p>
								<p class="text-xs font-medium" :class="validadePadrao(p).classe">{{ validadePadrao(p).texto }}</p>
							</li>
						</ul>
					</section>
				</div>
			</div>
		</template>

		<FormEquipamento v-if="editar" :equipamento="e" @fechar="editar = false" @salvo="(editar = false), carregar()" />
		<EnviarCertificado v-if="enviar" :equipamento="e" @fechar="enviar = false" @salvo="(enviar = false), carregar()" />
		<Modal v-if="obs !== null" :titulo="`Observação · ${e.tag}`" subtitulo="Anotação da sua empresa sobre este equipamento (não altera os dados do laboratório)." @fechar="obs = null">
			<textarea v-model="obs" rows="4" class="input" placeholder="Ex.: fica na bancada 2 do laboratório de efluentes" />
			<template #rodape>
				<button class="btn-secondary" @click="obs = null">Cancelar</button>
				<button class="btn-primary" @click="salvarObs">Salvar</button>
			</template>
		</Modal>
	</div>
</template>
