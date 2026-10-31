<script setup>
import {
	ArrowLeftRight,
	BookOpen,
	ChevronDown,
	CircleAlert,
	CircleCheck,
	FileText,
	FlaskConical,
	LogOut,
	Menu,
	MonitorCog,
	Moon,
	Receipt,
	Rocket,
	Send,
	Settings,
	Sun,
	X,
} from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"
import { useRoute } from "vue-router"
import { api } from "./api"
import Avatar from "./components/Avatar.vue"
import { alternarTema, store } from "./store"

const route = useRoute()
const erro = ref(null)
const menuAberto = ref(false)
const menuUsuario = ref(false)

const nav = computed(() => [
	{ rotulo: "Para emitir", icone: Send, rota: "/", alerta: store.contexto?.contadores.rejeitadas },
	{ rotulo: "Notas emitidas", icone: FileText, rota: "/notas" },
	{ rotulo: "Boletos", icone: Receipt, rota: "/boletos", alerta: store.contexto?.contadores.boletos_vencidos },
	{ rotulo: "Remessa e retorno", icone: ArrowLeftRight, rota: "/remessas", alerta: store.contexto?.contadores.remessas_atrasadas },
])

function ativo(rota) {
	return rota === "/" ? route.path === "/" : route.path.startsWith(rota)
}

async function carregarContexto() {
	store.contexto = await api("contexto")
}

watch(
	() => route.fullPath,
	() => {
		menuAberto.value = false
		menuUsuario.value = false
		document.title = `${route.meta.titulo || ""} · Notas e Boletos`
		if (store.contexto) carregarContexto().catch(() => {})
	},
)

async function sair() {
	await fetch("/api/method/logout", { method: "POST", headers: { "X-Frappe-CSRF-Token": window.csrf_token } })
	window.location.href = "/login"
}

onMounted(async () => {
	try {
		await carregarContexto()
	} catch (e) {
		erro.value = e.message
	}
})
</script>

<template>
	<div v-if="erro" class="grid min-h-screen place-items-center p-6">
		<div class="card max-w-md p-8 text-center">
			<CircleAlert class="mx-auto mb-3 size-10 text-rose-500" />
			<p class="font-semibold text-tinta">Não foi possível abrir Notas e Boletos</p>
			<p class="mt-1 text-sm text-suave">{{ erro }}</p>
			<a href="/login?redirect-to=/fiscal" class="btn-primario mt-5">Entrar</a>
		</div>
	</div>

	<div v-else-if="!store.contexto" class="grid min-h-screen place-items-center">
		<div class="size-8 animate-spin rounded-full border-[3px] border-marca-500/20 border-t-marca-600" />
	</div>

	<div v-else class="min-h-screen lg:pl-64">
		<Transition name="fade">
			<div v-if="menuAberto" class="fixed inset-0 z-30 bg-slate-950/50 lg:hidden" @click="menuAberto = false" />
		</Transition>

		<aside
			class="fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-borda bg-superficie transition-transform lg:translate-x-0"
			:class="menuAberto ? 'translate-x-0' : '-translate-x-full'"
		>
			<div class="flex h-16 items-center gap-3 px-5">
				<div class="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-marca-500 to-emerald-600 shadow-lg shadow-marca-600/30">
					<Receipt class="size-5 text-white" />
				</div>
				<div class="min-w-0 leading-tight">
					<p class="truncate text-sm font-semibold text-tinta">Notas e Boletos</p>
					<p class="truncate text-[11px] text-suave">{{ store.contexto.empresa }}</p>
				</div>
				<button class="ml-auto p-1 text-suave lg:hidden" aria-label="Fechar menu" @click="menuAberto = false"><X class="size-5" /></button>
			</div>

			<nav class="mt-4 flex-1 space-y-1 overflow-y-auto px-3">
				<RouterLink
					v-for="item in nav"
					:key="item.rota"
					:to="item.rota"
					class="flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition"
					:class="ativo(item.rota) ? 'bg-marca-500/10 text-marca-700 dark:text-marca-300' : 'text-texto hover:bg-realce'"
				>
					<component :is="item.icone" class="size-[18px]" />
					<span class="flex-1">{{ item.rotulo }}</span>
					<span v-if="item.alerta" class="rounded-full bg-rose-500 px-2 text-[11px] font-semibold text-white tabular-nums">{{ item.alerta }}</span>
				</RouterLink>

				<p class="px-3 pt-5 pb-1 text-[10px] font-semibold tracking-widest text-suave uppercase">Ajuda e gestão</p>
				<RouterLink to="/ajuda" class="flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition"
					:class="ativo('/ajuda') ? 'bg-marca-500/10 text-marca-700 dark:text-marca-300' : 'text-texto hover:bg-realce'">
					<BookOpen class="size-[18px]" /> Manual
				</RouterLink>
				<RouterLink to="/producao" class="flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition"
					:class="ativo('/producao') ? 'bg-marca-500/10 text-marca-700 dark:text-marca-300' : 'text-texto hover:bg-realce'">
					<Rocket class="size-[18px]" /> Ir para produção
				</RouterLink>
				<a v-if="store.contexto.pode_configurar" href="/app/configuracao-fiscal" class="flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium text-texto transition hover:bg-realce">
					<Settings class="size-[18px]" /> Configuração fiscal
				</a>
			</nav>

			<div v-if="store.contexto.simulacao" class="m-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-800 dark:text-amber-200">
				<p class="flex items-center gap-1.5 font-semibold"><FlaskConical class="size-4" /> Modo simulação</p>
				<p class="mt-1">Notas e boletos são de teste, sem valor fiscal. Nada é enviado à SEFAZ, à prefeitura, ao banco ou ao cliente.</p>
			</div>
		</aside>

		<header class="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-borda bg-fundo/75 px-4 backdrop-blur-xl sm:px-6">
			<button class="btn-fantasma -ml-2 p-2 lg:hidden" aria-label="Abrir menu" @click="menuAberto = true"><Menu class="size-5" /></button>
			<p class="truncate text-sm font-semibold text-tinta">{{ route.meta.titulo }}</p>
			<span v-if="store.contexto.simulacao" class="hidden rounded-full bg-amber-500/15 px-2.5 py-0.5 text-[11px] font-semibold text-amber-700 sm:inline dark:text-amber-300">SIMULAÇÃO</span>
			<span v-else class="hidden rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700 sm:inline dark:text-emerald-300">{{ store.contexto.ambiente.toUpperCase() }}</span>

			<div class="ml-auto flex items-center gap-1">
				<button class="btn-fantasma p-2" :title="store.escuro ? 'Tema claro' : 'Tema escuro'" @click="alternarTema">
					<Sun v-if="store.escuro" class="size-[18px]" /><Moon v-else class="size-[18px]" />
				</button>
				<div class="relative">
					<button class="flex items-center gap-2.5 rounded-xl p-1 pr-2 hover:bg-realce" @click="menuUsuario = !menuUsuario">
						<img v-if="store.contexto.usuario.imagem" :src="store.contexto.usuario.imagem" class="size-8 rounded-full object-cover" alt="" />
						<Avatar v-else :nome="store.contexto.usuario.nome" />
						<span class="hidden text-left leading-tight sm:block">
							<span class="block text-sm font-medium text-tinta">{{ store.contexto.usuario.nome }}</span>
							<span class="block text-[11px] text-suave">Financeiro</span>
						</span>
						<ChevronDown class="size-4 text-suave" />
					</button>
					<Transition name="slide">
						<div v-if="menuUsuario" class="absolute right-0 mt-2 w-56 rounded-xl border border-borda bg-elevada p-1.5 shadow-pop">
							<a href="/app" class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-texto hover:bg-realce"><MonitorCog class="size-4 text-suave" /> Ir para o ERP</a>
							<button class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-rose-600 hover:bg-rose-500/10" @click="sair"><LogOut class="size-4" /> Sair</button>
						</div>
					</Transition>
				</div>
			</div>
		</header>

		<main class="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-8">
			<RouterView v-slot="{ Component }">
				<Transition name="fade" mode="out-in">
					<component :is="Component" :key="route.path" />
				</Transition>
			</RouterView>
		</main>

		<div class="pointer-events-none fixed right-4 bottom-4 z-[60] flex w-full max-w-sm flex-col gap-2">
			<TransitionGroup name="slide">
				<div v-for="t in store.toasts" :key="t.id" class="pointer-events-auto flex items-start gap-3 rounded-xl bg-slate-900 px-4 py-3 text-sm text-white shadow-pop dark:bg-slate-800">
					<CircleCheck v-if="t.tipo === 'sucesso'" class="mt-0.5 size-4 shrink-0 text-emerald-400" />
					<CircleAlert v-else class="mt-0.5 size-4 shrink-0 text-rose-400" />
					<span class="whitespace-pre-line">{{ t.mensagem }}</span>
				</div>
			</TransitionGroup>
		</div>
	</div>
</template>
