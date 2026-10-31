<script setup>
import { ArrowLeft, Check, FileText, ListPlus, Plus, Search, Send, Trash2, X } from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { api } from "@/api"
import CadastroFiscal from "@/components/CadastroFiscal.vue"
import Checagens from "@/components/Checagens.vue"
import Esqueleto from "@/components/Esqueleto.vue"
import Modal from "@/components/Modal.vue"
import Resultado from "@/components/Resultado.vue"
import { moeda } from "@/format"
import { toast } from "@/store"

const route = useRoute()
const router = useRouter()
const naturezas = ref([])
const f = ref({ natureza: route.query.natureza || "", tipo_parte: "Customer", parte: "", nome: "", nf_referenciada: "", prazo_retorno: "", observacao: "", itens: [] })
const busca = ref("")
const achados = ref([])
const conf = ref(null)
const cadastro = ref(false)
const escolher = ref(null) // lista de equipamentos
const marcados = ref([])
const emitindo = ref(false)
const confirmar = ref(false)
const resultado = ref(null)

const nat = computed(() => naturezas.value.find((n) => n.name === f.value.natureza))
// quem costuma ser o destinatário de cada operação
const PARTE_PADRAO = { "Remessa para conserto ou calibração": "Supplier", "Retorno de demonstração": "Supplier" }

onMounted(async () => {
	naturezas.value = await api("naturezas_avulsas")
	if (f.value.natureza) escolherNatureza(f.value.natureza, false)
})

function escolherNatureza(nome, limpar = true) {
	f.value.natureza = nome
	f.value.tipo_parte = PARTE_PADRAO[nome] || "Customer"
	if (limpar) Object.assign(f.value, { parte: "", nome: "", itens: [] })
}

let esperaBusca
watch([busca, () => f.value.tipo_parte], () => {
	clearTimeout(esperaBusca)
	esperaBusca = setTimeout(async () => {
		achados.value = busca.value.length >= 2 ? await api("buscar_partes", { tipo_parte: f.value.tipo_parte, texto: busca.value }) : []
	}, 250)
})

function selecionar(p) {
	f.value.parte = p.name
	f.value.nome = p.nome
	busca.value = ""
	achados.value = []
}

async function abrirEquipamentos() {
	escolher.value = null
	marcados.value = []
	escolher.value = await api("equipamentos", { tipo_parte: f.value.tipo_parte, parte: f.value.parte })
}

function adicionarMarcados() {
	for (const e of escolher.value.filter((x) => marcados.value.includes(x.name))) {
		f.value.itens.push({ descricao: [e.descricao, e.fabricante, e.modelo].filter(Boolean).join(" "), numero_serie: e.numero_serie, referencia: e.name, ncm: "", quantidade: 1, valor_unitario: null })
	}
	escolher.value = null
}

function novoItem() {
	f.value.itens.push({ descricao: "", numero_serie: "", ncm: "", quantidade: 1, valor_unitario: null })
}

// conferência ao vivo
async function conferir() {
	if (!f.value.natureza) return (conf.value = null)
	conf.value = await api("conferir_avulsa", { dados: f.value }, { post: true }).catch((e) => ({ checagens: [{ nivel: "erro", texto: e.message }], pode_emitir: false }))
}
let esperaConf
watch(
	f,
	() => {
		clearTimeout(esperaConf)
		esperaConf = setTimeout(conferir, 400)
	},
	{ deep: true, immediate: true },
)

async function emitir() {
	emitindo.value = true
	try {
		resultado.value = await api("emitir_avulsa", { dados: f.value }, { post: true })
		confirmar.value = false
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		emitindo.value = false
	}
}
</script>

<template>
	<div class="space-y-5">
		<button class="btn-fantasma -ml-2" @click="router.push('/remessas')"><ArrowLeft class="size-4" /> Remessa e retorno</button>
		<h1 class="text-2xl font-semibold tracking-tight text-tinta">Nova remessa ou retorno</h1>

		<div class="grid gap-5 lg:grid-cols-5">
			<div class="space-y-5 lg:col-span-3">
				<!-- 1. operação -->
				<section class="card p-5">
					<p class="mb-3 text-sm font-semibold text-tinta">1. O que você precisa fazer?</p>
					<Esqueleto v-if="!naturezas.length" :linhas="3" classe="h-12" />
					<div class="grid gap-2">
						<button v-for="n in naturezas" :key="n.name" class="flex items-start gap-3 rounded-xl border p-3 text-left transition"
							:class="f.natureza === n.name ? 'border-marca-500 bg-marca-500/8' : 'border-borda hover:bg-realce'" @click="escolherNatureza(n.name)">
							<span class="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border" :class="f.natureza === n.name ? 'border-marca-600 bg-marca-600 text-white' : 'border-borda'"><Check v-if="f.natureza === n.name" class="size-3" /></span>
							<span>
								<span class="block text-sm font-medium text-tinta">{{ n.name }} <span class="font-normal text-suave">· CFOP {{ n.cfop_dentro_estado }}/{{ n.cfop_fora_estado }}</span></span>
								<span class="block text-xs text-suave">{{ n.explicacao }}</span>
							</span>
						</button>
					</div>
				</section>

				<!-- 2. destinatário -->
				<section v-if="nat" class="card p-5">
					<p class="mb-3 text-sm font-semibold text-tinta">2. Para quem?</p>
					<div class="mb-3 inline-flex rounded-xl border border-borda p-0.5 text-sm">
						<button v-for="[v, r] in [['Customer', 'Cliente'], ['Supplier', 'Fornecedor']]" :key="v" class="rounded-lg px-3 py-1" :class="f.tipo_parte === v ? 'bg-marca-600 text-white' : 'text-suave'"
							@click="f.tipo_parte = v; f.parte = ''; f.nome = ''">{{ r }}</button>
					</div>
					<div v-if="f.parte" class="flex items-center gap-3 rounded-xl border border-borda p-3">
						<div class="min-w-0 flex-1"><p class="font-medium text-tinta">{{ f.nome }}</p><p class="text-xs text-suave">{{ f.parte }}</p></div>
						<button class="btn-fantasma px-2 py-1 text-xs" @click="cadastro = true"><FileText class="size-3.5" /> Cadastro fiscal</button>
						<button class="btn-fantasma p-1.5" aria-label="Trocar" @click="f.parte = ''; f.nome = ''"><X class="size-4" /></button>
					</div>
					<div v-else class="relative">
						<Search class="absolute top-2.5 left-3 size-4 text-suave" />
						<input v-model="busca" class="campo pl-9" :placeholder="`Buscar ${f.tipo_parte === 'Customer' ? 'cliente' : 'fornecedor'} por nome ou CNPJ`" />
						<div v-if="achados.length" class="absolute z-10 mt-1 w-full rounded-xl border border-borda bg-elevada p-1 shadow-pop">
							<button v-for="p in achados" :key="p.name" class="block w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-realce" @click="selecionar(p)">
								<span class="text-tinta">{{ p.nome }}</span> <span class="text-xs text-suave">{{ p.tax_id }}</span>
							</button>
						</div>
					</div>
				</section>

				<!-- 3. nota de origem -->
				<section v-if="nat?.exige_nf_referenciada && f.parte" class="card p-5">
					<p class="text-sm font-semibold text-tinta">3. Nota com que o equipamento chegou</p>
					<p class="mb-3 text-xs text-suave">A chave de acesso tem 44 números e fica no alto do DANFE, perto do código de barras.</p>
					<input v-model="f.nf_referenciada" class="campo font-mono" placeholder="3526 1045 9974 1800 0153 5500 1000 0045 2113 1415 9261" />
				</section>

				<!-- 4. itens -->
				<section v-if="nat && f.parte" class="card p-5">
					<div class="mb-3 flex flex-wrap items-center gap-2">
						<p class="text-sm font-semibold text-tinta">{{ nat.exige_nf_referenciada ? "4" : "3" }}. Equipamentos</p>
						<button class="btn-secundario ml-auto px-2.5 py-1.5 text-xs" @click="abrirEquipamentos"><ListPlus class="size-3.5" /> {{ f.tipo_parte === "Customer" ? "Escolher dos equipamentos do cliente" : "Escolher dos nossos padrões" }}</button>
						<button class="btn-fantasma px-2.5 py-1.5 text-xs" @click="novoItem"><Plus class="size-3.5" /> Item avulso</button>
					</div>
					<p v-if="!f.itens.length" class="rounded-xl border border-dashed border-borda p-4 text-center text-sm text-suave">Adicione os equipamentos que vão na nota.</p>
					<div v-for="(i, k) in f.itens" :key="k" class="mb-2 grid gap-2 rounded-xl border border-borda p-3 sm:grid-cols-12">
						<div class="sm:col-span-12 flex gap-2">
							<input v-model="i.descricao" class="campo" placeholder="Descrição (ex.: Balança analítica 220 g)" />
							<button class="btn-fantasma p-2 text-rose-600" aria-label="Remover" @click="f.itens.splice(k, 1)"><Trash2 class="size-4" /></button>
						</div>
						<div class="sm:col-span-3"><label class="rotulo">Nº de série</label><input v-model="i.numero_serie" class="campo" /></div>
						<div class="sm:col-span-3"><label class="rotulo">NCM (8 dígitos)</label><input v-model="i.ncm" class="campo" placeholder="90318099" /></div>
						<div class="sm:col-span-2"><label class="rotulo">Qtd</label><input v-model.number="i.quantidade" type="number" min="1" class="campo" /></div>
						<div class="sm:col-span-4"><label class="rotulo">Valor unitário declarado</label><input v-model.number="i.valor_unitario" type="number" step="0.01" class="campo" placeholder="o mesmo da nota de origem" /></div>
					</div>
				</section>

				<section v-if="nat && f.parte" class="card grid gap-3 p-5 sm:grid-cols-2">
					<div v-if="nat.controla_retorno"><label class="rotulo">Volta até (se vazio, prazo padrão)</label><input v-model="f.prazo_retorno" type="date" class="campo" /></div>
					<div :class="!nat.controla_retorno && 'sm:col-span-2'"><label class="rotulo">Observação na nota (opcional)</label><input v-model="f.observacao" class="campo" placeholder="Ex.: OS 2026-00123" /></div>
				</section>
			</div>

			<aside class="lg:col-span-2">
				<div class="card sticky top-20 space-y-4 p-5">
					<p class="text-xs font-semibold tracking-wider text-suave uppercase">Conferência</p>
					<p v-if="!conf" class="text-sm text-suave">Escolha a operação para começar.</p>
					<template v-else>
						<p v-if="conf.resumo" class="text-sm text-tinta">{{ conf.resumo }}</p>
						<p v-if="conf.texto_complementar" class="rounded-xl bg-realce/70 px-3 py-2 text-xs text-suave">Texto na nota: “{{ conf.texto_complementar }}”</p>
						<Checagens :itens="conf.checagens" compacto @acao="(a) => a === 'cadastro' && (cadastro = true)" />
						<button class="btn-primario w-full py-2.5" :disabled="!conf.pode_emitir" @click="confirmar = true"><Send class="size-4" /> Emitir NF-e</button>
					</template>
				</div>
			</aside>
		</div>

		<Modal v-if="escolher" :titulo="f.tipo_parte === 'Customer' ? 'Equipamentos do cliente' : 'Nossos padrões e equipamentos'" largura="max-w-xl" @fechar="escolher = null">
			<p v-if="!escolher.length" class="text-sm text-suave">Nenhum equipamento cadastrado. Use “Item avulso”.</p>
			<label v-for="e in escolher" :key="e.name" class="flex cursor-pointer items-start gap-3 rounded-xl px-2 py-2 hover:bg-realce">
				<input v-model="marcados" type="checkbox" :value="e.name" class="mt-1 accent-marca-600" />
				<span class="text-sm"><span class="text-tinta">{{ e.texto }}</span><span class="block text-xs text-suave">Série {{ e.numero_serie || "—" }} · {{ e.status }}</span></span>
			</label>
			<template #rodape>
				<button class="btn-secundario" @click="escolher = null">Voltar</button>
				<button class="btn-primario" :disabled="!marcados.length" @click="adicionarMarcados">Adicionar {{ marcados.length || "" }}</button>
			</template>
		</Modal>

		<Modal v-if="confirmar" titulo="Confirmar emissão" largura="max-w-md" @fechar="confirmar = false">
			<p class="text-sm text-tinta">{{ conf.resumo }}</p>
			<p class="mt-2 text-sm text-suave">Total declarado: {{ moeda(conf.valores?.valor_total) }}</p>
			<template #rodape>
				<button class="btn-secundario" @click="confirmar = false">Voltar</button>
				<button class="btn-primario" :disabled="emitindo" @click="emitir"><Send class="size-4" /> {{ emitindo ? "Emitindo…" : "Confirmar e emitir" }}</button>
			</template>
		</Modal>

		<CadastroFiscal v-if="cadastro" :tipo-parte="f.tipo_parte" :parte="f.parte" @fechar="cadastro = false" @salvo="cadastro = false; conferir()" />
		<Resultado v-if="resultado" :resultado="resultado" @fechar="router.push('/remessas')" @abrir-nota="(id) => router.push(`/notas/${id}`)" />
	</div>
</template>
