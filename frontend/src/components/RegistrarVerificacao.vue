<script setup>
import { CircleCheck, CircleX, Plus, Trash2 } from "lucide-vue-next"
import { computed, reactive, ref } from "vue"
import { api } from "@/api"
import Modal from "@/components/Modal.vue"
import { numero } from "@/format"
import { toast } from "@/store"

// Verificação intermediária: o cliente compara o instrumento com uma referência própria.
const props = defineProps({ equipamento: { type: Object, required: true } })
const emit = defineEmits(["fechar", "salvo"])

const tolerancia = computed(() => props.equipamento.tolerancia_verificacao || props.equipamento.tolerancia || 0)
const f = reactive({ referencia: "", observacao: "", pontos: [{ valor_referencia: "", valor_lido: "" }] })
const salvando = ref(false)

function avaliar(p) {
	if (p.valor_referencia === "" || p.valor_lido === "") return null
	const desvio = Number(p.valor_lido) - Number(p.valor_referencia)
	return { desvio, conforme: !tolerancia.value || Math.abs(desvio) <= tolerancia.value }
}
const avaliados = computed(() => f.pontos.map(avaliar))
const preenchidos = computed(() => avaliados.value.filter(Boolean))
const resultado = computed(() => (preenchidos.value.length ? (preenchidos.value.every((a) => a.conforme) ? "Conforme" : "Não Conforme") : null))

async function salvar() {
	if (!preenchidos.value.length) return toast("Informe ao menos uma leitura.", "erro")
	salvando.value = true
	try {
		const v = await api("registrar_verificacao", { id: props.equipamento.id, dados: f }, { post: true })
		toast(v.resultado === "Conforme" ? "Verificação registrada: conforme." : "Verificação registrada: NÃO conforme.", v.resultado === "Conforme" ? "sucesso" : "erro")
		emit("salvo", v)
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		salvando.value = false
	}
}
</script>

<template>
	<Modal titulo="Verificação intermediária" :subtitulo="`${equipamento.tag} · ${equipamento.descricao}`" largura="max-w-lg" @fechar="emit('fechar')">
		<form id="form-verif" class="space-y-4" @submit.prevent="salvar">
			<div class="rounded-xl bg-slate-50 p-3 text-sm text-slate-600">
				Meça uma referência conhecida (bloco, peso, ponto fixo…) e anote o valor lido.
				<span v-if="tolerancia">Tolerância: <b>± {{ numero(tolerancia, 6) }} {{ equipamento.unidade || "" }}</b>.</span>
				<span v-else class="text-amber-700">Equipamento sem tolerância cadastrada: o resultado não será avaliado.</span>
			</div>

			<div>
				<label class="label">Referência utilizada</label>
				<input v-model="f.referencia" class="input" placeholder="Ex.: bloco padrão 50 mm nº 123" />
			</div>

			<div class="space-y-2">
				<div class="grid grid-cols-[1fr_1fr_auto] gap-2 text-xs font-medium text-slate-500">
					<span>Valor de referência</span><span>Valor lido</span><span class="w-8" />
				</div>
				<div v-for="(p, i) in f.pontos" :key="i" class="grid grid-cols-[1fr_1fr_auto] items-center gap-2">
					<input v-model="p.valor_referencia" type="number" step="any" inputmode="decimal" class="input" required />
					<div class="relative">
						<input
							v-model="p.valor_lido"
							type="number"
							step="any"
							inputmode="decimal"
							class="input pr-9"
							:class="avaliados[i] && (avaliados[i].conforme ? 'border-emerald-300 bg-emerald-50/40' : 'border-rose-300 bg-rose-50/40')"
							required
						/>
						<CircleCheck v-if="avaliados[i]?.conforme" class="absolute top-1/2 right-2.5 size-4 -translate-y-1/2 text-emerald-600" />
						<CircleX v-else-if="avaliados[i]" class="absolute top-1/2 right-2.5 size-4 -translate-y-1/2 text-rose-600" />
					</div>
					<button type="button" class="btn-ghost w-8 p-1.5" :disabled="f.pontos.length === 1" title="Remover" @click="f.pontos.splice(i, 1)">
						<Trash2 class="size-4" />
					</button>
					<p v-if="avaliados[i]" class="col-span-3 -mt-1 text-xs" :class="avaliados[i].conforme ? 'text-emerald-700' : 'text-rose-700'">
						Desvio {{ numero(avaliados[i].desvio, 6) }}
					</p>
				</div>
				<button type="button" class="btn-ghost px-2 text-sm" @click="f.pontos.push({ valor_referencia: '', valor_lido: '' })">
					<Plus class="size-4" /> Adicionar ponto
				</button>
			</div>

			<div>
				<label class="label">Observação</label>
				<textarea v-model="f.observacao" rows="2" class="input" />
			</div>

			<div
				v-if="resultado"
				class="flex items-center gap-3 rounded-xl p-3 text-sm font-medium"
				:class="resultado === 'Conforme' ? 'bg-emerald-50 text-emerald-800' : 'bg-rose-50 text-rose-800'"
			>
				<CircleCheck v-if="resultado === 'Conforme'" class="size-5" /><CircleX v-else class="size-5" />
				{{ resultado === "Conforme" ? "Conforme: o equipamento pode continuar em uso." : "Não conforme: retire de uso e solicite calibração." }}
			</div>
		</form>
		<template #rodape>
			<button class="btn-secondary" @click="emit('fechar')">Cancelar</button>
			<button class="btn-primary" form="form-verif" type="submit" :disabled="salvando">{{ salvando ? "Salvando…" : "Registrar" }}</button>
		</template>
	</Modal>
</template>
