<script setup>
import { ArrowDownToLine, ArrowUpFromLine, Package, Plus, SlidersHorizontal } from "lucide-vue-next"
import { onMounted, reactive, ref, watch } from "vue"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import IconeEquipamento from "@/components/IconeEquipamento.vue"
import Modal from "@/components/Modal.vue"
import Vazio from "@/components/Vazio.vue"
import { relativo } from "@/format"
import { toast } from "@/store"

const d = ref(null)
const mov = ref(null) // { item, tipo, quantidade, para_usuario, observacao }
const novoItem = ref(null)
const pessoas = ref([])
const busca = ref("")
const salvando = ref(false)

onMounted(async () => (d.value = await api("inventario.estoque")))

function movimentar(item, tipo) {
	mov.value = reactive({ item: item.id, tipo, quantidade: tipo === "Ajuste" ? "" : 1, para_usuario: "", para_nome: "", observacao: "" })
	busca.value = ""
}
let atraso
watch(busca, (t) => {
	clearTimeout(atraso)
	atraso = setTimeout(async () => (pessoas.value = t.length >= 2 ? await api("buscar_pessoas", { texto: t }) : []), 250)
})
async function salvar(fn, params, msg) {
	salvando.value = true
	try {
		d.value = await api(fn, params, { post: true })
		toast(msg)
		mov.value = novoItem.value = null
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		salvando.value = false
	}
}
const ICONE = { Entrada: ArrowDownToLine, Saída: ArrowUpFromLine, Ajuste: SlidersHorizontal }
const COR_MOV = { Entrada: "text-emerald-600 dark:text-emerald-400", Saída: "text-rose-600 dark:text-rose-400", Ajuste: "text-amber-600 dark:text-amber-400" }
</script>

<template>
	<div class="space-y-5">
		<div class="flex flex-wrap items-end justify-between gap-4">
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-tinta">Estoque de TI</h1>
				<p class="mt-1 text-sm text-suave">Periféricos e consumíveis controlados por quantidade (mouse, teclado, cabos…). Compras entram sozinhas pela tela Compras de TI.</p>
			</div>
			<button class="btn-primario" @click="novoItem = { nome: '', minimo: 2, localizacao: '', quantidade_inicial: 0 }"><Plus class="size-4" /> Novo item</button>
		</div>

		<div v-if="!d" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"><div v-for="i in 3" :key="i" class="card p-5"><Esqueleto :linhas="3" /></div></div>
		<template v-else>
			<div v-if="!d.itens.length" class="card"><Vazio :icone="Package" titulo="Nenhum item de estoque" texto="Cadastre um item ou dê entrada a partir de Compras de TI." /></div>
			<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
				<article v-for="i in d.itens" :key="i.id" class="card p-5" :class="i.abaixo_minimo && 'border-rose-500/40'">
					<div class="flex items-start gap-3">
						<span class="grid size-10 shrink-0 place-items-center rounded-xl bg-marca-500/10 text-marca-600 dark:text-marca-300"><IconeEquipamento :nome="i.icone" class="size-5" /></span>
						<div class="min-w-0 flex-1">
							<p class="font-semibold text-tinta">{{ i.id }}</p>
							<p class="text-xs text-suave">{{ i.localizacao || "—" }}</p>
						</div>
					</div>
					<div class="mt-4 flex items-end justify-between">
						<p class="text-3xl font-semibold tabular-nums" :class="i.abaixo_minimo ? 'text-rose-600 dark:text-rose-400' : 'text-tinta'">{{ i.quantidade }}</p>
						<p class="text-xs" :class="i.abaixo_minimo ? 'font-medium text-rose-600 dark:text-rose-400' : 'text-suave'">{{ i.abaixo_minimo ? `abaixo do mínimo (${i.minimo}) — comprar` : `mínimo ${i.minimo}` }}</p>
					</div>
					<div class="mt-2 h-1.5 overflow-hidden rounded-full bg-realce">
						<div class="h-full rounded-full" :class="i.abaixo_minimo ? 'bg-rose-500' : 'bg-emerald-500'" :style="{ width: Math.min(100, (100 * i.quantidade) / Math.max(i.minimo * 3, 1)) + '%' }" />
					</div>
					<div class="mt-4 grid grid-cols-3 gap-2">
						<button class="btn-secundario px-2 text-xs" @click="movimentar(i, 'Saída')"><ArrowUpFromLine class="size-3.5" /> Entregar</button>
						<button class="btn-secundario px-2 text-xs" @click="movimentar(i, 'Entrada')"><ArrowDownToLine class="size-3.5" /> Entrada</button>
						<button class="btn-secundario px-2 text-xs" @click="movimentar(i, 'Ajuste')"><SlidersHorizontal class="size-3.5" /> Ajuste</button>
					</div>
				</article>
			</div>

			<section class="card overflow-hidden">
				<h2 class="px-5 pt-5 pb-3 font-semibold text-tinta">Últimas movimentações</h2>
				<ul class="divide-y divide-borda border-t border-borda">
					<li v-for="m in d.movimentos" :key="m.id" class="flex items-center gap-3 px-5 py-3 text-sm">
						<component :is="ICONE[m.tipo]" class="size-4 shrink-0" :class="COR_MOV[m.tipo]" />
						<div class="min-w-0 flex-1">
							<p class="truncate text-tinta"><b class="font-medium">{{ m.tipo === "Saída" ? "-" : m.tipo === "Entrada" ? "+" : "±" }}{{ m.quantidade }}</b> {{ m.item }}<span v-if="m.para_nome" class="text-suave"> → {{ m.para_nome }}</span></p>
							<p class="truncate text-xs text-suave">{{ m.observacao || m.tipo }} · {{ m.por_nome }}</p>
						</div>
						<span class="text-xs text-suave">saldo {{ m.saldo_apos }}</span>
						<span class="w-20 text-right text-xs text-suave">{{ relativo(m.data) }}</span>
					</li>
				</ul>
			</section>
		</template>

		<Modal v-if="mov" :titulo="{ Saída: 'Entregar item', Entrada: 'Entrada no estoque', Ajuste: 'Ajuste de inventário' }[mov.tipo]" :subtitulo="mov.item" @fechar="mov = null">
			<form id="form-mov" class="space-y-4" @submit.prevent="salvar('inventario.movimentar_estoque', { ...mov }, 'Estoque atualizado.')">
				<div>
					<label class="rotulo">{{ mov.tipo === "Ajuste" ? "Diferença encontrada na contagem (ex.: -2 ou 3)" : "Quantidade" }}</label>
					<input v-model="mov.quantidade" type="number" class="campo" required />
				</div>
				<div v-if="mov.tipo === 'Saída'" class="relative">
					<label class="rotulo">Para quem</label>
					<div v-if="mov.para_usuario" class="flex items-center gap-2 rounded-xl border border-borda bg-realce px-3 py-2 text-sm">
						<span class="flex-1 text-tinta">{{ mov.para_nome }}</span><button type="button" class="text-xs text-suave" @click="(mov.para_usuario = ''), (mov.para_nome = '')">trocar</button>
					</div>
					<template v-else>
						<input v-model="busca" class="campo" placeholder="Buscar pessoa (opcional)…" />
						<ul v-if="pessoas.length" class="absolute z-10 mt-1 w-full overflow-hidden rounded-xl border border-borda bg-elevada shadow-pop">
							<li v-for="p in pessoas" :key="p.id"><button type="button" class="w-full px-3 py-2 text-left text-sm hover:bg-realce" @click="(mov.para_usuario = p.id), (mov.para_nome = p.nome), (busca = ''), (pessoas = [])">{{ p.nome }}</button></li>
						</ul>
					</template>
				</div>
				<div><label class="rotulo">Observação</label><input v-model="mov.observacao" class="campo" placeholder="Ex.: troca por desgaste, chamado CH-00123" /></div>
			</form>
			<template #rodape>
				<button class="btn-secundario" @click="mov = null">Cancelar</button>
				<button class="btn-primario" form="form-mov" type="submit" :disabled="salvando">Confirmar</button>
			</template>
		</Modal>

		<Modal v-if="novoItem" titulo="Novo item de estoque" @fechar="novoItem = null">
			<form id="form-item" class="space-y-4" @submit.prevent="salvar('inventario.salvar_item_estoque', { ...novoItem }, 'Item cadastrado.')">
				<div><label class="rotulo">Item *</label><input v-model="novoItem.nome" class="campo" required placeholder="Ex.: Cabo HDMI 2 m" /></div>
				<div class="grid grid-cols-3 gap-3">
					<div><label class="rotulo">Quantidade atual</label><input v-model="novoItem.quantidade_inicial" type="number" min="0" class="campo" /></div>
					<div><label class="rotulo">Mínimo</label><input v-model="novoItem.minimo" type="number" min="0" class="campo" /></div>
					<div><label class="rotulo">Onde fica</label><input v-model="novoItem.localizacao" class="campo" /></div>
				</div>
			</form>
			<template #rodape>
				<button class="btn-secundario" @click="novoItem = null">Cancelar</button>
				<button class="btn-primario" form="form-item" type="submit" :disabled="salvando">Cadastrar</button>
			</template>
		</Modal>
	</div>
</template>
