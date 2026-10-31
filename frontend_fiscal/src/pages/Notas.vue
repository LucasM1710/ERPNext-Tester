<script setup>
import { FileText, Search } from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import Vazio from "@/components/Vazio.vue"
import { dataHora, moeda } from "@/format"

const notas = ref(null)
const tipo = ref("")
const status = ref("")
const busca = ref("")
const periodo = ref("")

const total = computed(() => (notas.value || []).filter((n) => n.status === "Autorizada").reduce((s, n) => s + n.valor_total, 0))
const meses = computed(() => {
	const r = []
	const d = new Date()
	for (let i = 0; i < 12; i++) {
		const m = new Date(d.getFullYear(), d.getMonth() - i, 1)
		r.push({ v: m.toLocaleDateString("sv-SE").slice(0, 7), r: m.toLocaleDateString("pt-BR", { month: "long", year: "numeric" }) })
	}
	return r
})

let espera
async function carregar() {
	notas.value = await api("notas", { tipo: tipo.value, status: status.value, busca: busca.value, periodo: periodo.value })
}
watch([tipo, status, periodo], carregar)
watch(busca, () => {
	clearTimeout(espera)
	espera = setTimeout(carregar, 300)
})
onMounted(carregar)
</script>

<template>
	<div class="space-y-5">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight text-tinta">Notas emitidas</h1>
			<p class="mt-1 text-sm text-suave">Todas as NFS-e e NF-e: vendas, serviços, remessas e retornos. Clique numa nota para ver o PDF, o XML ou cancelar.</p>
		</div>

		<div class="flex flex-wrap items-center gap-2">
			<button v-for="[v, r] in [['', 'Todas'], ['NFS-e', 'NFS-e (serviços)'], ['NF-e', 'NF-e (produtos e remessas)']]" :key="v" class="chip"
				:class="tipo === v ? 'border-marca-500 bg-marca-500/10 text-marca-700 dark:text-marca-300' : 'border-borda text-suave hover:bg-realce'" @click="tipo = v">{{ r }}</button>
			<select v-model="status" class="campo w-auto py-1.5">
				<option value="">Qualquer situação</option>
				<option>Autorizada</option>
				<option>Rejeitada</option>
				<option>Cancelada</option>
			</select>
			<select v-model="periodo" class="campo w-auto py-1.5 capitalize">
				<option value="">Todo o período</option>
				<option v-for="m in meses" :key="m.v" :value="m.v">{{ m.r }}</option>
			</select>
			<div class="relative ml-auto w-full sm:w-64">
				<Search class="absolute top-2.5 left-3 size-4 text-suave" />
				<input v-model="busca" class="campo pl-9" placeholder="Cliente, número, fatura ou CNPJ" />
			</div>
		</div>

		<div class="card overflow-hidden">
			<div v-if="!notas" class="p-5"><Esqueleto :linhas="6" /></div>
			<Vazio v-else-if="!notas.length" :icone="FileText" titulo="Nenhuma nota encontrada" texto="Mude os filtros ou emita a primeira nota em Para emitir." />
			<table v-else class="w-full">
				<thead class="border-b border-borda bg-realce/50">
					<tr><th class="th">Nota</th><th class="th">Destinatário</th><th class="th hidden md:table-cell">Operação</th><th class="th hidden sm:table-cell">Emissão</th><th class="th text-right">Valor</th><th class="th">Situação</th></tr>
				</thead>
				<tbody class="divide-y divide-borda">
					<tr v-for="n in notas" :key="n.id" class="cursor-pointer hover:bg-realce/60" @click="$router.push(`/notas/${n.id}`)">
						<td class="td whitespace-nowrap"><Etiqueta :valor="n.tipo_documento" :ponto="false" /> <span class="ml-1 font-semibold text-tinta">{{ n.numero ? `nº ${n.numero}` : "—" }}</span></td>
						<td class="td"><p class="max-w-56 truncate font-medium text-tinta">{{ n.nome_parte }}</p><p class="text-xs text-suave">{{ n.fatura || n.documento_parte }}</p></td>
						<td class="td hidden text-suave md:table-cell">{{ n.natureza }}</td>
						<td class="td hidden whitespace-nowrap text-suave sm:table-cell">{{ dataHora(n.data_emissao || n.creation) }}</td>
						<td class="td text-right font-medium text-tinta tabular-nums">{{ moeda(n.valor_total) }}</td>
						<td class="td"><Etiqueta :valor="n.status" /></td>
					</tr>
				</tbody>
				<tfoot class="border-t border-borda bg-realce/40">
					<tr><td class="td text-xs text-suave" colspan="4">{{ notas.length }} nota(s)</td><td class="td text-right text-sm font-semibold text-tinta tabular-nums">{{ moeda(total) }}</td><td class="td text-xs text-suave">autorizadas</td></tr>
				</tfoot>
			</table>
		</div>
	</div>
</template>
