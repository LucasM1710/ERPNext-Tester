<script setup>
import { ScrollText } from "lucide-vue-next"
import { computed, onMounted, reactive, ref, watch } from "vue"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import Modal from "@/components/Modal.vue"
import { dataHora } from "@/format"

// Auditoria do portal: acessos, downloads de certificado e alterações.
const filtros = reactive({ de: "", ate: "", usuario: "", acao: "" })
const r = ref(null)
const detalhe = ref(null)

async function carregar() {
	r.value = await api("consulta.logs", { filtros: { ...filtros } })
}
onMounted(carregar)
watch(filtros, carregar)

const usuarios = computed(() => {
	const mapa = new Map((r.value?.logs || []).map((l) => [l.usuario, l.usuario_nome]))
	return [...mapa.entries()].sort((a, b) => a[1].localeCompare(b[1]))
})

function resumo(v) {
	if (!v) return "—"
	try {
		const o = JSON.parse(v)
		return Object.entries(o)
			.map(([k, x]) => `${k}: ${Array.isArray(x) ? x.join(", ") : x ?? "—"}`)
			.join(" · ")
	} catch {
		return v
	}
}
</script>

<template>
	<div class="space-y-5">
		<div class="relative overflow-hidden rounded-[28px] border border-slate-200 bg-white px-6 py-5 shadow-card">
			<div class="absolute top-1/2 -left-8 size-24 -translate-y-1/2 rounded-full bg-brand-100/60" />
			<div class="absolute -top-4 -right-4 size-20 rounded-full bg-cyan-100/70" />
			<span class="relative inline-flex items-center gap-1.5 rounded-full border border-brand-100 bg-brand-50 px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-brand-700 uppercase">
				<ScrollText class="size-3" /> Auditoria
			</span>
			<h1 class="relative mt-1.5 text-3xl font-semibold tracking-tight text-slate-900">Logs de auditoria</h1>
			<p class="relative mt-1 text-sm text-slate-500">Quem acessou o portal, baixou certificados ou alterou distritos, usuários e equipamentos.</p>
		</div>

		<div class="card grid gap-3 p-4 md:grid-cols-4">
			<div><label class="label">De</label><input v-model="filtros.de" type="date" class="input" /></div>
			<div><label class="label">Até</label><input v-model="filtros.ate" type="date" class="input" /></div>
			<div>
				<label class="label">Usuário</label>
				<select v-model="filtros.usuario" class="input">
					<option value="">Todos os usuários</option>
					<option v-for="[id, nome] in usuarios" :key="id" :value="id">{{ nome }}</option>
				</select>
			</div>
			<div>
				<label class="label">Ação</label>
				<select v-model="filtros.acao" class="input">
					<option value="">Todas as ações</option>
					<option v-for="a in r?.acoes || []" :key="a" :value="a">{{ a }}</option>
				</select>
			</div>
		</div>

		<div v-if="!r" class="card p-5"><Esqueleto :linhas="8" /></div>
		<section v-else class="card overflow-hidden">
			<div class="overflow-x-auto">
				<table class="w-full min-w-[960px] text-[13px]">
					<thead>
						<tr class="bg-brand-700 text-left text-[11px] tracking-wider text-white uppercase">
							<th class="px-3 py-2.5 font-semibold">Data</th>
							<th class="px-3 py-2.5 font-semibold">Usuário</th>
							<th class="px-3 py-2.5 font-semibold">Cliente</th>
							<th class="px-3 py-2.5 font-semibold">Ação</th>
							<th class="px-3 py-2.5 font-semibold">Registro</th>
							<th class="px-3 py-2.5 font-semibold">Valor anterior</th>
							<th class="px-3 py-2.5 font-semibold">Valor novo</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-slate-100">
						<tr v-if="!r.logs.length"><td colspan="7" class="px-3 py-8 text-center text-slate-500">Nenhum log encontrado para o período/filtro informado.</td></tr>
						<tr v-for="l in r.logs" :key="l.name" class="cursor-pointer hover:bg-slate-50/80" @click="detalhe = l">
							<td class="px-3 py-2 whitespace-nowrap">{{ dataHora(l.creation) }}</td>
							<td class="px-3 py-2 whitespace-nowrap">{{ l.usuario_nome }}</td>
							<td class="px-3 py-2 whitespace-nowrap">{{ l.cliente_nome || "—" }}</td>
							<td class="px-3 py-2 font-medium whitespace-nowrap text-slate-900">{{ l.acao }}</td>
							<td class="px-3 py-2 whitespace-nowrap">{{ l.referencia || "—" }}</td>
							<td class="max-w-[260px] truncate px-3 py-2 text-slate-500">{{ resumo(l.valor_anterior) }}</td>
							<td class="max-w-[260px] truncate px-3 py-2 text-slate-500">{{ resumo(l.valor_novo) }}</td>
						</tr>
					</tbody>
				</table>
			</div>
			<p class="border-t border-slate-100 px-4 py-2 text-xs text-slate-500">Clique numa linha para ver os valores completos. Mostra os 500 registros mais recentes do filtro.</p>
		</section>

		<Modal v-if="detalhe" :titulo="detalhe.acao" :subtitulo="`${detalhe.usuario_nome} · ${dataHora(detalhe.creation)}`" largura="max-w-2xl" @fechar="detalhe = null">
			<div class="grid gap-4 sm:grid-cols-2">
				<div>
					<p class="label">Valor anterior</p>
					<pre class="max-h-80 overflow-auto rounded-xl bg-slate-50 p-3 text-xs whitespace-pre-wrap text-slate-700">{{ detalhe.valor_anterior || "—" }}</pre>
				</div>
				<div>
					<p class="label">Valor novo</p>
					<pre class="max-h-80 overflow-auto rounded-xl bg-slate-50 p-3 text-xs whitespace-pre-wrap text-slate-700">{{ detalhe.valor_novo || "—" }}</pre>
				</div>
			</div>
		</Modal>
	</div>
</template>
