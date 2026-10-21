<script setup>
import {
	BookOpen,
	Building2,
	ChevronDown,
	CircleAlert,
	CircleCheck,
	ClipboardList,
	FileCheck2,
	FileSpreadsheet,
	Workflow,
	ScrollText,
	Gauge,
	LayoutDashboard,
	Eye,
	LogOut,
	MapPin,
	MessagesSquare,
	Menu,
	MonitorCog,
	Plus,
	UsersRound,
	X,
} from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { api } from "./api"
import { BASE, CONSULTA } from "./modo"
import { clienteAtual, definirCliente, definirDistrito, podeEditar, store } from "./store"

// Servido pelo Frappe (apps/solucoes/solucoes/public/img), fora do build do Vite.
const LOGO = "/assets/solucoes/img/er-analitica.png"
const route = useRoute()
const router = useRouter()
const erro = ref(null)
const menuAberto = ref(false)
const menuUsuario = ref(false)

const NAV = [
	{ nome: "painel", rotulo: "Painel", icone: LayoutDashboard, rota: "/" },
	{ nome: "equipamentos", rotulo: "Equipamentos", icone: Gauge, rota: "/equipamentos" },
	{ nome: "certificados", rotulo: "Certificados", icone: FileCheck2, rota: "/certificados" },
	{ nome: "ordens", rotulo: "Ordens de Serviço", icone: ClipboardList, rota: "/ordens" },
]

// /consulta: menu da gestão do parque (Relatórios para todos; Logs só gestor/interno).
const NAV_CONSULTA = [
	{ nome: "painel", rotulo: "Visão operacional", icone: LayoutDashboard, rota: "/" },
	{ nome: "equipamentos", rotulo: "Equipamentos", icone: Gauge, rota: "/equipamentos" },
	{ nome: "certificados", rotulo: "Certificados", icone: FileCheck2, rota: "/certificados" },
	{ nome: "ordens", rotulo: "Ordens de Serviço", icone: ClipboardList, rota: "/ordens" },
	{ nome: "relatorios", rotulo: "Relatórios", icone: FileSpreadsheet, rota: "/relatorios" },
]

// Perfil Usuário (em todos os clientes): só Equipamentos, Certificados e Ordens.
const soUsuario = computed(() => !!store.contexto?.clientes.length && store.contexto.clientes.every((c) => c.perfil === "Usuário"))
// Usuário entra direto em Equipamentos (sem visão operacional nem relatórios).
watch(
	() => [soUsuario.value, route.path],
	([so, caminho]) => {
		if (CONSULTA && so && ["/", "/relatorios", "/logs"].includes(caminho)) router.replace("/equipamentos")
	},
	{ immediate: true },
)

const nav = computed(() => {
	const base = CONSULTA ? NAV_CONSULTA.filter((i) => !soUsuario.value || !["painel", "relatorios"].includes(i.nome)) : [...NAV]
	// Histórico de atendimento: só Gestor/Líder com oportunidades liberadas pela ER
	if (CONSULTA && store.contexto?.clientes.some((c) => c.ver_historico))
		base.push({ nome: "historico", rotulo: "Histórico de atendimento", icone: MessagesSquare, rota: "/historico" })
	if (CONSULTA && store.contexto?.pode_ver_logs) base.push({ nome: "logs", rotulo: "Logs de auditoria", icone: ScrollText, rota: "/logs" })
	if (store.contexto?.clientes.some((c) => c.pode_gerenciar)) base.push({ nome: "gestao", rotulo: "Distritos e equipe", icone: UsersRound, rota: "/gestao" })
	// Triagem da ER (só usuários internos)
	if (CONSULTA && store.contexto?.usuario.interno) base.push({ nome: "central", rotulo: "Central do portal", icone: Workflow, rota: "/central" })
	// Manual (parte do cliente para todos; parte da ER só para internos)
	if (CONSULTA) base.push({ nome: "manual", rotulo: "Manual", icone: BookOpen, rota: "/manual" })
	return base
})

// Seletor de distrito: só para cliente com controle por distritos e mais de um distrito visível
const distritosDoCliente = computed(() => clienteAtual()?.distritos || [])
// Com filtro de distrito ativo o seletor sempre aparece, para dar para voltar a "Todos".
const mostrarDistritos = computed(() => clienteAtual()?.usa_distritos && (distritosDoCliente.value.length > 1 || (store.distrito && distritosDoCliente.value.length)))
const somenteConsulta = computed(() => store.contexto && !podeEditar())

function ativo(item) {
	return item.rota === "/" ? route.path === "/" : route.path.startsWith(item.rota)
}

const iniciais = computed(() =>
	(store.contexto?.usuario.nome || "?")
		.split(" ")
		.slice(0, 2)
		.map((p) => p[0])
		.join("")
		.toUpperCase(),
)

watch(
	() => route.fullPath,
	() => {
		menuAberto.value = false
		menuUsuario.value = false
		document.title = `${route.meta.titulo || ""} · ${store.contexto?.config.titulo || "Portal do Cliente"}`
	},
)

async function sair() {
	await fetch("/api/method/logout", { method: "POST", headers: { "X-Frappe-CSRF-Token": window.csrf_token } })
	window.location.href = CONSULTA ? "/acesso" : "/login"
}

onMounted(async () => {
	try {
		store.contexto = await api("contexto", { cliente: undefined, distrito: undefined })
		const ids = store.contexto.clientes.map((c) => c.id)
		const distritoSalvo = store.distrito
		if (store.cliente && !ids.includes(store.cliente)) definirCliente(null)
		if (ids.length === 1 && store.cliente !== ids[0]) definirCliente(ids[0])
		// mantém o distrito lembrado só se ele ainda estiver visível para o usuário
		const visiveis = (clienteAtual()?.distritos || []).map((d) => d.id)
		definirDistrito(visiveis.includes(distritoSalvo) ? distritoSalvo : null)
	} catch (e) {
		erro.value = e.message
	}
})
</script>

<template>
	<div v-if="erro" class="grid min-h-screen place-items-center p-6">
		<div class="card max-w-md p-8 text-center">
			<CircleAlert class="mx-auto mb-3 size-10 text-rose-500" />
			<p class="font-semibold text-slate-900">Não foi possível abrir o portal</p>
			<p class="mt-1 text-sm text-slate-500">{{ erro }}</p>
			<a :href="`/acesso?redirect-to=${BASE}`" class="btn-primary mt-5">Entrar com outro usuário</a>
		</div>
	</div>

	<div v-else-if="!store.contexto" class="grid min-h-screen place-items-center">
		<div class="size-8 animate-spin rounded-full border-[3px] border-brand-100 border-t-brand-600" />
	</div>

	<div v-else class="min-h-screen lg:pl-64">
		<!-- Menu lateral -->
		<Transition name="fade">
			<div v-if="menuAberto" class="fixed inset-0 z-30 bg-slate-900/40 lg:hidden" @click="menuAberto = false" />
		</Transition>
		<aside
			class="fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200/80 bg-white text-slate-600 transition-transform lg:translate-x-0"
			:class="menuAberto ? 'translate-x-0' : '-translate-x-full'"
		>
			<div class="flex items-center gap-3 px-6 pt-6 pb-4">
				<img :src="LOGO" alt="ER Analítica" class="h-11 w-auto" />
				<button class="ml-auto p-1 text-slate-400 lg:hidden" aria-label="Fechar menu" @click="menuAberto = false">
					<X class="size-5" />
				</button>
			</div>

			<p class="mx-6 mb-3 rounded-lg bg-brand-50 px-3 py-1.5 text-[11px] font-semibold tracking-wide text-brand-700">{{ store.contexto.config.titulo }}</p>
			<nav class="flex-1 space-y-0.5 px-3">
				<p class="px-3 pb-2 text-[10px] font-semibold tracking-widest text-slate-400 uppercase">Menu</p>
				<RouterLink
					v-for="item in nav"
					:key="item.nome"
					:to="item.rota"
					class="group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition"
					:class="ativo(item) ? 'bg-brand-50 text-brand-800' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'"
				>
					<span v-if="ativo(item)" class="absolute top-2 bottom-2 -left-3 w-1 rounded-r-full bg-brand-600" />
					<component
						:is="item.icone"
						class="size-[18px]"
						:class="ativo(item) ? 'text-brand-600' : 'text-slate-400 group-hover:text-slate-600'"
					/>
					{{ item.rotulo }}
				</RouterLink>
			</nav>

			<div v-if="CONSULTA" class="m-4 rounded-2xl bg-gradient-to-br from-brand-700 to-brand-500 p-4 text-white">
				<p class="text-xs font-semibold tracking-wide text-white/80 uppercase">Laboratório de calibração</p>
				<p class="mt-1 text-sm leading-snug">Certificados, rastreabilidade e prazos do seu parque num só lugar.</p>
			</div>
			<div v-if="!somenteConsulta && !CONSULTA" class="m-3 rounded-2xl bg-gradient-to-br from-brand-600 to-brand-800 p-4 text-white">
				<p class="text-sm font-semibold">Precisa calibrar?</p>
				<p class="mt-1 text-xs text-brand-100">Solicite coleta ou atendimento in loco em poucos cliques.</p>
				<RouterLink to="/solicitar" class="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-white px-3 py-2 text-sm font-medium text-brand-700 transition hover:bg-brand-50">
					<Plus class="size-4" /> Solicitar serviço
				</RouterLink>
			</div>
		</aside>

		<!-- Barra superior -->
		<header class="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-slate-200/70 bg-white/80 px-4 backdrop-blur-md sm:px-6">
			<button class="btn-ghost -ml-2 p-2 lg:hidden" aria-label="Abrir menu" @click="menuAberto = true">
				<Menu class="size-5" />
			</button>

			<div v-if="store.contexto.clientes.length > 1" class="relative">
				<Building2 class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" />
				<select
					class="input max-w-[220px] appearance-none py-1.5 pr-8 pl-9 font-medium sm:max-w-xs"
					:value="store.cliente || ''"
					@change="definirCliente($event.target.value)"
				>
					<option value="">Todos os clientes</option>
					<option v-for="c in store.contexto.clientes" :key="c.id" :value="c.id">{{ c.nome }}</option>
				</select>
				<ChevronDown class="pointer-events-none absolute top-1/2 right-2.5 size-4 -translate-y-1/2 text-slate-400" />
			</div>
			<p v-else class="truncate text-sm font-medium text-slate-700">{{ store.contexto.clientes[0]?.nome }}</p>

			<div v-if="mostrarDistritos" class="relative">
				<MapPin class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-brand-500" />
				<select
					class="input max-w-[200px] appearance-none border-brand-200 bg-brand-50/50 py-1.5 pr-8 pl-9 font-medium text-brand-900"
					:value="store.distrito || ''"
					@change="definirDistrito($event.target.value)"
				>
					<option value="">{{ clienteAtual()?.perfil === "Gestor" ? "Todos os distritos" : "Meus distritos" }}</option>
					<option v-for="d in distritosDoCliente" :key="d.id" :value="d.id">{{ d.nome }}</option>
				</select>
				<ChevronDown class="pointer-events-none absolute top-1/2 right-2.5 size-4 -translate-y-1/2 text-brand-400" />
			</div>
			<span
				v-else-if="clienteAtual()?.usa_distritos && distritosDoCliente.length === 1 && !store.distrito"
				class="hidden items-center gap-1.5 rounded-lg bg-brand-50 px-2.5 py-1 text-sm font-medium text-brand-800 sm:inline-flex"
			>
				<MapPin class="size-3.5" /> {{ distritosDoCliente[0].nome }}
			</span>

			<span v-if="somenteConsulta" class="hidden items-center gap-1.5 rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 md:inline-flex">
				<Eye class="size-3.5" /> Somente consulta
			</span>

			<div class="relative ml-auto">
				<button class="flex items-center gap-2.5 rounded-xl p-1 pr-2 hover:bg-slate-100" @click="menuUsuario = !menuUsuario">
					<img v-if="store.contexto.usuario.imagem" :src="store.contexto.usuario.imagem" class="size-8 rounded-full object-cover" alt="" />
					<span v-else class="grid size-8 place-items-center rounded-full bg-brand-100 text-xs font-semibold text-brand-700">{{ iniciais }}</span>
					<span class="hidden text-left leading-tight sm:block">
						<span class="block text-sm font-medium text-slate-800">{{ store.contexto.usuario.nome }}</span>
						<span class="block text-[11px] text-slate-500">{{ store.contexto.usuario.email }}</span>
					</span>
					<ChevronDown class="size-4 text-slate-400" />
				</button>
				<Transition name="slide">
					<div v-if="menuUsuario" class="absolute right-0 mt-2 w-56 rounded-xl border border-slate-200 bg-white p-1.5 shadow-pop">
						<a v-if="store.contexto.usuario.interno" href="/app" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-slate-50">
							<MonitorCog class="size-4 text-slate-400" /> Abrir o sistema (Desk)
						</a>
						<button class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-rose-600 hover:bg-rose-50" @click="sair">
							<LogOut class="size-4" /> Sair
						</button>
					</div>
				</Transition>
			</div>
		</header>

		<main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:py-8">
			<RouterView v-slot="{ Component }">
				<Transition name="fade" mode="out-in">
					<component :is="Component" :key="route.path + (store.cliente || '') + (store.distrito || '')" />
				</Transition>
			</RouterView>
		</main>

		<!-- Notificações -->
		<div class="pointer-events-none fixed right-4 bottom-4 z-[60] flex w-full max-w-sm flex-col gap-2">
			<TransitionGroup name="slide">
				<div
					v-for="t in store.toasts"
					:key="t.id"
					class="pointer-events-auto flex items-start gap-3 rounded-xl bg-slate-900 px-4 py-3 text-sm text-white shadow-pop"
				>
					<CircleCheck v-if="t.tipo === 'sucesso'" class="mt-0.5 size-4 shrink-0 text-emerald-400" />
					<CircleAlert v-else class="mt-0.5 size-4 shrink-0 text-rose-400" />
					<span class="whitespace-pre-line">{{ t.mensagem }}</span>
				</div>
			</TransitionGroup>
		</div>
	</div>
</template>
