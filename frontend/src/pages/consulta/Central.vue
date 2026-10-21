<script setup>
import {
	Building2,
	Check,
	CircleAlert,
	ClipboardList,
	ExternalLink,
	Gauge,
	KeyRound,
	Link2,
	MapPin,
	MessagesSquare,
	Plus,
	Search,
	ShieldCheck,
	UserPlus,
	UsersRound,
} from "lucide-vue-next"
import { computed, onMounted, reactive, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import { data, dataHora } from "@/format"
import { toast } from "@/store"

// Central do portal (só ER): triagem para amarrar cliente → contatos → portal → distritos →
// usuários → equipamentos → OS num lugar só. Toda lista já vem filtrada pelo cliente escolhido.
const route = useRoute()
const router = useRouter()
const chamar = (m, p = {}, o = {}) => api("central." + m, p, o)

const busca = ref("")
const resultados = ref([])
const cliente = ref(route.query.cliente || null)
const r = ref(null)
const etapa = ref(route.query.etapa || "portal")
const salvando = ref(false)

let timer
watch(busca, (t) => {
	clearTimeout(timer)
	timer = setTimeout(async () => (resultados.value = t.trim().length >= 2 ? await chamar("clientes", { busca: t.trim() }) : []), 250)
})

async function carregar() {
	if (!cliente.value) return
	r.value = await chamar("resumo", { cliente: cliente.value })
}
function escolher(c) {
	cliente.value = c.name
	busca.value = ""
	resultados.value = []
	r.value = null
	router.replace({ query: { cliente: c.name } })
	carregar()
}
onMounted(carregar)

async function executar(fn, msg) {
	salvando.value = true
	try {
		await fn()
		if (msg) toast(msg)
		await carregar()
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		salvando.value = false
	}
}

const ETAPAS = [
	{ id: "portal", rotulo: "Portal", icone: ShieldCheck, chave: "portal" },
	{ id: "contatos", rotulo: "Contatos", icone: Building2, chave: "contatos" },
	{ id: "distritos", rotulo: "Distritos", icone: MapPin, chave: "distritos" },
	{ id: "usuarios", rotulo: "Usuários", icone: UsersRound, chave: "usuarios" },
	{ id: "equipamentos", rotulo: "Equipamentos", icone: Gauge, chave: "equipamentos" },
	{ id: "os", rotulo: "OS e certificados", icone: ClipboardList, chave: "os" },
]
const prontas = computed(() => (r.value ? ETAPAS.filter((e) => !r.value.pendencias[e.chave]).length : 0))

// ------------------------------------------------------------ portal
const usaDistritos = ref(false)
watch(r, (v) => v && (usaDistritos.value = v.portal.usa_distritos))
const liberar = () => executar(() => chamar("liberar", { cliente: cliente.value, usa_distritos: usaDistritos.value ? 1 : 0 }, { post: true }), "Portal configurado.")

// ------------------------------------------------------------ distritos
const formDistrito = ref(null)
function editarDistrito(d) {
	formDistrito.value = d ? { ...d } : { nome: "", responsavel_nome: "", responsavel_email: "", uf: "", cidade: "", ativo: 1 }
}
function responsavelDoContato(nome) {
	const c = r.value.contatos.find((x) => x.nome === nome)
	if (c && !formDistrito.value.responsavel_email) formDistrito.value.responsavel_email = c.email_id
}
// Endereços do cliente que ainda não viraram distrito (sugestão de um clique).
const enderecosSemDistrito = computed(() => {
	const nomes = new Set((r.value?.distritos || []).map((d) => (d.nome || "").toLowerCase()))
	return (r.value?.enderecos || []).filter((e) => !nomes.has((e.address_title || e.city || "").toLowerCase()))
})
const distritosDosEnderecos = () =>
	executar(() => chamar("distritos_dos_enderecos", { cliente: cliente.value }, { post: true }), "Distritos criados a partir dos endereços.")
const salvarDistrito = () =>
	executar(async () => {
		await chamar("salvar_distrito", { cliente: cliente.value, ...formDistrito.value }, { post: true })
		formDistrito.value = null
	}, "Distrito salvo.")

// ------------------------------------------------------------ usuários
const formUsuario = ref(null)
const buscaEqp = ref("")
const buscaOpp = ref("")
const perfilDe = (email) => r.value?.usuarios.find((u) => u.usuario === email)
function editarUsuario(u, contato) {
	buscaEqp.value = ""
	buscaOpp.value = ""
	Object.assign(filtroOpp, { email: "", status: "", so_marcadas: false })
	formUsuario.value = reactive(
		u
			? {
					id: u.name, email: u.usuario, nome: u.nome_completo, perfil: u.perfil, ativo: !!u.ativo, senha: "",
					distritos: new Set(u.distritos), equipamentos: new Set(r.value.equipamentos.filter((e) => e.dono === u.usuario).map((e) => e.id)),
					ver_historico: !!u.ver_historico, oportunidades: new Set(u.oportunidades),
				}
			: {
					email: contato?.email_id || "", nome: contato?.nome || "",
					// o primeiro acesso do cliente é o Gestor
					perfil: r.value.usuarios.some((x) => x.perfil === "Gestor") ? "Líder" : "Gestor",
					ativo: true, senha: "", distritos: new Set(), equipamentos: new Set(),
					ver_historico: false, oportunidades: new Set(),
				},
	)
	etapa.value = "usuarios"
}
function escolherContato(email) {
	const c = r.value.contatos.find((x) => x.email_id === email)
	if (c && !formUsuario.value.nome) formUsuario.value.nome = c.nome
}
const eqpParaUsuario = computed(() => {
	const q = buscaEqp.value.trim().toLowerCase()
	return (r.value?.equipamentos || []).filter((e) => !q || [e.tag, e.descricao, e.numero_serie, e.distrito_nome].some((v) => String(v || "").toLowerCase().includes(q)))
})
// Oportunidades (já só as do cliente): filtros de e-mail do contato, status e texto, como na lista do ERP.
const STATUS_OPP = { Open: "Aberto", Quotation: "Orçamento", Converted: "Convertido", Lost: "Perdido", Replied: "Respondido", Closed: "Fechado" }
const filtroOpp = reactive({ email: "", status: "", so_marcadas: false })
const emailsOpp = computed(() => {
	const cont = new Map()
	for (const o of r.value?.oportunidades || []) if (o.contact_email) cont.set(o.contact_email, (cont.get(o.contact_email) || 0) + 1)
	return [...cont.entries()].sort((a, b) => a[0].localeCompare(b[0]))
})
const statusOpp = computed(() => [...new Set((r.value?.oportunidades || []).map((o) => o.status).filter(Boolean))])
const emailDoAcessoNasOpps = computed(() => {
	const e = (formUsuario.value?.email || "").trim().toLowerCase()
	return e && emailsOpp.value.some(([x]) => x === e) ? e : null
})
const oppParaUsuario = computed(() => {
	const q = buscaOpp.value.trim().toLowerCase()
	return (r.value?.oportunidades || []).filter(
		(o) =>
			(!filtroOpp.email || o.contact_email === filtroOpp.email) &&
			(!filtroOpp.status || o.status === filtroOpp.status) &&
			(!filtroOpp.so_marcadas || formUsuario.value.oportunidades.has(o.id)) &&
			(!q || [o.id, o.title, o.contato, o.contact_email, o.responsavel].some((v) => String(v || "").toLowerCase().includes(q))),
	)
})
function marcarFiltradas(marcar) {
	for (const o of oppParaUsuario.value) marcar ? formUsuario.value.oportunidades.add(o.id) : formUsuario.value.oportunidades.delete(o.id)
}
function alternar(set, id) {
	set.has(id) ? set.delete(id) : set.add(id)
}
const salvarUsuario = () =>
	executar(async () => {
		const f = formUsuario.value
		if (f.perfil === "Líder" && r.value.portal.usa_distritos && !f.distritos.size) throw new Error("Escolha ao menos um distrito para o Líder.")
		if (f.perfil === "Usuário" && !f.equipamentos.size) throw new Error("Escolha os equipamentos sob a responsabilidade do Usuário.")
		const historico = f.perfil !== "Usuário" && f.ver_historico
		if (historico && !f.oportunidades.size) throw new Error("Escolha as oportunidades do histórico de atendimento.")
		const res = await chamar(
			"salvar_usuario",
			{ cliente: cliente.value, id: f.id, email: f.email, nome: f.nome, perfil: f.perfil, ativo: f.ativo ? 1 : 0, senha: f.senha || undefined, distritos: [...f.distritos], equipamentos: [...f.equipamentos],
				ver_historico: historico ? 1 : 0, oportunidades: historico ? [...f.oportunidades] : [] },
			{ post: true },
		)
		toast(res.convidado ? `Convite enviado para ${f.email}.` : "Acesso salvo.")
		formUsuario.value = null
	})

// ------------------------------------------------------------ equipamentos
const filtroEqp = ref("todos")
const selecionados = ref(new Set())
const destinoDistrito = ref("")
const destinoDono = ref("")
const donosPossiveis = computed(() => (r.value?.usuarios || []).filter((u) => u.perfil === "Usuário" && u.ativo))
const eqpFiltrados = computed(() =>
	(r.value?.equipamentos || []).filter((e) => (filtroEqp.value === "sem_distrito" ? !e.distrito : filtroEqp.value === "sem_dono" ? !e.dono : true)),
)
function alternarTodos() {
	const ids = eqpFiltrados.value.map((e) => e.id)
	selecionados.value = ids.every((i) => selecionados.value.has(i)) ? new Set() : new Set(ids)
}
const aplicarDistrito = (ids, distrito) =>
	executar(() => chamar("definir_distrito", { cliente: cliente.value, equipamentos: ids, distrito: distrito || undefined }, { post: true }), "Distrito atualizado.")
const aplicarDono = (ids, usuario) =>
	executar(() => chamar("definir_dono", { cliente: cliente.value, equipamentos: ids, usuario: usuario || undefined }, { post: true }), "Dono atualizado.")

// ------------------------------------------------------------ OS
const vincular = (o, equipamento) =>
	executar(() => chamar("vincular_os", { doctype: o.doctype, os: o.os, equipamento }, { post: true }), `${o.os} ligada ao equipamento.`)
const seletores = {} // <select> de cada OS sem vínculo (fora da reatividade)
const rotaOs = (o) => `/app/${o.doctype === "Ordem Servico Interna" ? "ordem-servico-interna" : "ordem-servico-externa"}/${o.os}`
</script>

<template>
	<div class="space-y-6">
		<div class="flex flex-wrap items-end justify-between gap-4">
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-slate-900">Central do portal</h1>
				<p class="mt-1 text-sm text-slate-500">Triagem da ER: escolha o cliente e amarre tudo numa tela — cada lista já vem filtrada por ele.
					<RouterLink :to="{ path: '/manual', query: { parte: 'er' } }" class="font-medium text-brand-700 hover:underline">Ver o manual</RouterLink></p>
			</div>
			<div class="relative w-full max-w-md">
				<Search class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" />
				<input v-model="busca" class="input pl-9" placeholder="Buscar cliente por nome ou código…" />
				<ul v-if="resultados.length" class="absolute z-30 mt-1 max-h-80 w-full overflow-y-auto rounded-xl border border-slate-200 bg-white p-1 shadow-pop">
					<li v-for="c in resultados" :key="c.name">
						<button class="flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-50" @click="escolher(c)">
							<span><b class="font-medium text-slate-900">{{ c.customer_name }}</b> <span class="text-xs text-slate-400">{{ c.name }}</span></span>
							<span v-if="c.portal" class="rounded-md bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700">PORTAL</span>
						</button>
					</li>
				</ul>
			</div>
		</div>

		<div v-if="!cliente" class="card p-10 text-center text-slate-500">
			<Building2 class="mx-auto mb-3 size-10 text-slate-300" />
			Busque um cliente para começar.
		</div>
		<div v-else-if="!r" class="card p-6"><Esqueleto :linhas="8" /></div>

		<template v-else>
			<!-- Cabeçalho do cliente + etapas -->
			<section class="card overflow-hidden">
				<div class="flex flex-wrap items-center justify-between gap-4 bg-gradient-to-r from-brand-800 to-brand-600 px-6 py-5 text-white">
					<div>
						<p class="text-xs text-white/70">{{ r.cliente.id }}</p>
						<h2 class="text-xl font-semibold">{{ r.cliente.nome }}</h2>
					</div>
					<div class="text-right">
						<p class="text-3xl font-semibold tabular-nums">{{ prontas }}/{{ ETAPAS.length }}</p>
						<p class="text-xs text-white/70">etapas sem pendência</p>
					</div>
				</div>
				<nav class="grid grid-cols-3 gap-px bg-slate-100 sm:grid-cols-6">
					<button
						v-for="(e, i) in ETAPAS"
						:key="e.id"
						class="flex items-center gap-2 bg-white px-4 py-3 text-left text-sm transition"
						:class="etapa === e.id ? 'text-brand-700 shadow-[inset_0_-2px_0_var(--color-brand-600)]' : 'text-slate-600 hover:bg-slate-50'"
						@click="etapa = e.id"
					>
						<span class="grid size-6 shrink-0 place-items-center rounded-full text-xs font-semibold" :class="r.pendencias[e.chave] ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'">
							<Check v-if="!r.pendencias[e.chave]" class="size-3.5" /><template v-else>{{ i + 1 }}</template>
						</span>
						<span class="min-w-0 truncate font-medium">{{ e.rotulo }}</span>
						<span v-if="r.pendencias[e.chave]" class="ml-auto rounded-full bg-amber-50 px-1.5 text-[11px] font-semibold text-amber-700">{{ r.pendencias[e.chave] }}</span>
					</button>
				</nav>
			</section>

			<!-- 1. Portal -->
			<section v-if="etapa === 'portal'" class="card space-y-5 p-6">
				<div class="flex items-start gap-4">
					<span class="grid size-11 place-items-center rounded-xl" :class="r.portal.liberado ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'"><ShieldCheck class="size-5" /></span>
					<div>
						<h3 class="font-semibold text-slate-900">{{ r.portal.liberado ? "Portal liberado para este cliente" : "Portal ainda não liberado" }}</h3>
						<p class="text-sm text-slate-500">Libere o portal e decida se o parque será organizado por distritos (filiais, unidades, setores).</p>
					</div>
				</div>
				<label class="flex max-w-xl cursor-pointer items-start gap-3 rounded-2xl border p-4" :class="usaDistritos ? 'border-brand-300 bg-brand-50/50' : 'border-slate-200'">
					<input v-model="usaDistritos" type="checkbox" class="mt-1 accent-brand-600" />
					<span>
						<span class="block text-sm font-medium text-slate-900">Controle por distritos</span>
						<span class="text-xs text-slate-500">Líderes veem só os distritos atribuídos; o Gestor vê tudo. Sem isso, todos os usuários do cliente veem o parque inteiro.</span>
					</span>
				</label>
				<div class="flex flex-wrap gap-2">
					<button class="btn-primary" :disabled="salvando" @click="liberar">{{ r.portal.liberado ? "Salvar" : "Liberar portal" }}</button>
					<a :href="`/app/customer/${r.cliente.id}`" target="_blank" class="btn-secondary"><ExternalLink class="size-4" /> Cadastro do cliente no ERP</a>
				</div>
			</section>

			<!-- 2. Contatos -->
			<section v-else-if="etapa === 'contatos'" class="card overflow-hidden">
				<div class="flex flex-wrap items-center justify-between gap-3 p-5">
					<div>
						<h3 class="font-semibold text-slate-900">Contatos do cliente</h3>
						<p class="text-sm text-slate-500">A OS exige um contato. Daqui você já dá acesso ao portal a partir do contato.</p>
					</div>
					<a href="/app/contact/new" target="_blank" class="btn-secondary"><Plus class="size-4" /> Novo contato no ERP</a>
				</div>
				<table class="w-full text-sm">
					<thead class="bg-slate-50 text-left text-[11px] tracking-wider text-slate-500 uppercase">
						<tr><th class="px-5 py-2.5">Contato</th><th class="px-5 py-2.5">E-mail</th><th class="px-5 py-2.5">Telefone</th><th class="px-5 py-2.5">Portal</th><th /></tr>
					</thead>
					<tbody class="divide-y divide-slate-100">
						<tr v-if="!r.contatos.length"><td colspan="5" class="px-5 py-8 text-center text-slate-500">Nenhum contato ligado a este cliente.</td></tr>
						<tr v-for="c in r.contatos" :key="c.name">
							<td class="px-5 py-3 font-medium text-slate-900">{{ c.nome }}</td>
							<td class="px-5 py-3 text-slate-600">{{ c.email_id || "—" }}</td>
							<td class="px-5 py-3 text-slate-600">{{ c.mobile_no || c.phone || "—" }}</td>
							<td class="px-5 py-3"><Etiqueta v-if="perfilDe(c.email_id)" :valor="perfilDe(c.email_id).perfil" :ponto="false" /><span v-else class="text-xs text-slate-400">sem acesso</span></td>
							<td class="px-5 py-3 text-right">
								<button v-if="c.email_id && !perfilDe(c.email_id)" class="btn-ghost px-2.5 py-1 text-xs" @click="editarUsuario(null, c)"><UserPlus class="size-3.5" /> Dar acesso</button>
							</td>
						</tr>
					</tbody>
				</table>
			</section>

			<!-- 3. Distritos -->
			<section v-else-if="etapa === 'distritos'" class="space-y-4">
				<div v-if="!r.portal.usa_distritos" class="card flex items-center gap-3 p-5 text-sm text-slate-600">
					<CircleAlert class="size-5 text-amber-500" /> Este cliente não usa controle por distritos (etapa Portal). Distritos são opcionais.
				</div>
				<div v-if="enderecosSemDistrito.length" class="card flex flex-wrap items-center gap-4 border-brand-200 bg-brand-50/50 p-5">
					<MapPin class="size-5 text-brand-600" />
					<div class="min-w-0 flex-1">
						<p class="font-medium text-slate-900">{{ enderecosSemDistrito.length }} endereço(s) do cliente ainda não viraram distrito</p>
						<p class="text-sm text-slate-600">{{ enderecosSemDistrito.map((e) => `${e.address_title} (${[e.city, e.state].filter(Boolean).join("/")})`).join(" · ") }}</p>
					</div>
					<button class="btn-primary" :disabled="salvando" @click="distritosDosEnderecos">Criar distritos pelos endereços</button>
				</div>
				<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
					<article v-for="d in r.distritos" :key="d.id" class="card p-5" :class="!d.ativo && 'opacity-60'">
						<div class="flex items-start justify-between gap-2">
							<p class="font-semibold text-slate-900">{{ d.nome }}</p>
							<button class="btn-ghost -mt-1 -mr-2 px-2 py-1 text-xs" @click="editarDistrito(d)">Editar</button>
						</div>
						<p class="mt-1 text-sm" :class="d.responsavel_nome ? 'text-slate-600' : 'text-amber-600'">{{ d.responsavel_nome || "Sem responsável" }}</p>
						<p class="text-xs text-slate-500">{{ [d.cidade, d.uf].filter(Boolean).join("/") || "Sem cidade/UF" }}</p>
						<p class="mt-3 text-xs text-slate-500">{{ r.equipamentos.filter((e) => e.distrito === d.id).length }} equipamento(s) · {{ r.usuarios.filter((u) => u.distritos.includes(d.id)).length }} líder(es)</p>
					</article>
					<button class="card flex min-h-[140px] flex-col items-center justify-center gap-2 border-dashed text-slate-500 hover:border-brand-300 hover:text-brand-700" @click="editarDistrito(null)">
						<Plus class="size-6" /> <span class="text-sm font-medium">Novo distrito</span>
					</button>
				</div>
				<form v-if="formDistrito" class="card grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-5" @submit.prevent="salvarDistrito">
					<div class="lg:col-span-1"><label class="label">Distrito *</label><input v-model="formDistrito.nome" class="input" required /></div>
					<div class="lg:col-span-1">
						<label class="label">Responsável (contato)</label>
						<input v-model="formDistrito.responsavel_nome" class="input" list="contatos-cliente" @change="responsavelDoContato(formDistrito.responsavel_nome)" />
						<datalist id="contatos-cliente"><option v-for="c in r.contatos" :key="c.name" :value="c.nome" /></datalist>
					</div>
					<div class="lg:col-span-1"><label class="label">E-mail do responsável</label><input v-model="formDistrito.responsavel_email" type="email" class="input" /></div>
					<div><label class="label">Cidade</label><input v-model="formDistrito.cidade" class="input" /></div>
					<div><label class="label">UF</label><input v-model="formDistrito.uf" maxlength="2" class="input uppercase" /></div>
					<div class="flex gap-2 sm:col-span-2 lg:col-span-5">
						<button class="btn-primary" type="submit" :disabled="salvando">Salvar distrito</button>
						<button class="btn-secondary" type="button" @click="formDistrito = null">Cancelar</button>
					</div>
				</form>
			</section>

			<!-- 4. Usuários -->
			<section v-else-if="etapa === 'usuarios'" class="grid gap-5 xl:grid-cols-[1fr_1.1fr]">
				<div class="card overflow-hidden">
					<div class="flex items-center justify-between gap-3 p-5">
						<h3 class="font-semibold text-slate-900">Quem acessa o portal</h3>
						<button class="btn-primary" @click="editarUsuario(null)"><UserPlus class="size-4" /> Novo acesso</button>
					</div>
					<ul class="divide-y divide-slate-100">
						<li v-if="!r.usuarios.length" class="px-5 py-8 text-center text-sm text-slate-500">Nenhum acesso. Comece pelo Gestor do cliente.</li>
						<li v-for="u in r.usuarios" :key="u.name" class="flex cursor-pointer items-center gap-3 px-5 py-3 hover:bg-slate-50" :class="!u.ativo && 'opacity-50'" @click="editarUsuario(u)">
							<div class="min-w-0 flex-1">
								<p class="truncate font-medium text-slate-900">{{ u.nome_completo || u.usuario }}</p>
								<p class="truncate text-xs text-slate-500">
									{{ u.usuario }} ·
									<template v-if="u.perfil === 'Gestor'">todo o parque</template>
									<template v-else-if="u.perfil === 'Líder'">{{ u.distritos.map((d) => r.distritos.find((x) => x.id === d)?.nome || d).join(", ") || "sem distrito" }}</template>
									<template v-else>{{ r.equipamentos.filter((e) => e.dono === u.usuario).length }} equipamento(s)</template>
									<template v-if="u.ver_historico"> · histórico de {{ u.oportunidades.length }} oportunidade(s)</template>
								</p>
							</div>
							<Etiqueta :valor="u.perfil" :ponto="false" />
							<span class="hidden text-xs text-slate-400 sm:block">{{ u.ultimo_acesso ? dataHora(u.ultimo_acesso) : "nunca entrou" }}</span>
						</li>
					</ul>
				</div>

				<form v-if="formUsuario" class="card space-y-4 p-5" @submit.prevent="salvarUsuario">
					<h3 class="font-semibold text-slate-900">{{ formUsuario.id ? "Editar acesso" : "Novo acesso" }}</h3>
					<div class="grid gap-3 sm:grid-cols-2">
						<div>
							<label class="label">E-mail * <span class="font-normal text-slate-400">(sugere os contatos)</span></label>
							<input v-model="formUsuario.email" type="email" class="input" list="emails-contatos" required :disabled="!!formUsuario.id" @change="escolherContato(formUsuario.email)" />
							<datalist id="emails-contatos"><option v-for="c in r.contatos.filter((c) => c.email_id)" :key="c.name" :value="c.email_id">{{ c.nome }}</option></datalist>
						</div>
						<div><label class="label">Nome</label><input v-model="formUsuario.nome" class="input" :disabled="!!formUsuario.id" /></div>
					</div>
					<div>
						<label class="label">Perfil</label>
						<div class="grid gap-2 sm:grid-cols-3">
							<label
								v-for="p in [
									['Gestor', 'Todo o parque; distritos, equipe e logs'],
									['Líder', 'Só os distritos atribuídos'],
									['Usuário', 'Só os equipamentos dele, leitura'],
								]"
								:key="p[0]"
								class="cursor-pointer rounded-xl border p-3 text-sm"
								:class="formUsuario.perfil === p[0] ? 'border-brand-400 bg-brand-50/60 ring-4 ring-brand-100' : 'border-slate-200 hover:bg-slate-50'"
							>
								<input v-model="formUsuario.perfil" type="radio" :value="p[0]" class="sr-only" />
								<span class="block font-medium text-slate-900">{{ p[0] }}</span>
								<span class="text-xs text-slate-500">{{ p[1] }}</span>
							</label>
						</div>
					</div>
					<div v-if="formUsuario.perfil === 'Líder'">
						<label class="label">Distritos do Líder</label>
						<p v-if="!r.distritos.length" class="text-sm text-amber-600">Cadastre os distritos primeiro (etapa Distritos).</p>
						<div class="flex flex-wrap gap-2">
							<button
								v-for="d in r.distritos"
								:key="d.id"
								type="button"
								class="chip"
								:class="formUsuario.distritos.has(d.id) ? 'border-brand-500 bg-brand-600 text-white' : 'border-slate-200 bg-white text-slate-600'"
								@click="alternar(formUsuario.distritos, d.id)"
							>
								<MapPin class="size-3.5" /> {{ d.nome }}
							</button>
						</div>
					</div>
					<div v-if="formUsuario.perfil === 'Usuário'">
						<label class="label">Equipamentos sob responsabilidade ({{ formUsuario.equipamentos.size }})</label>
						<input v-model="buscaEqp" class="input mb-2" placeholder="Filtrar por TAG, equipamento, série ou distrito…" />
						<div class="max-h-56 divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-200">
							<label v-for="e in eqpParaUsuario" :key="e.id" class="flex cursor-pointer items-center gap-3 px-3 py-2 text-sm hover:bg-slate-50">
								<input type="checkbox" class="accent-brand-600" :checked="formUsuario.equipamentos.has(e.id)" @change="alternar(formUsuario.equipamentos, e.id)" />
								<span class="min-w-0 flex-1 truncate"><b class="font-medium">{{ e.tag }}</b> · {{ e.descricao }}</span>
								<span class="text-xs text-slate-400">{{ e.distrito_nome || "sem distrito" }}</span>
							</label>
						</div>
					</div>
					<div v-if="formUsuario.perfil !== 'Usuário'" class="rounded-xl border border-slate-200 p-3">
						<label class="flex cursor-pointer items-start gap-2 text-sm text-slate-700">
							<input v-model="formUsuario.ver_historico" type="checkbox" class="mt-0.5 accent-brand-600" />
							<span>
								<span class="flex items-center gap-1.5 font-medium text-slate-900"><MessagesSquare class="size-4 text-brand-600" /> Habilitar histórico de atendimento</span>
								<span class="text-xs text-slate-500">Mostra no portal as notas (aba Comentários) das oportunidades escolhidas — as já escritas e as que forem escritas depois.</span>
							</span>
						</label>
						<div v-if="formUsuario.ver_historico" class="mt-3">
							<p v-if="!r.oportunidades.length" class="text-sm text-amber-600">Este cliente não tem oportunidades no ERP (oportunidades de Lead não entram).</p>
							<template v-else>
								<label class="label">
									Oportunidades do cliente — {{ formUsuario.oportunidades.size }} liberada(s) de {{ r.oportunidades.length }}
								</label>
								<div class="mb-2 grid gap-2 sm:grid-cols-[1.3fr_1fr]">
									<select v-model="filtroOpp.email" class="input">
										<option value="">Todos os e-mails de contato</option>
										<option v-for="[e, n] in emailsOpp" :key="e" :value="e">{{ e }} ({{ n }})</option>
									</select>
									<select v-model="filtroOpp.status" class="input">
										<option value="">Todos os status</option>
										<option v-for="s in statusOpp" :key="s" :value="s">{{ STATUS_OPP[s] || s }}</option>
									</select>
								</div>
								<input v-model="buscaOpp" class="input mb-2" placeholder="Buscar por código, título, contato, e-mail ou responsável…" />
								<div class="mb-2 flex flex-wrap items-center gap-2 text-xs">
									<button
										v-if="emailDoAcessoNasOpps"
										type="button"
										class="chip"
										:class="filtroOpp.email === emailDoAcessoNasOpps ? 'border-brand-500 bg-brand-600 text-white' : 'border-slate-200 bg-white text-slate-600'"
										@click="filtroOpp.email = filtroOpp.email === emailDoAcessoNasOpps ? '' : emailDoAcessoNasOpps"
									>
										Só do e-mail deste acesso
									</button>
									<button
										type="button"
										class="chip"
										:class="filtroOpp.so_marcadas ? 'border-brand-500 bg-brand-600 text-white' : 'border-slate-200 bg-white text-slate-600'"
										@click="filtroOpp.so_marcadas = !filtroOpp.so_marcadas"
									>
										Só as liberadas
									</button>
									<span class="ml-auto text-slate-500">{{ oppParaUsuario.length }} na lista ·</span>
									<button type="button" class="font-medium text-brand-700 hover:underline" @click="marcarFiltradas(true)">marcar todas</button>
									<button type="button" class="font-medium text-slate-500 hover:underline" @click="marcarFiltradas(false)">desmarcar</button>
								</div>
								<div class="max-h-72 divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-200">
									<p v-if="!oppParaUsuario.length" class="px-3 py-4 text-center text-sm text-slate-500">Nenhuma oportunidade com esses filtros.</p>
									<label v-for="o in oppParaUsuario" :key="o.id" class="flex cursor-pointer items-start gap-3 px-3 py-2 text-sm hover:bg-slate-50">
										<input type="checkbox" class="mt-1 accent-brand-600" :checked="formUsuario.oportunidades.has(o.id)" @change="alternar(formUsuario.oportunidades, o.id)" />
										<span class="min-w-0 flex-1">
											<span class="flex items-center gap-1.5">
												<span class="truncate" :title="o.title"><b class="font-medium">{{ o.id }}</b> · {{ o.title }}</span>
												<a :href="`/app/opportunity/${o.id}`" target="_blank" class="shrink-0 text-slate-400 hover:text-brand-700" title="Abrir no ERP" @click.stop><ExternalLink class="size-3.5" /></a>
											</span>
											<span class="block truncate text-xs text-slate-500">
												{{ o.contato || "sem contato" }}<template v-if="o.contact_email"> · {{ o.contact_email }}</template>
												<template v-if="o.responsavel"> · resp. {{ o.responsavel }}</template>
											</span>
										</span>
										<span class="shrink-0 text-right text-xs text-slate-400">
											<span class="block">{{ STATUS_OPP[o.status] || o.status }} · {{ data(o.transaction_date || o.creation) }}</span>
											<span class="block">{{ o.notas }} nota(s)</span>
										</span>
									</label>
								</div>
								<p class="mt-2 text-xs text-amber-700">Tudo o que for anotado nessas oportunidades fica visível para este acesso.</p>
							</template>
						</div>
					</div>
					<div class="grid gap-3 sm:grid-cols-2">
						<div>
							<label class="label"><KeyRound class="inline size-3.5" /> Senha inicial (opcional)</label>
							<input v-model="formUsuario.senha" type="text" class="input" placeholder="Vazio = envia convite por e-mail" autocomplete="off" />
						</div>
						<label v-if="formUsuario.id" class="flex items-end gap-2 pb-2 text-sm text-slate-700"><input v-model="formUsuario.ativo" type="checkbox" class="accent-brand-600" /> Acesso ativo</label>
					</div>
					<div class="flex gap-2">
						<button class="btn-primary" type="submit" :disabled="salvando">Salvar acesso</button>
						<button class="btn-secondary" type="button" @click="formUsuario = null">Cancelar</button>
					</div>
				</form>
				<div v-else class="card grid place-items-center p-8 text-center text-sm text-slate-500">
					Escolha um acesso na lista, clique em “Novo acesso” ou use “Dar acesso” na etapa Contatos.
				</div>
			</section>

			<!-- 5. Equipamentos -->
			<section v-else-if="etapa === 'equipamentos'" class="card overflow-hidden">
				<div class="flex flex-wrap items-center justify-between gap-3 p-5">
					<div class="flex flex-wrap gap-2">
						<button
							v-for="f in [
								['todos', `Todos ${r.equipamentos.length}`],
								['sem_distrito', `Sem distrito ${r.equipamentos.filter((e) => !e.distrito).length}`],
								['sem_dono', `Sem dono ${r.equipamentos.filter((e) => !e.dono).length}`],
							]"
							:key="f[0]"
							class="chip"
							:class="filtroEqp === f[0] ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-600'"
							@click="filtroEqp = f[0]"
						>
							{{ f[1] }}
						</button>
					</div>
					<a :href="`/app/equipamentos/new?customer=${encodeURIComponent(r.cliente.id)}`" target="_blank" class="btn-secondary"><Plus class="size-4" /> Cadastrar equipamento no ERP</a>
				</div>
				<div v-if="selecionados.size" class="flex flex-wrap items-center gap-3 border-y border-brand-100 bg-brand-50/60 px-5 py-3 text-sm">
					<b class="text-brand-800">{{ selecionados.size }} selecionado(s)</b>
					<select v-model="destinoDistrito" class="input h-9 w-48 py-0">
						<option value="">— sem distrito —</option>
						<option v-for="d in r.distritos" :key="d.id" :value="d.id">{{ d.nome }}</option>
					</select>
					<button class="btn-primary h-9 py-0" :disabled="salvando" @click="aplicarDistrito([...selecionados], destinoDistrito)">Mover para o distrito</button>
					<select v-model="destinoDono" class="input h-9 w-48 py-0">
						<option value="">— sem dono —</option>
						<option v-for="u in donosPossiveis" :key="u.usuario" :value="u.usuario">{{ u.nome_completo || u.usuario }}</option>
					</select>
					<button class="btn-secondary h-9 py-0" :disabled="salvando" @click="aplicarDono([...selecionados], destinoDono)">Definir dono</button>
				</div>
				<div class="overflow-x-auto">
					<table class="w-full min-w-[900px] text-sm">
						<thead class="bg-slate-50 text-left text-[11px] tracking-wider text-slate-500 uppercase">
							<tr>
								<th class="w-10 px-5 py-2.5"><input type="checkbox" class="accent-brand-600" @change="alternarTodos" /></th>
								<th class="px-3 py-2.5">Equipamento</th><th class="px-3 py-2.5">Situação</th><th class="px-3 py-2.5">OS</th><th class="px-3 py-2.5">Distrito</th><th class="px-3 py-2.5">Dono (Usuário)</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-slate-100">
							<tr v-if="!eqpFiltrados.length"><td colspan="6" class="px-5 py-8 text-center text-slate-500">Nenhum equipamento neste filtro.</td></tr>
							<tr v-for="e in eqpFiltrados" :key="e.id" :class="selecionados.has(e.id) && 'bg-brand-50/40'">
								<td class="px-5 py-2.5"><input type="checkbox" class="accent-brand-600" :checked="selecionados.has(e.id)" @change="alternar(selecionados, e.id)" /></td>
								<td class="px-3 py-2.5">
									<p class="font-medium text-slate-900">{{ e.tag }} · {{ e.descricao }}</p>
									<p class="text-xs text-slate-500">série {{ e.numero_serie || "—" }} · {{ e.vendor }}</p>
								</td>
								<td class="px-3 py-2.5"><Etiqueta :valor="e.status_calibracao" /></td>
								<td class="px-3 py-2.5 text-slate-600 tabular-nums">{{ e.origem === "laboratorio" ? e.qtd_os : "—" }}</td>
								<td class="px-3 py-2.5">
									<select class="input h-9 py-0" :value="e.distrito || ''" @change="aplicarDistrito([e.id], $event.target.value)">
										<option value="">— sem distrito —</option>
										<option v-for="d in r.distritos" :key="d.id" :value="d.id">{{ d.nome }}</option>
									</select>
								</td>
								<td class="px-3 py-2.5">
									<select class="input h-9 py-0" :value="e.dono || ''" @change="aplicarDono([e.id], $event.target.value)">
										<option value="">— sem dono —</option>
										<option v-for="u in donosPossiveis" :key="u.usuario" :value="u.usuario">{{ u.nome_completo || u.usuario }}</option>
									</select>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>

			<!-- 6. OS e certificados -->
			<section v-else-if="etapa === 'os'" class="space-y-5">
				<div class="card overflow-hidden">
					<div class="p-5">
						<h3 class="flex items-center gap-2 font-semibold text-slate-900"><Link2 class="size-4 text-brand-600" /> OS sem equipamento ligado</h3>
						<p class="text-sm text-slate-500">Sem o campo “Digite o número de série do equipamento”, a OS não entra no histórico nem na situação do portal. A sugestão é feita pela série ou TAG.</p>
					</div>
					<table class="w-full text-sm">
						<thead class="bg-slate-50 text-left text-[11px] tracking-wider text-slate-500 uppercase">
							<tr><th class="px-5 py-2.5">OS</th><th class="px-5 py-2.5">Na OS</th><th class="px-5 py-2.5">Ligar ao equipamento</th></tr>
						</thead>
						<tbody class="divide-y divide-slate-100">
							<tr v-if="!r.os_sem_vinculo.length"><td colspan="3" class="px-5 py-8 text-center text-emerald-700">Todas as OS deste cliente estão ligadas a um equipamento.</td></tr>
							<tr v-for="o in r.os_sem_vinculo" :key="o.os">
								<td class="px-5 py-3">
									<a :href="rotaOs(o)" target="_blank" class="font-medium text-brand-700 hover:underline">{{ o.os }}</a>
									<p class="text-xs text-slate-500">{{ o.tipo }} · {{ o.status || "—" }}</p>
								</td>
								<td class="px-5 py-3 text-slate-600">{{ o.descricao || "—" }}<p class="text-xs text-slate-400">série {{ o.serie || "—" }} · TAG {{ o.tag || "—" }}</p></td>
								<td class="px-5 py-3">
									<div class="flex flex-wrap items-center gap-2">
										<select :ref="(el) => (seletores[o.os] = el)" class="input h-9 w-64 py-0" :value="o.sugestao?.id || ''">
											<option value="">Escolha o equipamento…</option>
											<option v-for="e in r.equipamentos.filter((x) => x.origem === 'laboratorio')" :key="e.id" :value="e.id">{{ e.tag }} · {{ e.descricao }} · {{ e.numero_serie }}</option>
										</select>
										<button class="btn-primary h-9 py-0" :disabled="salvando" @click="seletores[o.os]?.value && vincular(o, seletores[o.os].value)">Ligar</button>
										<span v-if="o.sugestao" class="text-xs text-emerald-700">sugerido pela {{ o.serie ? "série" : "TAG" }}</span>
									</div>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
				<div class="card overflow-hidden">
					<div class="p-5">
						<h3 class="font-semibold text-slate-900">OS encerradas sem certificado anexado</h3>
						<p class="text-sm text-slate-500">O equipamento fica sem calibração registrada no portal até o PDF ser anexado na OS.</p>
					</div>
					<ul class="divide-y divide-slate-100 text-sm">
						<li v-if="!r.os_sem_certificado.length" class="px-5 py-6 text-center text-emerald-700">Nenhuma pendência.</li>
						<li v-for="o in r.os_sem_certificado" :key="o.os" class="flex items-center justify-between px-5 py-3">
							<span><a :href="rotaOs(o)" target="_blank" class="font-medium text-brand-700 hover:underline">{{ o.os }}</a> · {{ o.tag || o.equipamento }}</span>
							<a :href="rotaOs(o)" target="_blank" class="btn-ghost px-2.5 py-1 text-xs"><ExternalLink class="size-3.5" /> Abrir OS</a>
						</li>
					</ul>
				</div>
			</section>
		</template>
	</div>
</template>
