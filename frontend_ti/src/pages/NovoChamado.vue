<script setup>
import { ArrowLeft, Send, UserRound } from "lucide-vue-next"
import { computed, onMounted, reactive, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { api } from "@/api"
import Anexador from "@/components/Anexador.vue"
import IconeCategoria from "@/components/IconeCategoria.vue"
import IconeEquipamento from "@/components/IconeEquipamento.vue"
import { textoParaHtml } from "@/format"
import { eTecnico, store, toast } from "@/store"

const route = useRoute()
const router = useRouter()

const IMPACTOS = [
	{ valor: "Consigo trabalhar normalmente", titulo: "Não atrapalha", texto: "Dá para trabalhar normalmente", cor: "border-slate-400" },
	{ valor: "Atrapalha, mas consigo trabalhar", titulo: "Atrapalha", texto: "Consigo trabalhar, com dificuldade", cor: "border-sky-500" },
	{ valor: "Não consigo trabalhar", titulo: "Estou parado", texto: "Não consigo fazer meu trabalho", cor: "border-orange-500" },
	{ valor: "Afeta várias pessoas ou a empresa", titulo: "Afeta várias pessoas", texto: "Setor ou empresa impactados", cor: "border-rose-500" },
]

const f = reactive({
	categoria: route.query.categoria || "",
	assunto: route.query.assunto || "",
	descricao: "",
	impacto: "Atrapalha, mas consigo trabalhar",
	equipamento: route.query.equipamento || "",
	// só técnico
	solicitante: "",
	solicitante_nome: "",
	canal: "Portal",
	prioridade: "",
})
const arquivos = ref([])
// equipamentos de quem está pedindo (os meus; ou, para a TI, os do solicitante escolhido)
const equipamentos = ref([])
async function carregarEquipamentos() {
	equipamentos.value = await api("inventario.buscar_equipamentos", { usuario: eTecnico() ? f.solicitante || store.contexto.usuario.email : undefined })
	if (f.equipamento && !equipamentos.value.some((e) => e.id === f.equipamento)) f.equipamento = ""
}
onMounted(carregarEquipamentos)
watch(() => f.solicitante, carregarEquipamentos)
const enviando = ref(false)
const categoriaAtual = computed(() => store.contexto.categorias.find((c) => c.nome === f.categoria))

// técnico: abrir em nome de outra pessoa
const busca = ref("")
const pessoas = ref([])
let atraso
watch(busca, (t) => {
	clearTimeout(atraso)
	atraso = setTimeout(async () => (pessoas.value = t.length >= 2 ? await api("buscar_pessoas", { texto: t }) : []), 250)
})
function escolherPessoa(p) {
	f.solicitante = p.id
	f.solicitante_nome = p.nome
	busca.value = ""
	pessoas.value = []
}

async function enviar() {
	if (!f.assunto.trim()) return toast("Dê um título curto para o chamado.", "erro")
	enviando.value = true
	try {
		const c = await api(
			"abrir_chamado",
			{
				assunto: f.assunto,
				descricao: f.descricao.trim() ? textoParaHtml(f.descricao) : "",
				categoria: f.categoria,
				impacto: f.impacto,
				equipamento: f.equipamento,
				...(eTecnico() && { solicitante: f.solicitante, canal: f.canal, prioridade: f.prioridade }),
			},
			{ post: true, arquivos: arquivos.value },
		)
		toast(`Chamado ${c.id} aberto. Você vai receber as atualizações por e-mail.`)
		router.push(`/chamados/${c.id}`)
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		enviando.value = false
	}
}
</script>

<template>
	<div class="mx-auto max-w-3xl space-y-6">
		<RouterLink to="/" class="inline-flex items-center gap-1.5 text-sm text-suave hover:text-tinta"><ArrowLeft class="size-4" /> Voltar</RouterLink>
		<div>
			<h1 class="text-2xl font-semibold tracking-tight text-tinta">Abrir chamado</h1>
			<p class="mt-1 text-sm text-suave">Quanto mais detalhes (e prints), mais rápido a TI resolve.</p>
		</div>

		<form class="space-y-6" @submit.prevent="enviar">
			<!-- Categoria -->
			<section class="card p-5">
				<p class="rotulo">Sobre o que é?</p>
				<div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
					<button
						v-for="c in store.contexto.categorias"
						:key="c.nome"
						type="button"
						class="flex items-center gap-2.5 rounded-xl border p-3 text-left text-sm transition"
						:class="f.categoria === c.nome ? 'border-marca-500 bg-marca-500/10 font-medium text-tinta ring-4 ring-marca-500/15' : 'border-borda text-texto hover:bg-realce'"
						@click="f.categoria = c.nome"
					>
						<IconeCategoria :nome="c.icone" class="size-4 shrink-0" :class="f.categoria === c.nome ? 'text-marca-600 dark:text-marca-300' : 'text-suave'" />
						<span class="truncate">{{ c.nome }}</span>
					</button>
				</div>
				<p v-if="categoriaAtual?.descricao" class="mt-3 text-xs text-suave">{{ categoriaAtual.descricao }}</p>
			</section>

			<!-- Descrição -->
			<section class="card space-y-4 p-5">
				<div>
					<label class="rotulo">Título *</label>
					<input v-model="f.assunto" class="campo text-base" maxlength="140" required placeholder="Ex.: Outlook não abre desde a atualização" />
				</div>
				<div>
					<label class="rotulo">Descreva o que está acontecendo</label>
					<textarea v-model="f.descricao" rows="5" class="campo" placeholder="O que você estava fazendo, qual mensagem apareceu, desde quando…" />
				</div>
				<Anexador v-model="arquivos" />
			</section>

			<!-- Equipamento -->
			<section v-if="equipamentos.length" class="card p-5">
				<p class="rotulo">É sobre algum destes equipamentos? (opcional)</p>
				<div class="grid gap-2 sm:grid-cols-2">
					<button
						v-for="e in equipamentos"
						:key="e.id"
						type="button"
						class="flex items-center gap-3 rounded-xl border p-3 text-left text-sm transition"
						:class="f.equipamento === e.id ? 'border-marca-500 bg-marca-500/10 ring-4 ring-marca-500/15' : 'border-borda hover:bg-realce'"
						@click="f.equipamento = f.equipamento === e.id ? '' : e.id"
					>
						<IconeEquipamento :nome="e.icone" class="size-5 shrink-0 text-suave" />
						<span class="min-w-0"><span class="block font-medium text-tinta">{{ e.id }}</span><span class="block truncate text-xs text-suave">{{ e.modelo || e.tipo }}</span></span>
					</button>
				</div>
			</section>

			<!-- Impacto -->
			<section class="card p-5">
				<p class="rotulo">Quanto isso atrapalha seu trabalho?</p>
				<div class="grid gap-2 sm:grid-cols-2">
					<button
						v-for="i in IMPACTOS"
						:key="i.valor"
						type="button"
						class="rounded-xl border border-l-4 p-3 text-left transition"
						:class="[i.cor, f.impacto === i.valor ? 'bg-marca-500/10 ring-4 ring-marca-500/15' : 'border-borda hover:bg-realce']"
						@click="f.impacto = i.valor"
					>
						<span class="block text-sm font-semibold text-tinta">{{ i.titulo }}</span>
						<span class="block text-xs text-suave">{{ i.texto }}</span>
					</button>
				</div>
			</section>

			<!-- Só para a equipe de TI -->
			<section v-if="eTecnico()" class="card space-y-4 border-dashed p-5">
				<p class="text-xs font-semibold tracking-wider text-suave uppercase">Equipe de TI · registrar para outra pessoa</p>
				<div class="relative">
					<label class="rotulo">Solicitante</label>
					<div v-if="f.solicitante" class="flex items-center gap-2 rounded-xl border border-borda bg-realce px-3 py-2 text-sm">
						<UserRound class="size-4 text-suave" /> <span class="flex-1 text-tinta">{{ f.solicitante_nome }}</span>
						<button type="button" class="text-xs text-suave hover:text-rose-500" @click="(f.solicitante = ''), (f.solicitante_nome = '')">trocar</button>
					</div>
					<template v-else>
						<input v-model="busca" class="campo" placeholder="Você mesmo, ou busque pelo nome…" />
						<ul v-if="pessoas.length" class="absolute z-10 mt-1 w-full overflow-hidden rounded-xl border border-borda bg-elevada shadow-pop">
							<li v-for="p in pessoas" :key="p.id">
								<button type="button" class="w-full px-3 py-2 text-left text-sm hover:bg-realce" @click="escolherPessoa(p)">
									<span class="text-tinta">{{ p.nome }}</span> <span class="text-xs text-suave">{{ p.id }}</span>
								</button>
							</li>
						</ul>
					</template>
				</div>
				<div class="grid gap-4 sm:grid-cols-2">
					<div>
						<label class="rotulo">Canal</label>
						<select v-model="f.canal" class="campo">
							<option>Portal</option><option>Telefone</option><option>Presencial</option><option>E-mail</option>
						</select>
					</div>
					<div>
						<label class="rotulo">Prioridade</label>
						<select v-model="f.prioridade" class="campo">
							<option value="">Pelo impacto informado</option><option>Crítica</option><option>Alta</option><option>Média</option><option>Baixa</option>
						</select>
					</div>
				</div>
			</section>

			<div class="flex justify-end gap-2">
				<RouterLink to="/" class="btn-secundario">Cancelar</RouterLink>
				<button type="submit" class="btn-primario px-5" :disabled="enviando"><Send class="size-4" /> {{ enviando ? "Enviando…" : "Abrir chamado" }}</button>
			</div>
		</form>
	</div>
</template>
