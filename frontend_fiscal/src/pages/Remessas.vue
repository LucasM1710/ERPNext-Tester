<script setup>
import { ArrowDownLeft, ArrowUpRight, CircleAlert, PackageCheck, Plus, Truck } from "lucide-vue-next"
import { onMounted, ref } from "vue"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import Modal from "@/components/Modal.vue"
import Vazio from "@/components/Vazio.vue"
import { data, hojeISO, moeda } from "@/format"
import { toast } from "@/store"

const dados = ref(null)
const retorno = ref(null)
const form = ref({ chave: "", data: hojeISO() })
const chaveInfo = ref(null)
const ocupado = ref(false)

const ATALHOS = [
	{ natureza: "Retorno de conserto ou calibração", icone: ArrowDownLeft, titulo: "Devolver equipamento ao cliente", texto: "O cliente mandou o equipamento para calibrar ou consertar e ele está pronto para voltar." },
	{ natureza: "Remessa para conserto ou calibração", icone: ArrowUpRight, titulo: "Enviar equipamento nosso para fora", texto: "Mandar um padrão ou equipamento nosso para calibrar ou consertar em outro laboratório ou no fabricante." },
]

async function carregar() {
	dados.value = await api("remessas")
}

function abrirRetorno(n) {
	retorno.value = n
	form.value = { chave: "", data: hojeISO() }
	chaveInfo.value = null
}

async function lerChave() {
	const c = form.value.chave.replace(/\D/g, "")
	chaveInfo.value = c ? await api("decodificar_chave", { chave: c }) : null
}

async function registrar() {
	ocupado.value = true
	try {
		await api("registrar_retorno", { id: retorno.value.id, chave: form.value.chave.replace(/\D/g, ""), data: form.value.data }, { post: true })
		toast("Retorno registrado. O equipamento saiu da lista de pendentes.")
		retorno.value = null
		await carregar()
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		ocupado.value = false
	}
}

onMounted(carregar)
</script>

<template>
	<div class="space-y-6">
		<div class="flex flex-wrap items-end justify-between gap-4">
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-tinta">Remessa e retorno</h1>
				<p class="mt-1 text-sm text-suave">Notas para movimentar equipamentos sem venda: não geram boleto nem cobrança.</p>
			</div>
			<RouterLink to="/remessas/nova" class="btn-secundario"><Plus class="size-4" /> Outra operação</RouterLink>
		</div>

		<div class="grid gap-3 sm:grid-cols-2">
			<RouterLink v-for="a in ATALHOS" :key="a.natureza" :to="{ path: '/remessas/nova', query: { natureza: a.natureza } }" class="card group flex gap-4 p-5 transition hover:ring-2 hover:ring-marca-500/30">
				<span class="grid size-12 shrink-0 place-items-center rounded-2xl bg-marca-500/12 text-marca-600 dark:text-marca-300"><component :is="a.icone" class="size-6" /></span>
				<div>
					<p class="font-semibold text-tinta group-hover:text-marca-700 dark:group-hover:text-marca-300">{{ a.titulo }}</p>
					<p class="mt-0.5 text-sm text-suave">{{ a.texto }}</p>
				</div>
			</RouterLink>
		</div>

		<section class="card overflow-hidden">
			<div class="flex items-center gap-2 px-5 pt-5 pb-3">
				<Truck class="size-4 text-suave" />
				<h2 class="text-sm font-semibold text-tinta">Nossos equipamentos fora da empresa</h2>
			</div>
			<div v-if="!dados" class="px-5 pb-5"><Esqueleto :linhas="3" /></div>
			<Vazio v-else-if="!dados.abertas.length" :icone="PackageCheck" titulo="Nada fora" texto="Quando você enviar um equipamento com nota de remessa, ele aparece aqui até voltar." />
			<table v-else class="w-full">
				<thead class="border-y border-borda bg-realce/50"><tr><th class="th">Destino</th><th class="th hidden sm:table-cell">Nota</th><th class="th">Fora há</th><th class="th">Volta até</th><th class="th" /></tr></thead>
				<tbody class="divide-y divide-borda">
					<tr v-for="n in dados.abertas" :key="n.id">
						<td class="td"><RouterLink :to="`/notas/${n.id}`" class="font-medium text-tinta hover:underline">{{ n.nome_parte }}</RouterLink><p class="text-xs text-suave">{{ n.natureza }} · {{ moeda(n.valor_total) }}</p></td>
						<td class="td hidden text-suave sm:table-cell">NF-e nº {{ n.numero }}</td>
						<td class="td text-tinta tabular-nums">{{ n.dias_fora }} dias</td>
						<td class="td">
							<span :class="n.atrasada ? 'font-medium text-rose-600' : 'text-suave'">{{ data(n.prazo_retorno) }}</span>
							<span v-if="n.atrasada" class="ml-1 inline-flex items-center gap-1 text-xs text-rose-600"><CircleAlert class="size-3.5" /> atrasado</span>
						</td>
						<td class="td text-right"><button class="btn-secundario px-2.5 py-1.5 text-xs" @click="abrirRetorno(n)">Chegou de volta</button></td>
					</tr>
				</tbody>
			</table>
		</section>

		<section v-if="dados?.recentes.length" class="card overflow-hidden">
			<h2 class="px-5 pt-5 pb-3 text-sm font-semibold text-tinta">Últimas remessas e retornos</h2>
			<table class="w-full">
				<tbody class="divide-y divide-borda border-t border-borda">
					<tr v-for="n in dados.recentes" :key="n.id" class="cursor-pointer hover:bg-realce/60" @click="$router.push(`/notas/${n.id}`)">
						<td class="td"><p class="font-medium text-tinta">{{ n.natureza }}</p><p class="text-xs text-suave">{{ n.nome_parte }}</p></td>
						<td class="td hidden text-suave sm:table-cell">{{ n.numero ? `nº ${n.numero}` : "—" }} · {{ data(n.data_emissao || n.creation) }}</td>
						<td class="td text-right text-tinta tabular-nums">{{ moeda(n.valor_total) }}</td>
						<td class="td"><Etiqueta :valor="n.situacao_remessa === 'Retornada' ? 'Retornada' : n.status" /></td>
					</tr>
				</tbody>
			</table>
		</section>

		<Modal v-if="retorno" titulo="Registrar o retorno" :subtitulo="`${retorno.nome_parte} · NF-e nº ${retorno.numero}`" @fechar="retorno = null">
			<div class="space-y-3 text-sm">
				<p class="text-suave">Quem devolve o equipamento emite a nota de retorno. Aqui você só registra que ele voltou; a chave da nota é opcional, mas ajuda na auditoria.</p>
				<div>
					<label class="rotulo">Chave da nota de retorno (44 dígitos, opcional)</label>
					<input v-model="form.chave" class="campo font-mono" placeholder="0000 0000 0000 …" @blur="lerChave" />
					<p v-if="chaveInfo && chaveInfo.valida" class="mt-1 text-xs text-emerald-600">✓ NF-e {{ chaveInfo.numero }}, série {{ chaveInfo.serie }}, de {{ chaveInfo.ano_mes }} ({{ chaveInfo.uf }})</p>
					<p v-else-if="chaveInfo" class="mt-1 text-xs text-rose-600">{{ chaveInfo.motivo }}</p>
				</div>
				<div><label class="rotulo">Chegou em</label><input v-model="form.data" type="date" class="campo" /></div>
			</div>
			<template #rodape>
				<button class="btn-secundario" @click="retorno = null">Voltar</button>
				<button class="btn-primario" :disabled="ocupado || (chaveInfo && !chaveInfo.valida)" @click="registrar">Registrar retorno</button>
			</template>
		</Modal>
	</div>
</template>
