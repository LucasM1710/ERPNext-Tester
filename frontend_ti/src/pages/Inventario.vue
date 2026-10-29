<script setup>
import { AlertTriangle, Download, Plus, Search, Server } from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { api } from "@/api"
import Avatar from "@/components/Avatar.vue"
import Esqueleto from "@/components/Esqueleto.vue"
import FormEquipamentoTI from "@/components/FormEquipamentoTI.vue"
import IconeEquipamento from "@/components/IconeEquipamento.vue"
import Vazio from "@/components/Vazio.vue"
import { data } from "@/format"

const route = useRoute()
const router = useRouter()
const lista = ref(null)
const tipos = ref([])
const busca = ref("")
const grupo = ref(route.query.grupo || "")
const status = ref(route.query.status || "")
const soAlertas = ref(route.query.alertas === "1")
const novo = ref(false)

const GRUPOS = ["Computador", "Impressora", "Celular", "Rede e Servidores", "Periférico", "Outro"]
const STATUS = ["Em Uso", "Em Estoque", "Em Manutenção", "Emprestado", "Descartado", "Extraviado"]

async function carregar() {
	lista.value = null
	lista.value = await api("inventario.inventario", { grupo: grupo.value, status: status.value })
}
onMounted(async () => {
	tipos.value = await api("inventario.tipos")
	carregar()
})
watch([grupo, status], carregar)

const filtrados = computed(() => {
	const t = busca.value.trim().toLowerCase()
	return (lista.value || [])
		.filter((e) => !soAlertas.value || e.alertas.length)
		.filter((e) => !t || [e.nome, e.modelo, e.responsavel_nome, e.departamento, e.numero_serie, e.patrimonio, e.resumo].some((v) => v?.toLowerCase().includes(t)))
})
const contagemGrupo = computed(() => Object.fromEntries(GRUPOS.map((g) => [g, (lista.value || []).filter((e) => e.grupo === g).length])))
const reais = (v) => (v ? v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }) : "—")
const COR_STATUS = {
	"Em Uso": "text-emerald-600 dark:text-emerald-400",
	"Em Estoque": "text-sky-600 dark:text-sky-400",
	"Em Manutenção": "text-amber-600 dark:text-amber-400",
	Emprestado: "text-violet-600 dark:text-violet-400",
}

function exportar() {
	const col = ["Nome", "Tipo", "Status", "Modelo", "Configuração", "Responsável", "Departamento", "Compra", "Valor", "Garantia", "Fim vida útil", "Chamados", "Custo total", "Alertas"]
	const linhas = filtrados.value.map((e) => [e.nome, e.tipo, e.status, e.modelo, e.resumo, e.responsavel_nome, e.departamento, data(e.data_compra), e.valor_compra, data(e.garantia_ate), data(e.fim_vida_util), e.qtd_chamados, e.custo_total, e.alertas.join(" / ")])
	const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`
	const blob = new Blob(["﻿" + [col, ...linhas].map((l) => l.map(esc).join(";")).join("\n")], { type: "text/csv;charset=utf-8" })
	const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: "inventario-ti.csv" })
	a.click()
}
</script>

<template>
	<div class="space-y-5">
		<div class="flex flex-wrap items-end justify-between gap-4">
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-tinta">Inventário</h1>
				<p class="mt-1 text-sm text-suave">Todos os equipamentos da empresa: com quem estão, configuração, garantia e custo.</p>
			</div>
			<div class="flex gap-2">
				<button class="btn-secundario" :disabled="!filtrados.length" @click="exportar"><Download class="size-4" /> Exportar</button>
				<button class="btn-primario" @click="novo = true"><Plus class="size-4" /> Novo equipamento</button>
			</div>
		</div>

		<div class="flex flex-wrap gap-2">
			<button class="chip" :class="!grupo ? 'border-marca-500 bg-marca-600 text-white' : 'border-borda bg-superficie text-texto hover:bg-realce'" @click="grupo = ''">
				Todos <span class="opacity-70 tabular-nums">{{ lista?.length ?? "…" }}</span>
			</button>
			<button
				v-for="g in GRUPOS"
				:key="g"
				class="chip"
				:class="grupo === g ? 'border-marca-500 bg-marca-600 text-white' : 'border-borda bg-superficie text-texto hover:bg-realce'"
				@click="grupo = grupo === g ? '' : g"
			>
				{{ g }} <span v-if="!grupo" class="opacity-70 tabular-nums">{{ contagemGrupo[g] }}</span>
			</button>
		</div>

		<div class="card overflow-hidden">
			<div class="flex flex-wrap items-center gap-3 border-b border-borda p-3">
				<div class="relative min-w-[220px] flex-1">
					<Search class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-suave" />
					<input v-model="busca" class="campo pl-9" placeholder="Nome, modelo, pessoa, departamento, série, patrimônio…" />
				</div>
				<select v-model="status" class="campo w-auto">
					<option value="">Ativos (sem descartados)</option>
					<option v-for="s in STATUS" :key="s">{{ s }}</option>
				</select>
				<label class="flex items-center gap-2 px-1 text-sm text-texto"><input v-model="soAlertas" type="checkbox" class="accent-marca-600" /> Só com alerta</label>
			</div>

			<div v-if="!lista" class="p-5"><Esqueleto :linhas="8" classe="h-10" /></div>
			<Vazio v-else-if="!filtrados.length" :icone="Server" titulo="Nenhum equipamento" texto="Cadastre manualmente ou a partir de Compras de TI." />
			<div v-else class="overflow-x-auto">
				<table class="w-full min-w-[920px]">
					<thead class="border-b border-borda bg-realce/50">
						<tr>
							<th class="th">Equipamento</th>
							<th class="th">Configuração</th>
							<th class="th">Com quem está</th>
							<th class="th">Compra</th>
							<th class="th text-right">Custo total</th>
							<th class="th">Alertas</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-borda">
						<tr v-for="e in filtrados" :key="e.id" class="cursor-pointer transition hover:bg-realce" @click="router.push(`/inventario/${e.id}`)">
							<td class="td">
								<div class="flex items-center gap-3">
									<span class="grid size-9 shrink-0 place-items-center rounded-xl bg-marca-500/10 text-marca-600 dark:text-marca-300"><IconeEquipamento :nome="e.icone" class="size-4" /></span>
									<div class="min-w-0">
										<p class="font-semibold text-tinta">{{ e.nome }}</p>
										<p class="max-w-56 truncate text-xs text-suave">{{ e.modelo || e.tipo }} · <span :class="COR_STATUS[e.status]">{{ e.status }}</span></p>
									</div>
								</div>
							</td>
							<td class="td max-w-56 truncate text-texto">{{ e.resumo || "—" }}</td>
							<td class="td">
								<div v-if="e.responsavel_nome" class="flex items-center gap-2">
									<Avatar :nome="e.responsavel_nome" tamanho="size-6" />
									<div class="min-w-0"><p class="truncate text-tinta">{{ e.responsavel_nome }}</p><p class="text-xs text-suave">{{ e.departamento }}</p></div>
								</div>
								<span v-else class="text-suave">{{ e.localizacao || e.departamento || "—" }}</span>
							</td>
							<td class="td">
								<p class="text-texto">{{ data(e.data_compra) }}</p>
								<p v-if="e.idade_anos !== null" class="text-xs text-suave">{{ String(e.idade_anos).replace(".", ",") }} ano(s)</p>
							</td>
							<td class="td text-right text-tinta tabular-nums">{{ reais(e.custo_total) }}</td>
							<td class="td">
								<div class="flex flex-wrap gap-1">
									<span v-for="a in e.alertas" :key="a" class="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium" :class="a.includes('vencida') || a.includes('Fora') ? 'bg-rose-500/12 text-rose-700 dark:text-rose-300' : 'bg-amber-500/14 text-amber-700 dark:text-amber-300'">
										<AlertTriangle class="size-3" /> {{ a }}
									</span>
								</div>
							</td>
						</tr>
					</tbody>
				</table>
			</div>
			<p v-if="lista" class="border-t border-borda px-4 py-3 text-xs text-suave">{{ filtrados.length }} de {{ lista.length }} equipamentos</p>
		</div>

		<FormEquipamentoTI v-if="novo" @fechar="novo = false" @salvo="(e) => router.push(`/inventario/${e.id}`)" />
	</div>
</template>
