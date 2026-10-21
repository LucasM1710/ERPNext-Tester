<script setup>
import { Eye, MapPin, Pencil, Plus, ShieldCheck, TriangleAlert, UserPlus, UserRound, UsersRound } from "lucide-vue-next"
import { computed, onMounted, reactive, ref } from "vue"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import Modal from "@/components/Modal.vue"
import Vazio from "@/components/Vazio.vue"
import { COR } from "@/cores"
import { dataHora } from "@/format"
import { definirDistrito, store, toast } from "@/store"
import { useRouter } from "vue-router"

const router = useRouter()
const gerenciaveis = computed(() => store.contexto.clientes.filter((c) => c.pode_gerenciar))
const cliente = ref(gerenciaveis.value.find((c) => c.id === store.cliente)?.id || gerenciaveis.value[0]?.id)

const aba = ref("distritos")
const dados = ref(null)
const usuarios = ref(null)

// distrito: undefined => a gestão sempre enxerga o cliente inteiro, independente do filtro do topo
const chamar = (metodo, params = {}, opcoes) => api(`gestao.${metodo}`, { cliente: cliente.value, distrito: undefined, ...params }, opcoes)

async function carregar() {
	;[dados.value, usuarios.value] = await Promise.all([chamar("distritos"), chamar("usuarios")])
}

async function atualizarContexto() {
	store.contexto = await api("contexto", { cliente: undefined, distrito: undefined })
}

onMounted(() => cliente.value && carregar())

function corPct(p) {
	return p >= 90 ? COR.verde : p >= 75 ? COR.ambar : COR.vermelho
}

// ------------------------------------------------------------ distritos
const formDistrito = ref(null)
function editarDistrito(d) {
	formDistrito.value = d ? { ...d } : { nome: "", descricao: "", ativo: true, responsavel_nome: "", responsavel_email: "", uf: "", cidade: "" }
}
async function salvarDistrito() {
	try {
		const f = formDistrito.value
		await chamar(
			"salvar_distrito",
			{
				id: f.id, nome: f.nome, descricao: f.descricao, ativo: f.ativo ? 1 : 0,
				responsavel_nome: f.responsavel_nome, responsavel_email: f.responsavel_email, uf: f.uf, cidade: f.cidade,
			},
			{ post: true },
		)
		toast(f.id ? "Distrito atualizado." : `Distrito ${f.nome} criado.`)
		formDistrito.value = null
		await Promise.all([carregar(), atualizarContexto()])
	} catch (e) {
		toast(e.message, "erro")
	}
}

function verDistrito(d) {
	definirDistrito(d.id)
	router.push("/equipamentos")
}

// equipamentos sem distrito -> distribuir
const organizar = ref(null)
async function abrirOrganizar() {
	const todos = await api("equipamentos", { cliente: cliente.value, distrito: undefined })
	organizar.value = { lista: todos.filter((e) => !e.distrito), marcados: new Set(), destino: "" }
}
async function distribuir() {
	const o = organizar.value
	if (!o.destino || !o.marcados.size) return toast("Escolha o distrito e os equipamentos.", "erro")
	try {
		const r = await chamar("distribuir_equipamentos", { distrito: o.destino, equipamentos: [...o.marcados] }, { post: true })
		toast(`${r.movidos} equipamento(s) organizados.`)
		organizar.value = null
		carregar()
	} catch (e) {
		toast(e.message, "erro")
	}
}

// ------------------------------------------------------------ usuários
const PERFIS = [
	{ valor: "Gestor", icone: ShieldCheck, texto: "Vê todo o parque, os relatórios e os logs; administra distritos e equipe." },
	{ valor: "Líder", icone: UserRound, texto: "Vê e opera somente os distritos atribuídos (cadastra terceiros, anota observações)." },
	{ valor: "Usuário", icone: Eye, texto: "Vê somente os equipamentos sob a sua responsabilidade, só leitura." },
]
const formUsuario = ref(null)
function editarUsuario(u) {
	formUsuario.value = reactive(
		u
			? { id: u.id, email: u.email, nome: u.nome, perfil: u.perfil, ativo: u.ativo, distritos: new Set(u.distritos.map((d) => d.id)), equipamentos: new Set(u.equipamentos || []), eu: u.eu }
			: { email: "", nome: "", perfil: "Líder", ativo: true, distritos: new Set(), equipamentos: new Set() },
	)
	buscaEqp.value = ""
	if (!parque.value) api("equipamentos", { cliente: cliente.value }).then((l) => (parque.value = l))
}
// Perfil Usuário: escolha dos equipamentos sob a responsabilidade dele.
const parque = ref(null)
const buscaEqp = ref("")
const parqueFiltrado = computed(() => {
	const q = buscaEqp.value.trim().toLowerCase()
	return (parque.value || []).filter((e) => !q || [e.tag, e.descricao, e.numero_serie, e.distrito_nome].some((v) => String(v || "").toLowerCase().includes(q)))
})
function alternarEquipamento(id) {
	const s = formUsuario.value.equipamentos
	s.has(id) ? s.delete(id) : s.add(id)
}
function alternarDistrito(id) {
	const s = formUsuario.value.distritos
	s.has(id) ? s.delete(id) : s.add(id)
}
async function salvarUsuario() {
	const f = formUsuario.value
	if (f.perfil === "Líder" && !f.distritos.size) return toast("Atribua ao menos um distrito ao Líder.", "erro")
	if (f.perfil === "Usuário" && !f.equipamentos.size) return toast("Escolha os equipamentos sob a responsabilidade do usuário.", "erro")
	try {
		const r = await chamar(
			"salvar_usuario",
			{ id: f.id, email: f.email, nome: f.nome, perfil: f.perfil, ativo: f.ativo ? 1 : 0, distritos: [...f.distritos], equipamentos: [...f.equipamentos] },
			{ post: true },
		)
		toast(r.convidado ? `Convite enviado para ${f.email}.` : "Acesso atualizado.")
		formUsuario.value = null
		carregar()
	} catch (e) {
		toast(e.message, "erro")
	}
}

const distritosAtivos = computed(() => (dados.value?.distritos || []).filter((d) => d.ativo))
</script>

<template>
	<div class="space-y-6">
		<div class="flex flex-wrap items-end justify-between gap-4">
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-slate-900">Distritos e equipe</h1>
				<p class="mt-1 text-sm text-slate-500">Organize o parque por distrito e defina quem enxerga e opera cada um.</p>
			</div>
			<select v-if="gerenciaveis.length > 1" v-model="cliente" class="input w-auto" @change="carregar">
				<option v-for="c in gerenciaveis" :key="c.id" :value="c.id">{{ c.nome }}</option>
			</select>
		</div>

		<div v-if="!cliente" class="card">
			<Vazio :icone="UsersRound" titulo="Nenhum cliente para administrar" texto="Esta área é para gestores de clientes com controle por distritos." />
		</div>

		<template v-else>
			<nav class="flex gap-1 rounded-xl bg-slate-100 p-1 sm:w-fit">
				<button
					v-for="a in [
						{ id: 'distritos', rotulo: 'Distritos', icone: MapPin, n: dados?.distritos.length },
						{ id: 'equipe', rotulo: 'Equipe', icone: UsersRound, n: usuarios?.length },
					]"
					:key="a.id"
					class="flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition"
					:class="aba === a.id ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'"
					@click="aba = a.id"
				>
					<component :is="a.icone" class="size-4" /> {{ a.rotulo }}
					<span class="rounded-full bg-slate-200/80 px-1.5 text-[11px] text-slate-600 tabular-nums">{{ a.n ?? "…" }}</span>
				</button>
			</nav>

			<div v-if="!dados" class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
				<div v-for="i in 4" :key="i" class="card p-5"><Esqueleto :linhas="4" /></div>
			</div>

			<!-- ================= Distritos ================= -->
			<template v-else-if="aba === 'distritos'">
				<div v-if="dados.equipamentos_sem_distrito" class="flex flex-wrap items-center gap-4 rounded-2xl border border-amber-200 bg-amber-50/70 p-4">
					<TriangleAlert class="size-5 text-amber-600" />
					<p class="flex-1 text-sm text-amber-900">
						<b>{{ dados.equipamentos_sem_distrito }} equipamento(s) sem distrito</b> — usuários de distrito não conseguem vê-los.
					</p>
					<button class="btn-secondary" @click="abrirOrganizar">Organizar agora</button>
				</div>

				<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
					<article v-for="d in dados.distritos" :key="d.id" class="card flex flex-col p-5" :class="!d.ativo && 'opacity-60'">
						<div class="flex items-start justify-between gap-2">
							<div class="min-w-0">
								<p class="truncate font-semibold text-slate-900">{{ d.nome }}</p>
								<p class="text-xs text-slate-500">{{ d.ativo ? `${d.usuarios} usuário(s) com acesso` : "Inativo" }}</p>
								<p v-if="d.responsavel_nome || d.cidade" class="mt-1 truncate text-xs text-slate-600">
									{{ d.responsavel_nome || "Sem responsável" }}<template v-if="d.cidade || d.uf"> · {{ [d.cidade, d.uf].filter(Boolean).join("/") }}</template>
								</p>
							</div>
							<button class="btn-ghost -mt-1 -mr-2 p-1.5" title="Editar" @click="editarDistrito(d)"><Pencil class="size-4" /></button>
						</div>
						<div class="mt-4 flex items-end justify-between">
							<p class="text-3xl font-semibold tabular-nums" :style="{ color: d.total && d.em_dia_pct !== null ? corPct(d.em_dia_pct) : COR.cinza }">
								{{ d.total && d.em_dia_pct !== null ? Math.round(d.em_dia_pct) : "—" }}<span v-if="d.total && d.em_dia_pct !== null" class="text-base">%</span>
							</p>
							<p class="text-xs text-slate-500">{{ d.em_dia_pct === null && d.total ? "sem calibração registrada" : "em dia" }}</p>
						</div>
						<div class="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
							<div class="h-full rounded-full" :style="{ width: (d.em_dia_pct || 0) + '%', background: corPct(d.em_dia_pct) }" />
						</div>
						<dl class="mt-4 grid grid-cols-3 gap-2 text-center">
							<div class="rounded-lg bg-slate-50 py-2"><dt class="text-[11px] text-slate-500">Total</dt><dd class="font-semibold text-slate-900">{{ d.total }}</dd></div>
							<div class="rounded-lg bg-rose-50 py-2"><dt class="text-[11px] text-rose-600">Vencidos</dt><dd class="font-semibold text-rose-700">{{ d.vencidos }}</dd></div>
							<div class="rounded-lg bg-amber-50 py-2"><dt class="text-[11px] text-amber-600">A vencer</dt><dd class="font-semibold text-amber-700">{{ d.a_vencer }}</dd></div>
						</dl>
						<button v-if="d.total" class="mt-4 text-left text-sm font-medium text-brand-600 hover:text-brand-700" @click="verDistrito(d)">Ver equipamentos →</button>
					</article>

					<button class="card flex min-h-[220px] flex-col items-center justify-center gap-2 border-dashed text-slate-500 transition hover:border-brand-300 hover:text-brand-700" @click="editarDistrito(null)">
						<Plus class="size-6" /> <span class="text-sm font-medium">Novo distrito</span>
					</button>
				</div>
			</template>

			<!-- ================= Equipe ================= -->
			<section v-else class="card overflow-hidden">
				<div class="flex items-center justify-between gap-4 border-b border-slate-100 p-4">
					<p class="text-sm text-slate-500">Quem acessa o portal pela sua empresa. Convidados recebem um e-mail para definir a senha.</p>
					<button class="btn-primary" @click="editarUsuario(null)"><UserPlus class="size-4" /> Convidar</button>
				</div>
				<div class="overflow-x-auto">
					<table class="w-full min-w-[720px]">
						<thead class="border-b border-slate-100 bg-slate-50/60">
							<tr>
								<th class="th">Usuário</th>
								<th class="th">Perfil</th>
								<th class="th">Distritos</th>
								<th class="th">Último acesso</th>
								<th class="th w-12"></th>
							</tr>
						</thead>
						<tbody class="divide-y divide-slate-100">
							<tr v-for="u in usuarios" :key="u.id" :class="!u.ativo && 'opacity-50'">
								<td class="td">
									<p class="font-medium text-slate-900">{{ u.nome || u.email }} <span v-if="u.eu" class="text-xs font-normal text-slate-400">(você)</span></p>
									<p class="text-xs text-slate-500">{{ u.email }}</p>
								</td>
								<td class="td">
									<span
										class="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-semibold"
										:class="{ Gestor: 'bg-brand-50 text-brand-700', Líder: 'bg-emerald-50 text-emerald-700', Usuário: 'bg-slate-100 text-slate-600' }[u.perfil]"
										>{{ u.perfil }}</span
									>
									<span v-if="!u.ativo" class="ml-1 text-xs text-rose-600">desativado</span>
								</td>
								<td class="td">
									<span v-if="u.perfil === 'Gestor'" class="text-xs text-slate-500">Todos</span>
									<span v-else-if="u.perfil === 'Usuário'" class="text-xs text-slate-500">{{ (u.equipamentos || []).length }} equipamento(s) sob responsabilidade</span>
									<div v-else class="flex flex-wrap gap-1">
										<span v-for="d in u.distritos" :key="d.id" class="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-700">{{ d.nome }}</span>
									</div>
								</td>
								<td class="td text-xs text-slate-500">{{ u.ultimo_acesso ? dataHora(u.ultimo_acesso) : "Nunca acessou" }}</td>
								<td class="td"><button class="btn-ghost p-1.5" title="Editar acesso" @click="editarUsuario(u)"><Pencil class="size-4" /></button></td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>
		</template>

		<!-- Modal distrito -->
		<Modal v-if="formDistrito" :titulo="formDistrito.id ? 'Editar distrito' : 'Novo distrito'" largura="max-w-md" @fechar="formDistrito = null">
			<form id="form-distrito" class="space-y-4" @submit.prevent="salvarDistrito">
				<div>
					<label class="label">Nome *</label>
					<input v-model="formDistrito.nome" class="input" required placeholder="Ex.: Distrito Norte" />
				</div>
				<div>
					<label class="label">Descrição / endereço</label>
					<textarea v-model="formDistrito.descricao" rows="2" class="input" />
				</div>
				<div class="grid gap-4 sm:grid-cols-2">
					<div>
						<label class="label">Responsável (owner)</label>
						<input v-model="formDistrito.responsavel_nome" class="input" placeholder="Quem responde pelos equipamentos" />
					</div>
					<div>
						<label class="label">E-mail do responsável</label>
						<input v-model="formDistrito.responsavel_email" type="email" class="input" />
					</div>
					<div>
						<label class="label">Cidade</label>
						<input v-model="formDistrito.cidade" class="input" />
					</div>
					<div>
						<label class="label">UF</label>
						<input v-model="formDistrito.uf" maxlength="2" class="input uppercase" placeholder="SP" />
					</div>
				</div>
				<label v-if="formDistrito.id" class="flex items-center gap-2 text-sm text-slate-700">
					<input v-model="formDistrito.ativo" type="checkbox" class="accent-brand-600" /> Distrito ativo
				</label>
			</form>
			<template #rodape>
				<button class="btn-secondary" @click="formDistrito = null">Cancelar</button>
				<button class="btn-primary" form="form-distrito" type="submit">Salvar</button>
			</template>
		</Modal>

		<!-- Modal organizar -->
		<Modal v-if="organizar" titulo="Organizar equipamentos sem distrito" subtitulo="Selecione os equipamentos e o distrito de destino." largura="max-w-2xl" @fechar="organizar = null">
			<div class="space-y-4">
				<select v-model="organizar.destino" class="input">
					<option value="" disabled>Mover para o distrito…</option>
					<option v-for="d in distritosAtivos" :key="d.id" :value="d.id">{{ d.nome }}</option>
				</select>
				<ul class="max-h-80 divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-100">
					<li v-for="e in organizar.lista" :key="e.id">
						<label class="flex cursor-pointer items-center gap-3 px-4 py-2.5 text-sm hover:bg-slate-50">
							<input
								type="checkbox"
								class="accent-brand-600"
								:checked="organizar.marcados.has(e.id)"
								@change="organizar.marcados.has(e.id) ? organizar.marcados.delete(e.id) : organizar.marcados.add(e.id)"
							/>
							<b class="font-medium text-slate-900">{{ e.tag }}</b> <span class="text-slate-500">{{ e.descricao }} · {{ e.localizacao || "—" }}</span>
						</label>
					</li>
				</ul>
			</div>
			<template #rodape>
				<button class="btn-secondary" @click="organizar = null">Cancelar</button>
				<button class="btn-primary" @click="distribuir">Mover {{ organizar.marcados.size || "" }}</button>
			</template>
		</Modal>

		<!-- Modal usuário -->
		<Modal v-if="formUsuario" :titulo="formUsuario.id ? 'Editar acesso' : 'Convidar usuário'" largura="max-w-xl" @fechar="formUsuario = null">
			<form id="form-usuario" class="space-y-5" @submit.prevent="salvarUsuario">
				<div class="grid gap-4 sm:grid-cols-2">
					<div>
						<label class="label">E-mail *</label>
						<input v-model="formUsuario.email" type="email" class="input" required :disabled="!!formUsuario.id" />
					</div>
					<div>
						<label class="label">Nome</label>
						<input v-model="formUsuario.nome" class="input" :disabled="!!formUsuario.id" />
					</div>
				</div>
				<div>
					<p class="label">Perfil</p>
					<div class="grid gap-2">
						<label
							v-for="p in PERFIS"
							:key="p.valor"
							class="flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition"
							:class="formUsuario.perfil === p.valor ? 'border-brand-400 bg-brand-50/60 ring-4 ring-brand-100' : 'border-slate-200 hover:bg-slate-50'"
						>
							<input v-model="formUsuario.perfil" type="radio" :value="p.valor" class="mt-1 accent-brand-600" :disabled="formUsuario.eu" />
							<component :is="p.icone" class="mt-0.5 size-4 shrink-0" :class="formUsuario.perfil === p.valor ? 'text-brand-600' : 'text-slate-400'" />
							<span>
								<span class="block text-sm font-semibold text-slate-900">{{ p.valor }}</span>
								<span class="block text-xs text-slate-500">{{ p.texto }}</span>
							</span>
						</label>
					</div>
				</div>
				<div v-if="formUsuario.perfil === 'Usuário'">
					<p class="label">Equipamentos sob a responsabilidade dele * <span class="font-normal text-slate-400">({{ formUsuario.equipamentos.size }} selecionado(s))</span></p>
					<input v-model="buscaEqp" class="input mb-2" placeholder="Buscar por TAG, equipamento, série ou distrito…" />
					<div class="max-h-60 divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-200">
						<p v-if="!parque" class="p-3 text-sm text-slate-500">Carregando…</p>
						<label v-for="e in parqueFiltrado" :key="e.id" class="flex cursor-pointer items-center gap-3 px-3 py-2 text-sm hover:bg-slate-50">
							<input type="checkbox" class="accent-brand-600" :checked="formUsuario.equipamentos.has(e.id)" @change="alternarEquipamento(e.id)" />
							<span class="min-w-0 flex-1 truncate"><b class="font-medium text-slate-900">{{ e.tag }}</b> · {{ e.descricao }}</span>
							<span class="shrink-0 text-xs text-slate-400">{{ e.distrito_nome || "Sem distrito" }}</span>
						</label>
					</div>
				</div>
				<div v-if="formUsuario.perfil === 'Líder'">
					<p class="label">Distritos *</p>
					<div class="flex flex-wrap gap-2">
						<button
							v-for="d in distritosAtivos"
							:key="d.id"
							type="button"
							class="chip"
							:class="formUsuario.distritos.has(d.id) ? 'border-brand-500 bg-brand-600 text-white' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'"
							@click="alternarDistrito(d.id)"
						>
							<MapPin class="size-3.5" /> {{ d.nome }}
						</button>
					</div>
				</div>
				<label v-if="formUsuario.id && !formUsuario.eu" class="flex items-center gap-2 text-sm text-slate-700">
					<input v-model="formUsuario.ativo" type="checkbox" class="accent-brand-600" /> Acesso ativo
				</label>
			</form>
			<template #rodape>
				<button class="btn-secondary" @click="formUsuario = null">Cancelar</button>
				<button class="btn-primary" form="form-usuario" type="submit">{{ formUsuario.id ? "Salvar" : "Enviar convite" }}</button>
			</template>
		</Modal>
	</div>
</template>
