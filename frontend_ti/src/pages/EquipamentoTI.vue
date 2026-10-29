<script setup>
import { AlertTriangle, ArrowLeft, ArrowRight, FileText, Pencil, Receipt, Ticket, UserRound, Wrench } from "lucide-vue-next"
import { computed, onMounted, reactive, ref } from "vue"
import { api } from "@/api"
import Avatar from "@/components/Avatar.vue"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import FormEquipamentoTI from "@/components/FormEquipamentoTI.vue"
import IconeEquipamento from "@/components/IconeEquipamento.vue"
import Modal from "@/components/Modal.vue"
import { data, dataHora } from "@/format"
import { toast } from "@/store"

const props = defineProps({ id: String })
const e = ref(null)
const erro = ref(null)
const editar = ref(false)
const manut = ref(null)
const salvando = ref(false)

async function carregar() {
	try {
		e.value = await api("inventario.equipamento", { id: props.id })
	} catch (err) {
		erro.value = err.message
	}
}
onMounted(carregar)

const reais = (v) => (v || v === 0 ? Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "—")
const TIPOS_MANUT = ["Upgrade", "Manutenção Corretiva", "Manutenção Preventiva", "Formatação / Reinstalação", "Troca de Peça", "Outro"]
const COMPONENTES = ["Memória RAM", "Armazenamento", "Processador", "Sistema Operacional", "Outro"]
const CAMPO = { "Memória RAM": "memoria_ram", Armazenamento: "armazenamento", Processador: "processador", "Sistema Operacional": "sistema_operacional" }

function abrirManut() {
	manut.value = reactive({ tipo: "Upgrade", componente: "Memória RAM", valor_novo: "", descricao: "", custo: "", fornecedor: "", data: new Date().toISOString().slice(0, 10) })
}
const mostraComponente = computed(() => manut.value && ["Upgrade", "Troca de Peça", "Formatação / Reinstalação"].includes(manut.value.tipo))
async function salvarManut() {
	salvando.value = true
	try {
		const dados = { ...manut.value }
		if (!mostraComponente.value) dados.componente = ""
		e.value = await api("inventario.registrar_manutencao", { equipamento_id: props.id, dados }, { post: true })
		toast(dados.componente && CAMPO[dados.componente] ? `${dados.componente} atualizado(a) para ${dados.valor_novo}.` : "Registro salvo.")
		manut.value = null
	} catch (err) {
		toast(err.message, "erro")
	} finally {
		salvando.value = false
	}
}

// linha do tempo única: compra, manutenções/upgrades, chamados e trocas de responsável
const linhaDoTempo = computed(() => {
	if (!e.value) return []
	const itens = []
	if (e.value.data_compra) itens.push({ data: e.value.data_compra, tipo: "compra", titulo: "Compra", texto: `${e.value.fornecedor || ""} · ${reais(e.value.valor_compra)}`, icone: Receipt })
	for (const m of e.value.manutencoes)
		itens.push({
			data: m.data,
			tipo: "manut",
			titulo: m.tipo + (m.componente && m.valor_novo ? `: ${m.componente}` : ""),
			antes: m.valor_anterior,
			depois: m.valor_novo,
			texto: m.descricao,
			extra: [m.fornecedor, m.custo ? reais(m.custo) : null, m.executado_por_nome].filter(Boolean).join(" · "),
			icone: Wrench,
		})
	for (const c of e.value.chamados) itens.push({ data: c.aberto_em, tipo: "chamado", titulo: `Chamado ${c.id}`, texto: c.assunto, extra: `${c.nome_solicitante} · ${c.status}`, link: `/chamados/${c.id}`, icone: Ticket })
	for (const h of e.value.historico_responsaveis) itens.push({ data: h.data, tipo: "resp", titulo: `Entregue a ${h.nome}`, texto: h.departamento, extra: h.por ? `por ${h.por}` : "", icone: UserRound })
	return itens.sort((a, b) => String(b.data).localeCompare(String(a.data)))
})
const COR_TL = { compra: "bg-sky-500", manut: "bg-amber-500", chamado: "bg-marca-500", resp: "bg-emerald-500" }
</script>

<template>
	<div class="space-y-5">
		<RouterLink to="/inventario" class="inline-flex items-center gap-1.5 text-sm text-suave hover:text-tinta"><ArrowLeft class="size-4" /> Inventário</RouterLink>
		<div v-if="erro" class="card p-6 text-sm text-rose-600">{{ erro }}</div>
		<div v-else-if="!e" class="card p-6"><Esqueleto :linhas="8" /></div>

		<template v-else>
			<div class="card flex flex-wrap items-start gap-4 p-5">
				<span class="grid size-14 shrink-0 place-items-center rounded-2xl bg-marca-500/10 text-marca-600 dark:text-marca-300"><IconeEquipamento :nome="e.icone" class="size-7" /></span>
				<div class="min-w-0 flex-1">
					<p class="text-xs text-suave">{{ e.tipo }} · {{ e.grupo }}</p>
					<h1 class="text-2xl font-semibold tracking-tight text-tinta">{{ e.nome }}</h1>
					<p class="text-sm text-texto">{{ [e.marca, e.modelo].filter(Boolean).join(" · ") }}</p>
					<div class="mt-2 flex flex-wrap gap-1.5">
						<Etiqueta :valor="e.status" />
						<span v-for="a in e.alertas" :key="a" class="inline-flex items-center gap-1 rounded-full bg-rose-500/12 px-2.5 py-0.5 text-xs font-medium text-rose-700 dark:text-rose-300"><AlertTriangle class="size-3" /> {{ a }}</span>
					</div>
				</div>
				<div class="flex gap-2">
					<button class="btn-secundario" @click="editar = true"><Pencil class="size-4" /> Editar</button>
					<button class="btn-primario" @click="abrirManut"><Wrench class="size-4" /> Manutenção / upgrade</button>
				</div>
			</div>

			<div class="grid gap-5 lg:grid-cols-3">
				<div class="space-y-5">
					<section class="card p-5">
						<p class="text-xs font-semibold tracking-wider text-suave uppercase">Com quem está</p>
						<div v-if="e.responsavel_nome" class="mt-3 flex items-center gap-3">
							<Avatar :nome="e.responsavel_nome" />
							<div><p class="font-medium text-tinta">{{ e.responsavel_nome }}</p><p class="text-xs text-suave">{{ e.departamento }}</p></div>
						</div>
						<p v-else class="mt-3 text-sm text-texto">{{ e.localizacao || "Sem responsável" }}</p>
						<p v-if="e.responsavel_nome && e.localizacao" class="mt-2 text-xs text-suave">Local: {{ e.localizacao }}</p>
						<p class="mt-2 text-xs" :class="e.tem_termo ? 'text-emerald-600 dark:text-emerald-400' : 'text-suave'">
							{{ e.tem_termo ? "Termo de responsabilidade anexado" : e.responsavel ? "Sem termo de responsabilidade anexado" : "" }}
						</p>
					</section>

					<section class="card p-5">
						<p class="text-xs font-semibold tracking-wider text-suave uppercase">Configuração</p>
						<dl class="mt-3 space-y-2 text-sm">
							<template v-for="[k, v] in [
								['Processador', e.processador], ['Memória', e.memoria_ram], ['Armazenamento', e.armazenamento], ['Sistema', e.sistema_operacional],
								['IP', e.endereco_ip], ['MAC', e.endereco_mac], ['Firmware', e.firmware], ['IMEI', e.imei], ['Linha', e.numero_linha], ['Operadora', e.operadora],
								['Nº de série', e.numero_serie], ['Patrimônio', e.patrimonio],
							]" :key="k">
								<div v-if="v" class="flex justify-between gap-3"><dt class="text-suave">{{ k }}</dt><dd class="text-right font-medium text-tinta">{{ v }}</dd></div>
							</template>
						</dl>
						<p v-if="e.especificacoes" class="mt-3 rounded-lg bg-realce p-2.5 text-xs text-texto">{{ e.especificacoes }}</p>
					</section>

					<section class="card p-5">
						<p class="text-xs font-semibold tracking-wider text-suave uppercase">Custos e ciclo de vida</p>
						<dl class="mt-3 space-y-2 text-sm">
							<div class="flex justify-between"><dt class="text-suave">Compra</dt><dd class="text-tinta tabular-nums">{{ reais(e.valor_compra) }}</dd></div>
							<div class="flex justify-between"><dt class="text-suave">Manutenções ({{ e.qtd_manutencoes }})</dt><dd class="text-tinta tabular-nums">{{ reais(e.custo_manutencoes) }}</dd></div>
							<div class="flex justify-between border-t border-borda pt-2 font-semibold"><dt class="text-tinta">Custo total</dt><dd class="text-tinta tabular-nums">{{ reais(e.custo_total) }}</dd></div>
							<div class="flex justify-between pt-2"><dt class="text-suave">Chamados</dt><dd class="text-tinta">{{ e.qtd_chamados }}</dd></div>
							<div class="flex justify-between"><dt class="text-suave">Comprado em</dt><dd class="text-tinta">{{ data(e.data_compra) }}<span v-if="e.idade_anos !== null" class="text-suave"> ({{ String(e.idade_anos).replace(".", ",") }} anos)</span></dd></div>
							<div class="flex justify-between"><dt class="text-suave">Garantia até</dt><dd class="text-tinta">{{ data(e.garantia_ate) }}</dd></div>
							<div class="flex justify-between"><dt class="text-suave">Fim da vida útil</dt><dd class="text-tinta">{{ data(e.fim_vida_util) }}</dd></div>
						</dl>
						<a v-if="e.nota_compra" :href="`/app/purchase-invoice/${e.nota_compra}`" target="_blank" class="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-marca-600 dark:text-marca-300">
							<FileText class="size-3.5" /> Nota de compra {{ e.nota_compra }}
						</a>
						<p v-if="e.custo_manutencoes > 0.5 * e.valor_compra" class="mt-3 rounded-lg bg-amber-500/10 p-2.5 text-xs text-amber-800 dark:text-amber-300">
							As manutenções já passam de 50% do valor de compra: avalie trocar em vez de consertar.
						</p>
					</section>
				</div>

				<section class="card p-5 lg:col-span-2">
					<p class="text-xs font-semibold tracking-wider text-suave uppercase">Histórico do equipamento</p>
					<ol v-if="linhaDoTempo.length" class="mt-4">
						<li v-for="(t, i) in linhaDoTempo" :key="i" class="relative flex gap-4 pb-5 last:pb-0">
							<span v-if="i < linhaDoTempo.length - 1" class="absolute top-8 left-4 h-full w-px bg-borda" />
							<span class="relative z-10 grid size-8 shrink-0 place-items-center rounded-full text-white ring-4 ring-superficie" :class="COR_TL[t.tipo]"><component :is="t.icone" class="size-4" /></span>
							<component :is="t.link ? 'RouterLink' : 'div'" :to="t.link" class="min-w-0 flex-1 rounded-xl border border-borda p-3" :class="t.link && 'transition hover:bg-realce'">
								<div class="flex flex-wrap items-baseline justify-between gap-2">
									<p class="text-sm font-medium text-tinta">{{ t.titulo }}</p>
									<p class="text-xs text-suave">{{ String(t.data).length > 10 ? dataHora(t.data) : data(t.data) }}</p>
								</div>
								<p v-if="t.antes || t.depois" class="mt-1 flex items-center gap-2 text-sm">
									<span class="rounded bg-realce px-1.5 text-suave line-through">{{ t.antes || "—" }}</span><ArrowRight class="size-3.5 text-suave" /><span class="rounded bg-emerald-500/12 px-1.5 font-medium text-emerald-700 dark:text-emerald-300">{{ t.depois }}</span>
								</p>
								<p v-if="t.texto" class="mt-1 text-sm text-texto">{{ t.texto }}</p>
								<p v-if="t.extra" class="mt-0.5 text-xs text-suave">{{ t.extra }}</p>
							</component>
						</li>
					</ol>
					<p v-else class="mt-4 text-sm text-suave">Sem histórico ainda.</p>
				</section>
			</div>
		</template>

		<FormEquipamentoTI v-if="editar" :equipamento="e" @fechar="editar = false" @salvo="(r) => ((e = r), (editar = false))" />
		<Modal v-if="manut" titulo="Registrar manutenção / upgrade" :subtitulo="e.nome" largura="max-w-xl" @fechar="manut = null">
			<form id="form-manut" class="space-y-4" @submit.prevent="salvarManut">
				<div class="grid gap-4 sm:grid-cols-2">
					<div><label class="rotulo">Tipo</label><select v-model="manut.tipo" class="campo"><option v-for="t in TIPOS_MANUT" :key="t">{{ t }}</option></select></div>
					<div><label class="rotulo">Data</label><input v-model="manut.data" type="date" class="campo" /></div>
				</div>
				<div v-if="mostraComponente" class="grid gap-4 rounded-xl bg-realce p-3 sm:grid-cols-2">
					<div><label class="rotulo">Componente</label><select v-model="manut.componente" class="campo"><option value="">— nenhum —</option><option v-for="c in COMPONENTES" :key="c">{{ c }}</option></select></div>
					<div v-if="manut.componente">
						<label class="rotulo">Como ficou{{ CAMPO[manut.componente] && e[CAMPO[manut.componente]] ? ` (hoje: ${e[CAMPO[manut.componente]]})` : "" }}</label>
						<input v-model="manut.valor_novo" class="campo" :required="!!CAMPO[manut.componente]" placeholder="Ex.: 16 GB" />
					</div>
					<p v-if="CAMPO[manut.componente]" class="text-xs text-suave sm:col-span-2">O cadastro do equipamento será atualizado automaticamente e o valor anterior fica no histórico.</p>
				</div>
				<div><label class="rotulo">O que foi feito *</label><textarea v-model="manut.descricao" rows="3" class="campo" required /></div>
				<div class="grid gap-4 sm:grid-cols-2">
					<div><label class="rotulo">Custo (R$)</label><input v-model="manut.custo" type="number" step="0.01" class="campo" /></div>
					<div><label class="rotulo">Fornecedor / assistência</label><input v-model="manut.fornecedor" class="campo" /></div>
				</div>
			</form>
			<template #rodape>
				<button class="btn-secundario" @click="manut = null">Cancelar</button>
				<button class="btn-primario" form="form-manut" type="submit" :disabled="salvando">{{ salvando ? "Salvando…" : "Registrar" }}</button>
			</template>
		</Modal>
	</div>
</template>
