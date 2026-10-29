<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue"
import { api } from "@/api"
import Modal from "@/components/Modal.vue"
import { toast } from "@/store"

// Cadastro/edição de equipamento. Os campos de configuração mudam conforme o grupo do tipo.
const props = defineProps({ equipamento: Object })
const emit = defineEmits(["fechar", "salvo"])
const novo = !props.equipamento
const tipos = ref([])
const pessoas = ref([])
const busca = ref("")
const salvando = ref(false)
const f = reactive({
	nome: "", tipo: "", status: "Em Estoque", marca: "", modelo: "", numero_serie: "", patrimonio: "", responsavel: "", departamento: "",
	localizacao: "", data_termo: "", processador: "", memoria_ram: "", armazenamento: "", sistema_operacional: "", endereco_ip: "",
	endereco_mac: "", firmware: "", imei: "", numero_linha: "", operadora: "", especificacoes: "", data_compra: "", valor_compra: "",
	fornecedor: "", garantia_ate: "", observacoes: "",
	...Object.fromEntries(Object.entries(props.equipamento || {}).map(([k, v]) => [k, v ?? ""])),
})
const responsavelNome = ref(props.equipamento?.responsavel_nome || "")
onMounted(async () => (tipos.value = (await api("inventario.tipos", {})).filter((t) => !t.controla_estoque)))
const grupo = computed(() => tipos.value.find((t) => t.id === f.tipo)?.grupo)

let atraso
watch(busca, (t) => {
	clearTimeout(atraso)
	atraso = setTimeout(async () => (pessoas.value = t.length >= 2 ? await api("buscar_pessoas", { texto: t }) : []), 250)
})

async function salvar() {
	salvando.value = true
	try {
		const r = await api("inventario.salvar_equipamento", { id: props.equipamento?.id, dados: { ...f } }, { post: true })
		toast(novo ? `Equipamento ${r.nome} cadastrado.` : "Alterações salvas.")
		emit("salvo", r)
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		salvando.value = false
	}
}
const STATUS = ["Em Uso", "Em Estoque", "Em Manutenção", "Emprestado", "Descartado", "Extraviado"]
</script>

<template>
	<Modal :titulo="novo ? 'Novo equipamento' : `Editar ${equipamento.nome}`" largura="max-w-3xl" @fechar="emit('fechar')">
		<form id="form-eqp-ti" class="space-y-5" @submit.prevent="salvar">
			<div class="grid gap-4 sm:grid-cols-3">
				<div>
					<label class="rotulo">Nome / hostname *</label>
					<input v-model="f.nome" class="campo uppercase" required :disabled="!novo" placeholder="LAB-NB-07" />
				</div>
				<div>
					<label class="rotulo">Tipo *</label>
					<select v-model="f.tipo" class="campo" required>
						<option value="" disabled>Selecione…</option>
						<option v-for="t in tipos" :key="t.id" :value="t.id">{{ t.id }}</option>
					</select>
				</div>
				<div>
					<label class="rotulo">Status</label>
					<select v-model="f.status" class="campo"><option v-for="s in STATUS" :key="s">{{ s }}</option></select>
				</div>
				<div><label class="rotulo">Marca</label><input v-model="f.marca" class="campo" /></div>
				<div><label class="rotulo">Modelo</label><input v-model="f.modelo" class="campo" /></div>
				<div><label class="rotulo">Nº de série</label><input v-model="f.numero_serie" class="campo" /></div>
			</div>

			<fieldset class="grid gap-4 border-t border-borda pt-4 sm:grid-cols-3">
				<div class="relative sm:col-span-1">
					<label class="rotulo">Com quem está</label>
					<div v-if="f.responsavel" class="flex items-center gap-2 rounded-xl border border-borda bg-realce px-3 py-2 text-sm">
						<span class="flex-1 truncate text-tinta">{{ responsavelNome || f.responsavel }}</span>
						<button type="button" class="text-xs text-suave hover:text-rose-500" @click="(f.responsavel = ''), (responsavelNome = '')">devolver</button>
					</div>
					<template v-else>
						<input v-model="busca" class="campo" placeholder="Buscar pessoa…" />
						<ul v-if="pessoas.length" class="absolute z-10 mt-1 w-full overflow-hidden rounded-xl border border-borda bg-elevada shadow-pop">
							<li v-for="p in pessoas" :key="p.id">
								<button type="button" class="w-full px-3 py-2 text-left text-sm hover:bg-realce" @click="(f.responsavel = p.id), (responsavelNome = p.nome), (busca = ''), (pessoas = [])">{{ p.nome }}</button>
							</li>
						</ul>
					</template>
				</div>
				<div><label class="rotulo">Departamento</label><input v-model="f.departamento" class="campo" /></div>
				<div><label class="rotulo">Localização</label><input v-model="f.localizacao" class="campo" /></div>
			</fieldset>

			<fieldset v-if="grupo === 'Computador'" class="grid gap-4 border-t border-borda pt-4 sm:grid-cols-4">
				<div><label class="rotulo">Processador</label><input v-model="f.processador" class="campo" /></div>
				<div><label class="rotulo">Memória RAM</label><input v-model="f.memoria_ram" class="campo" placeholder="16 GB" /></div>
				<div><label class="rotulo">Armazenamento</label><input v-model="f.armazenamento" class="campo" placeholder="512 GB SSD" /></div>
				<div><label class="rotulo">Sistema</label><input v-model="f.sistema_operacional" class="campo" /></div>
				<p v-if="!novo" class="text-xs text-suave sm:col-span-4">Dica: para upgrades, use "Registrar manutenção / upgrade" — o histórico fica guardado e estes campos se atualizam sozinhos.</p>
			</fieldset>
			<fieldset v-if="['Rede e Servidores', 'Impressora'].includes(grupo)" class="grid gap-4 border-t border-borda pt-4 sm:grid-cols-3">
				<div><label class="rotulo">Endereço IP</label><input v-model="f.endereco_ip" class="campo" /></div>
				<div><label class="rotulo">Endereço MAC</label><input v-model="f.endereco_mac" class="campo" /></div>
				<div><label class="rotulo">Firmware</label><input v-model="f.firmware" class="campo" /></div>
			</fieldset>
			<fieldset v-if="grupo === 'Celular'" class="grid gap-4 border-t border-borda pt-4 sm:grid-cols-3">
				<div><label class="rotulo">IMEI</label><input v-model="f.imei" class="campo" /></div>
				<div><label class="rotulo">Número da linha</label><input v-model="f.numero_linha" class="campo" /></div>
				<div><label class="rotulo">Operadora</label><input v-model="f.operadora" class="campo" /></div>
			</fieldset>

			<fieldset class="grid gap-4 border-t border-borda pt-4 sm:grid-cols-4">
				<div><label class="rotulo">Data da compra</label><input v-model="f.data_compra" type="date" class="campo" /></div>
				<div><label class="rotulo">Valor (R$)</label><input v-model="f.valor_compra" type="number" step="0.01" class="campo" /></div>
				<div><label class="rotulo">Fornecedor</label><input v-model="f.fornecedor" class="campo" /></div>
				<div><label class="rotulo">Garantia até</label><input v-model="f.garantia_ate" type="date" class="campo" /></div>
			</fieldset>
			<div><label class="rotulo">Observações</label><textarea v-model="f.observacoes" rows="2" class="campo" /></div>
		</form>
		<template #rodape>
			<button class="btn-secundario" @click="emit('fechar')">Cancelar</button>
			<button class="btn-primario" form="form-eqp-ti" type="submit" :disabled="salvando">{{ salvando ? "Salvando…" : "Salvar" }}</button>
		</template>
	</Modal>
</template>
