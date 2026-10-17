<script setup>
import { ArrowLeft, ArrowRight, Building, Check, CircleCheckBig, FlaskConical, Search, Truck, Wrench } from "lucide-vue-next"
import { computed, onMounted, reactive, ref } from "vue"
import { useRoute } from "vue-router"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import SeletorCliente from "@/components/SeletorCliente.vue"
import { data } from "@/format"
import { podeEditar, precisaEscolherCliente, store, toast } from "@/store"

const route = useRoute()
const passo = ref(1)
const equipamentos = ref(null)
const selecionados = ref(new Set((route.query.equipamentos || "").split(",").filter(Boolean)))
const busca = ref("")
const enviando = ref(false)
const criada = ref(null)
const cliente = ref(store.cliente || "")

const f = reactive({ tipo: "Calibração", local_atendimento: "Laboratório", coleta: false, endereco_coleta: "", observacoes: "" })

const TIPOS = [
	{ valor: "Calibração", icone: FlaskConical, texto: "Emissão de certificado com análise de conformidade" },
	{ valor: "Manutenção", icone: Wrench, texto: "Diagnóstico e reparo, com laudo técnico" },
	{ valor: "Calibração + Manutenção", icone: Check, texto: "Reparo seguido de calibração" },
]

onMounted(async () => {
	equipamentos.value = (await api("equipamentos")).filter((e) => !["Inativo", "Sucateado"].includes(e.status))
	// pré-seleção vinda de outra tela define o cliente quando o usuário vê "Todos"
	const primeiro = equipamentos.value.find((e) => selecionados.value.has(e.id))
	if (primeiro && !cliente.value) cliente.value = primeiro.cliente
})

const escolherCliente = computed(() => precisaEscolherCliente())
const disponiveis = computed(() => {
	const termo = busca.value.trim().toLowerCase()
	return (equipamentos.value || [])
		.filter((e) => !escolherCliente.value || !cliente.value || e.cliente === cliente.value)
		.filter((e) => !termo || [e.tag, e.descricao, e.localizacao, e.numero_serie].some((v) => v?.toLowerCase().includes(termo)))
		.sort((a, b) => ordem(a) - ordem(b))
})
const listaSelecionados = computed(() => (equipamentos.value || []).filter((e) => selecionados.value.has(e.id)))

function ordem(e) {
	return { Vencido: 0, "A Vencer": 1, "Sem Calibração": 2, "Em Dia": 3 }[e.situacao] ?? 4
}

function alternar(id) {
	const s = new Set(selecionados.value)
	s.has(id) ? s.delete(id) : s.add(id)
	selecionados.value = s
}

function selecionarPendentes() {
	selecionados.value = new Set([...selecionados.value, ...disponiveis.value.filter((e) => ["Vencido", "A Vencer"].includes(e.situacao)).map((e) => e.id)])
}

function avancar() {
	if (passo.value === 1 && escolherCliente.value && !cliente.value) return toast("Selecione o cliente.", "erro")
	if (passo.value === 1 && !selecionados.value.size) return toast("Selecione ao menos um equipamento.", "erro")
	passo.value++
}

async function enviar() {
	enviando.value = true
	try {
		criada.value = await api(
			"solicitar_servico",
			{ dados: { ...f, equipamentos: [...selecionados.value] }, cliente: cliente.value || listaSelecionados.value[0]?.cliente },
			{ post: true },
		)
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		enviando.value = false
	}
}

const PASSOS = ["Equipamentos", "Detalhes", "Revisão"]
</script>

<template>
	<div class="mx-auto max-w-4xl space-y-6">
		<div v-if="!podeEditar()" class="card p-10 text-center">
			<p class="font-semibold text-slate-900">Seu perfil é somente consulta</p>
			<p class="mt-1 text-sm text-slate-500">Peça ao gestor da sua empresa para solicitar serviços ou alterar o seu perfil.</p>
			<RouterLink to="/" class="btn-secondary mt-5">Voltar ao painel</RouterLink>
		</div>

		<!-- Sucesso -->
		<div v-else-if="criada" class="card p-10 text-center">
			<span class="mx-auto grid size-16 place-items-center rounded-full bg-emerald-50 text-emerald-600"><CircleCheckBig class="size-8" /></span>
			<h1 class="mt-5 text-2xl font-semibold text-slate-900">Solicitação enviada!</h1>
			<p class="mt-2 text-slate-500">
				Abrimos a ordem <b class="text-slate-800">{{ criada.id }}</b> com {{ criada.qtd_itens }} equipamento(s). Você acompanha cada etapa por aqui.
			</p>
			<div class="mt-6 flex justify-center gap-2">
				<RouterLink to="/" class="btn-secondary">Voltar ao painel</RouterLink>
				<RouterLink :to="`/ordens/${criada.id}`" class="btn-primary">Acompanhar ordem <ArrowRight class="size-4" /></RouterLink>
			</div>
		</div>

		<template v-else>
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-slate-900">Solicitar serviço</h1>
				<p class="mt-1 text-sm text-slate-500">Em três passos, sem e-mail nem telefone.</p>
			</div>

			<!-- Indicador de passos -->
			<ol class="flex items-center gap-3">
				<li v-for="(p, i) in PASSOS" :key="p" class="flex flex-1 items-center gap-3">
					<span
						class="grid size-8 shrink-0 place-items-center rounded-full text-sm font-semibold transition"
						:class="i + 1 < passo ? 'bg-brand-600 text-white' : i + 1 === passo ? 'bg-brand-600 text-white ring-4 ring-brand-100' : 'bg-slate-200 text-slate-500'"
					>
						<Check v-if="i + 1 < passo" class="size-4" /><span v-else>{{ i + 1 }}</span>
					</span>
					<span class="hidden text-sm font-medium sm:inline" :class="i + 1 <= passo ? 'text-slate-900' : 'text-slate-400'">{{ p }}</span>
					<span v-if="i < PASSOS.length - 1" class="h-px flex-1" :class="i + 1 < passo ? 'bg-brand-500' : 'bg-slate-200'" />
				</li>
			</ol>

			<!-- Passo 1 -->
			<section v-if="passo === 1" class="card overflow-hidden">
				<div class="space-y-3 border-b border-slate-100 p-4">
					<SeletorCliente v-if="escolherCliente" v-model="cliente" />
					<div class="flex flex-wrap gap-3">
						<div class="relative min-w-[220px] flex-1">
							<Search class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" />
							<input v-model="busca" class="input pl-9" placeholder="Buscar equipamento…" />
						</div>
						<button class="btn-secondary" @click="selecionarPendentes">Selecionar vencidos e a vencer</button>
					</div>
				</div>
				<div v-if="!equipamentos" class="p-5"><Esqueleto :linhas="6" classe="h-10" /></div>
				<ul v-else class="max-h-[460px] divide-y divide-slate-100 overflow-y-auto">
					<li v-for="e in disponiveis" :key="e.id">
						<label class="flex cursor-pointer items-center gap-4 px-4 py-3 transition hover:bg-slate-50" :class="selecionados.has(e.id) && 'bg-brand-50/50'">
							<input type="checkbox" class="size-4 accent-brand-600" :checked="selecionados.has(e.id)" @change="alternar(e.id)" />
							<div class="min-w-0 flex-1">
								<p class="text-sm font-medium text-slate-900">{{ e.tag }} <span class="font-normal text-slate-500">· {{ e.descricao }}</span></p>
								<p class="text-xs text-slate-500">{{ e.localizacao || "—" }} · vence {{ data(e.proxima_calibracao) }}</p>
							</div>
							<Etiqueta :valor="e.situacao" />
						</label>
					</li>
				</ul>
				<div class="flex items-center justify-between border-t border-slate-100 p-4">
					<p class="text-sm text-slate-600"><b>{{ selecionados.size }}</b> selecionado(s)</p>
					<button class="btn-primary" @click="avancar">Continuar <ArrowRight class="size-4" /></button>
				</div>
			</section>

			<!-- Passo 2 -->
			<section v-else-if="passo === 2" class="card space-y-6 p-6">
				<div>
					<p class="label">Tipo de serviço</p>
					<div class="grid gap-3 sm:grid-cols-3">
						<button
							v-for="t in TIPOS"
							:key="t.valor"
							type="button"
							class="rounded-2xl border p-4 text-left transition"
							:class="f.tipo === t.valor ? 'border-brand-400 bg-brand-50/60 ring-4 ring-brand-100' : 'border-slate-200 hover:bg-slate-50'"
							@click="f.tipo = t.valor"
						>
							<component :is="t.icone" class="size-5" :class="f.tipo === t.valor ? 'text-brand-600' : 'text-slate-400'" />
							<p class="mt-2 text-sm font-semibold text-slate-900">{{ t.valor }}</p>
							<p class="mt-0.5 text-xs text-slate-500">{{ t.texto }}</p>
						</button>
					</div>
				</div>

				<div>
					<p class="label">Onde será o atendimento?</p>
					<div class="grid gap-3 sm:grid-cols-2">
						<button
							v-for="l in [
								{ v: 'Laboratório', i: Building, t: 'Os equipamentos vão até o laboratório' },
								{ v: 'In Loco', i: Truck, t: 'O técnico vai até a sua empresa' },
							]"
							:key="l.v"
							type="button"
							class="flex items-center gap-3 rounded-2xl border p-4 text-left transition"
							:class="f.local_atendimento === l.v ? 'border-brand-400 bg-brand-50/60 ring-4 ring-brand-100' : 'border-slate-200 hover:bg-slate-50'"
							@click="f.local_atendimento = l.v"
						>
							<component :is="l.i" class="size-5" :class="f.local_atendimento === l.v ? 'text-brand-600' : 'text-slate-400'" />
							<div>
								<p class="text-sm font-semibold text-slate-900">{{ l.v === "In Loco" ? "In loco" : l.v }}</p>
								<p class="text-xs text-slate-500">{{ l.t }}</p>
							</div>
						</button>
					</div>
				</div>

				<div v-if="f.local_atendimento === 'Laboratório'" class="rounded-2xl border border-slate-200 p-4">
					<label class="flex items-center gap-2.5 text-sm font-medium text-slate-800">
						<input v-model="f.coleta" type="checkbox" class="size-4 accent-brand-600" /> Quero que o laboratório faça a coleta
					</label>
					<textarea v-if="f.coleta" v-model="f.endereco_coleta" rows="2" class="input mt-3" placeholder="Endereço, contato e melhor horário para coleta" />
				</div>

				<div>
					<label class="label">Observações</label>
					<textarea v-model="f.observacoes" rows="3" class="input" placeholder="Pontos específicos de calibração, urgência, defeitos observados…" />
				</div>

				<div class="flex justify-between">
					<button class="btn-secondary" @click="passo--"><ArrowLeft class="size-4" /> Voltar</button>
					<button class="btn-primary" @click="avancar">Revisar <ArrowRight class="size-4" /></button>
				</div>
			</section>

			<!-- Passo 3 -->
			<section v-else class="card space-y-6 p-6">
				<dl class="grid gap-4 sm:grid-cols-3">
					<div class="rounded-xl bg-slate-50 p-4"><dt class="text-xs text-slate-500">Serviço</dt><dd class="mt-1 font-semibold text-slate-900">{{ f.tipo }}</dd></div>
					<div class="rounded-xl bg-slate-50 p-4">
						<dt class="text-xs text-slate-500">Atendimento</dt>
						<dd class="mt-1 font-semibold text-slate-900">{{ f.local_atendimento === "In Loco" ? "In loco" : f.coleta ? "Laboratório, com coleta" : "Laboratório" }}</dd>
					</div>
					<div class="rounded-xl bg-slate-50 p-4"><dt class="text-xs text-slate-500">Equipamentos</dt><dd class="mt-1 font-semibold text-slate-900">{{ selecionados.size }}</dd></div>
				</dl>
				<ul class="divide-y divide-slate-100 rounded-xl border border-slate-100">
					<li v-for="e in listaSelecionados" :key="e.id" class="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
						<span><b class="font-medium text-slate-900">{{ e.tag }}</b> <span class="text-slate-500">· {{ e.descricao }}</span></span>
						<Etiqueta :valor="e.situacao" />
					</li>
				</ul>
				<p v-if="f.observacoes" class="rounded-xl bg-slate-50 p-4 text-sm whitespace-pre-line text-slate-600">{{ f.observacoes }}</p>
				<div class="flex justify-between">
					<button class="btn-secondary" @click="passo--"><ArrowLeft class="size-4" /> Voltar</button>
					<button class="btn-primary" :disabled="enviando" @click="enviar">{{ enviando ? "Enviando…" : "Enviar solicitação" }}</button>
				</div>
			</section>
		</template>
	</div>
</template>
