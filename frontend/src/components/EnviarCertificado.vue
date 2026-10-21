<script setup>
import { FileUp, UploadCloud } from "lucide-vue-next"
import { computed, onMounted, reactive, ref } from "vue"
import { api } from "@/api"
import Modal from "@/components/Modal.vue"
import { CONSULTA } from "@/modo"
import { store, toast } from "@/store"

// Certificado emitido por OUTRO laboratório, anexado pelo próprio cliente.
const props = defineProps({ equipamento: Object })
const emit = defineEmits(["fechar", "salvo"])

const equipamentos = ref(props.equipamento ? [props.equipamento] : [])
const f = reactive({
	equipamento_id: props.equipamento?.id || "",
	numero: "",
	laboratorio: props.equipamento?.fornecedor_externo || "",
	data_calibracao: "",
	data_validade: "",
	acreditado: true,
})
const arquivo = ref(null)
const arrastando = ref(false)
const enviando = ref(false)

const selecionado = computed(() => equipamentos.value.find((e) => e.id === f.equipamento_id))

onMounted(async () => {
	if (!props.equipamento) {
		const lista = await api("equipamentos")
		equipamentos.value = (CONSULTA ? lista.filter((e) => e.editavel) : lista).sort((a, b) => (a.calibrado_por === "Terceiro" ? -1 : 1) - (b.calibrado_por === "Terceiro" ? -1 : 1))
	}
})

function escolherEquipamento() {
	if (selecionado.value?.fornecedor_externo && !f.laboratorio) f.laboratorio = selecionado.value.fornecedor_externo
}

function soltar(e) {
	arrastando.value = false
	const file = e.dataTransfer.files[0]
	if (file) arquivo.value = file
}

async function enviar() {
	if (!arquivo.value) return toast("Anexe o PDF do certificado.", "erro")
	enviando.value = true
	try {
		const form = new FormData()
		form.append("file", arquivo.value)
		const cert = await api(
			"anexar_certificado_externo",
			{ dados: { ...f, data_validade: f.data_validade || null }, cliente: selecionado.value?.cliente },
			{ post: true, form },
		)
		toast("Certificado externo registrado.")
		emit("salvo", cert)
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		enviando.value = false
	}
}
</script>

<template>
	<Modal titulo="Enviar certificado externo" subtitulo="Registre calibrações feitas por outros laboratórios para manter o histórico completo." largura="max-w-xl" @fechar="emit('fechar')">
		<form id="form-cert" class="space-y-4" @submit.prevent="enviar">
			<div>
				<label class="label">Equipamento *</label>
				<select v-model="f.equipamento_id" class="input" required :disabled="!!equipamento" @change="escolherEquipamento">
					<option value="" disabled>Selecione…</option>
					<option v-for="e in equipamentos" :key="e.id" :value="e.id">
						{{ e.tag }} — {{ e.descricao }}{{ e.calibrado_por === "Terceiro" ? " (terceiro)" : "" }}{{ store.contexto.clientes.length > 1 ? ` · ${e.cliente}` : "" }}
					</option>
				</select>
			</div>
			<div class="grid gap-4 sm:grid-cols-2">
				<div>
					<label class="label">Nº do certificado *</label>
					<input v-model="f.numero" class="input" required />
				</div>
				<div>
					<label class="label">Laboratório emissor *</label>
					<input v-model="f.laboratorio" class="input" required />
				</div>
				<div>
					<label class="label">Data da calibração *</label>
					<input v-model="f.data_calibracao" type="date" class="input" required />
				</div>
				<div>
					<label class="label">Válido até</label>
					<input v-model="f.data_validade" type="date" class="input" />
					<p class="mt-1 text-[11px] text-slate-400">Vazio = calculado pela periodicidade do equipamento</p>
				</div>
			</div>
			<label class="flex items-center gap-2 text-sm text-slate-700">
				<input v-model="f.acreditado" type="checkbox" class="accent-brand-600" /> Laboratório acreditado (RBC / ISO/IEC 17025)
			</label>

			<label
				class="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-6 text-center transition"
				:class="arrastando ? 'border-brand-400 bg-brand-50' : arquivo ? 'border-emerald-300 bg-emerald-50/50' : 'border-slate-200 hover:bg-slate-50'"
				@dragover.prevent="arrastando = true"
				@dragleave="arrastando = false"
				@drop.prevent="soltar"
			>
				<input type="file" accept="application/pdf" class="hidden" @change="arquivo = $event.target.files[0]" />
				<component :is="arquivo ? FileUp : UploadCloud" class="mb-2 size-7" :class="arquivo ? 'text-emerald-600' : 'text-slate-400'" />
				<p class="text-sm font-medium text-slate-700">{{ arquivo ? arquivo.name : "Arraste o PDF aqui ou clique para escolher" }}</p>
				<p class="text-xs text-slate-400">{{ arquivo ? `${(arquivo.size / 1024).toFixed(0)} KB` : "Somente PDF" }}</p>
			</label>
		</form>
		<template #rodape>
			<button class="btn-secondary" @click="emit('fechar')">Cancelar</button>
			<button class="btn-primary" form="form-cert" type="submit" :disabled="enviando">{{ enviando ? "Enviando…" : "Registrar certificado" }}</button>
		</template>
	</Modal>
</template>
