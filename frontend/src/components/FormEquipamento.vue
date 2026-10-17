<script setup>
import { computed, reactive, ref } from "vue"
import { api } from "@/api"
import Modal from "@/components/Modal.vue"
import SeletorCliente from "@/components/SeletorCliente.vue"
import { clienteAtual, infoCliente, precisaEscolherCliente, store, toast } from "@/store"

// Sem `equipamento` = cadastro novo. Com `equipamento` = edição (campos limitados se não foi o cliente que cadastrou).
const props = defineProps({ equipamento: Object })
const emit = defineEmits(["fechar", "salvo"])

const GRANDEZAS = ["Dimensional", "Pressão", "Temperatura", "Umidade", "Elétrica", "Massa", "Força", "Torque", "Volume", "Vazão", "Tempo e Frequência", "Óptica", "Outros"]
const STATUS = ["Ativo", "Em Calibração", "Em Manutenção", "Reserva", "Inativo", "Sucateado"]

const novo = !props.equipamento
const completo = novo || props.equipamento.editavel
const f = reactive({
	tag: "",
	descricao: "",
	grandeza: "",
	fabricante: "",
	modelo: "",
	numero_serie: "",
	faixa_medicao: "",
	resolucao: "",
	unidade: "",
	distrito: "",
	localizacao: "",
	responsavel: "",
	status: "Ativo",
	calibrado_por: "Terceiro",
	fornecedor_externo: "",
	periodicidade_meses: 12,
	tolerancia: null,
	verificacao_intervalo_dias: null,
	tolerancia_verificacao: null,
	proxima_calibracao: "",
	...(props.equipamento || {}),
})
const cliente = ref(store.cliente || "")
const salvando = ref(false)
const escolherCliente = computed(() => novo && precisaEscolherCliente())

// Distrito: só para cliente com controle por distritos; lista apenas os que o usuário enxerga
const infoAlvo = computed(() => (novo ? infoCliente(cliente.value) || clienteAtual() : infoCliente(props.equipamento.cliente)))
const distritos = computed(() => (infoAlvo.value?.usa_distritos ? infoAlvo.value.distritos : []))
if (novo && !f.distrito) f.distrito = store.distrito || (distritos.value.length === 1 ? distritos.value[0].id : "")

async function salvar() {
	if (escolherCliente.value && !cliente.value) return toast("Selecione o cliente.", "erro")
	salvando.value = true
	const dados = Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v === "" ? null : v]))
	try {
		const res = novo
			? await api("criar_equipamento", { dados, cliente: cliente.value || undefined }, { post: true })
			: await api("atualizar_equipamento", { id: props.equipamento.id, dados }, { post: true })
		toast(novo ? `Equipamento ${res.tag} cadastrado.` : "Alterações salvas.")
		emit("salvo", res)
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		salvando.value = false
	}
}
</script>

<template>
	<Modal
		:titulo="novo ? 'Novo equipamento' : `Editar ${equipamento.tag}`"
		:subtitulo="novo ? 'Cadastre também instrumentos calibrados por outros laboratórios e centralize tudo aqui.' : completo ? '' : 'Equipamento cadastrado pelo laboratório: apenas localização, responsável e status podem ser alterados.'"
		largura="max-w-2xl"
		@fechar="emit('fechar')"
	>
		<form id="form-eqp" class="space-y-5" @submit.prevent="salvar">
			<SeletorCliente v-if="escolherCliente" v-model="cliente" />

			<fieldset v-if="completo" class="grid gap-4 sm:grid-cols-2">
				<div>
					<label class="label">TAG / Código interno *</label>
					<input v-model="f.tag" class="input uppercase" required placeholder="Ex.: PAQ-015" />
				</div>
				<div>
					<label class="label">Descrição *</label>
					<input v-model="f.descricao" class="input" required placeholder="Ex.: Paquímetro digital 150 mm" />
				</div>
				<div>
					<label class="label">Grandeza</label>
					<select v-model="f.grandeza" class="input">
						<option value="">—</option>
						<option v-for="g in GRANDEZAS" :key="g">{{ g }}</option>
					</select>
				</div>
				<div>
					<label class="label">Nº de série</label>
					<input v-model="f.numero_serie" class="input" />
				</div>
				<div>
					<label class="label">Fabricante</label>
					<input v-model="f.fabricante" class="input" />
				</div>
				<div>
					<label class="label">Modelo</label>
					<input v-model="f.modelo" class="input" />
				</div>
				<div>
					<label class="label">Faixa de medição</label>
					<input v-model="f.faixa_medicao" class="input" placeholder="Ex.: 0 a 150 mm" />
				</div>
				<div class="grid grid-cols-2 gap-3">
					<div>
						<label class="label">Resolução</label>
						<input v-model="f.resolucao" class="input" />
					</div>
					<div>
						<label class="label">Unidade</label>
						<input v-model="f.unidade" class="input" placeholder="mm" />
					</div>
				</div>
			</fieldset>

			<fieldset class="grid gap-4 sm:grid-cols-3" :class="completo && 'border-t border-slate-100 pt-5'">
				<div v-if="distritos.length" class="sm:col-span-3">
					<label class="label">Distrito *</label>
					<select v-model="f.distrito" class="input" required>
						<option value="" disabled>Selecione…</option>
						<option v-for="d in distritos" :key="d.id" :value="d.id">{{ d.nome }}</option>
					</select>
					<p v-if="!novo && equipamento.distrito && f.distrito !== equipamento.distrito" class="mt-1 text-xs text-amber-700">
						O equipamento será transferido de distrito. A mudança fica registrada no histórico.
					</p>
				</div>
				<div>
					<label class="label">Localização / Setor</label>
					<input v-model="f.localizacao" class="input" />
				</div>
				<div>
					<label class="label">Responsável</label>
					<input v-model="f.responsavel" class="input" />
				</div>
				<div>
					<label class="label">Status</label>
					<select v-model="f.status" class="input">
						<option v-for="s in STATUS" :key="s">{{ s }}</option>
					</select>
				</div>
			</fieldset>

			<fieldset v-if="completo" class="grid gap-4 border-t border-slate-100 pt-5 sm:grid-cols-2">
				<div class="sm:col-span-2">
					<label class="label">Quem calibra este equipamento?</label>
					<div class="grid grid-cols-2 gap-2">
						<label
							v-for="op in ['Nosso Laboratório', 'Terceiro']"
							:key="op"
							class="flex cursor-pointer items-center gap-2.5 rounded-xl border p-3 text-sm transition"
							:class="f.calibrado_por === op ? 'border-brand-400 bg-brand-50/60 ring-4 ring-brand-100' : 'border-slate-200 hover:bg-slate-50'"
						>
							<input v-model="f.calibrado_por" type="radio" :value="op" class="accent-brand-600" />
							{{ op === "Nosso Laboratório" ? store.contexto.empresa : "Outro laboratório" }}
						</label>
					</div>
				</div>
				<div v-if="f.calibrado_por === 'Terceiro'">
					<label class="label">Laboratório externo *</label>
					<input v-model="f.fornecedor_externo" class="input" required />
				</div>
				<div v-if="f.calibrado_por === 'Terceiro'">
					<label class="label">Próxima calibração</label>
					<input v-model="f.proxima_calibracao" type="date" class="input" />
				</div>
				<div class="sm:col-span-2">
					<label class="label">Tolerância (±) — critério de aceitação</label>
					<input v-model.number="f.tolerancia" type="number" step="any" class="input" placeholder="Ex.: 0,03" />
				</div>
			</fieldset>

			<fieldset class="grid gap-4 border-t border-slate-100 pt-5 sm:grid-cols-3">
				<legend class="mb-3 text-xs font-semibold tracking-wider text-slate-500 uppercase">Intervalos (decisão da sua empresa)</legend>
				<div>
					<label class="label">Calibração a cada (meses)</label>
					<input v-model.number="f.periodicidade_meses" type="number" min="1" class="input" />
				</div>
				<div>
					<label class="label">Verificação intermediária a cada (dias)</label>
					<input v-model.number="f.verificacao_intervalo_dias" type="number" min="1" class="input" placeholder="Não se aplica" />
				</div>
				<div>
					<label class="label">Tolerância da verificação (±)</label>
					<input v-model.number="f.tolerancia_verificacao" type="number" step="any" class="input" :placeholder="f.tolerancia ? `Padrão: ${f.tolerancia}` : ''" />
				</div>
			</fieldset>
		</form>

		<template #rodape>
			<button class="btn-secondary" @click="emit('fechar')">Cancelar</button>
			<button class="btn-primary" form="form-eqp" type="submit" :disabled="salvando">
				{{ salvando ? "Salvando…" : novo ? "Cadastrar" : "Salvar" }}
			</button>
		</template>
	</Modal>
</template>
