<script setup>
import { CircleAlert, CircleCheck, LoaderCircle, Search } from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"
import { api } from "@/api"
import Esqueleto from "@/components/Esqueleto.vue"
import Modal from "@/components/Modal.vue"
import { documentoValido, formatarDocumento, limparDocumento } from "@/format"
import { toast } from "@/store"

const props = defineProps({ tipoParte: { type: String, default: "Customer" }, parte: String })
const emit = defineEmits(["fechar", "salvo"])

const d = ref(null)
const salvando = ref(false)
const buscando = ref("")
const erro = ref("")
const rotulo = computed(() => (props.tipoParte === "Customer" ? "cliente" : "fornecedor"))
const docOk = computed(() => !d.value?.cnpj_cpf || documentoValido(d.value.cnpj_cpf))
const UFS = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split(" ")

onMounted(async () => {
	d.value = await api("dados_fiscais", { tipo_parte: props.tipoParte, parte: props.parte })
	d.value.cnpj_cpf = formatarDocumento(d.value.cnpj_cpf)
})

watch(
	() => d.value?.cnpj_cpf,
	(v) => {
		if (d.value && v) d.value.tipo_pessoa = limparDocumento(v).length === 11 ? "Física" : "Jurídica"
	},
)

// CEP: endereço e código IBGE automáticos (ViaCEP)
async function buscarCep() {
	const cep = String(d.value.cep || "").replace(/\D/g, "")
	if (cep.length !== 8) return
	buscando.value = "cep"
	try {
		const r = await (await fetch(`https://viacep.com.br/ws/${cep}/json/`)).json()
		if (r.erro) throw new Error()
		Object.assign(d.value, {
			cep: `${cep.slice(0, 5)}-${cep.slice(5)}`,
			logradouro: r.logradouro || d.value.logradouro,
			bairro: r.bairro || d.value.bairro,
			municipio: r.localidade,
			uf: r.uf,
			codigo_municipio: r.ibge,
		})
	} catch {
		toast("Não encontrei esse CEP. Preencha o endereço à mão.", "erro")
	} finally {
		buscando.value = ""
	}
}

// CNPJ: razão social e endereço da Receita (BrasilAPI, dados públicos)
async function buscarCnpj() {
	const c = limparDocumento(d.value.cnpj_cpf)
	if (c.length !== 14 || !documentoValido(c)) return toast("Digite um CNPJ válido primeiro.", "erro")
	buscando.value = "cnpj"
	try {
		const res = await fetch(`https://brasilapi.com.br/api/cnpj/v1/${c}`)
		if (!res.ok) throw new Error()
		const r = await res.json()
		Object.assign(d.value, {
			razao_social: r.razao_social || d.value.razao_social,
			logradouro: [r.descricao_tipo_de_logradouro, r.logradouro].filter(Boolean).join(" ") || d.value.logradouro,
			numero: r.numero || d.value.numero,
			complemento: r.complemento || d.value.complemento,
			bairro: r.bairro || d.value.bairro,
			cep: r.cep ? `${String(r.cep).slice(0, 5)}-${String(r.cep).slice(5)}` : d.value.cep,
			municipio: r.municipio ? r.municipio.charAt(0) + r.municipio.slice(1).toLowerCase() : d.value.municipio,
			uf: r.uf || d.value.uf,
			codigo_municipio: r.codigo_municipio_ibge ? String(r.codigo_municipio_ibge) : d.value.codigo_municipio,
			email_nota: d.value.email_nota || r.email || "",
		})
		toast("Dados da Receita preenchidos. Confira antes de salvar.")
	} catch {
		toast("Não consegui consultar esse CNPJ agora. Preencha à mão.", "erro")
	} finally {
		buscando.value = ""
	}
}

async function salvar() {
	erro.value = ""
	if (!docOk.value) return (erro.value = "O CNPJ/CPF não é válido.")
	salvando.value = true
	try {
		await api("salvar_dados_fiscais", { dados: { ...d.value, tipo_parte: props.tipoParte, parte: props.parte } }, { post: true })
		toast("Cadastro fiscal salvo.")
		emit("salvo")
	} catch (e) {
		erro.value = e.message
	} finally {
		salvando.value = false
	}
}
</script>

<template>
	<Modal :titulo="`Cadastro fiscal do ${rotulo}`" :subtitulo="parte" largura="max-w-2xl" @fechar="emit('fechar')">
		<Esqueleto v-if="!d" :linhas="8" classe="h-9" />
		<div v-else class="space-y-5">
			<p v-if="!d.existe" class="rounded-xl bg-blue-500/8 px-3 py-2 text-sm text-blue-700 dark:text-blue-300">
				Preenchemos com o que o ERP já sabe. Digite o CEP para completar o endereço sozinho.
			</p>

			<div class="grid gap-3 sm:grid-cols-6">
				<div class="sm:col-span-3">
					<label class="rotulo">CNPJ ou CPF</label>
					<div class="flex gap-2">
						<div class="relative flex-1">
							<input v-model="d.cnpj_cpf" class="campo pr-8" placeholder="00.000.000/0000-00" @blur="d.cnpj_cpf = formatarDocumento(d.cnpj_cpf)" />
							<CircleCheck v-if="d.cnpj_cpf && docOk" class="absolute top-2.5 right-2.5 size-4 text-emerald-500" />
							<CircleAlert v-else-if="d.cnpj_cpf" class="absolute top-2.5 right-2.5 size-4 text-rose-500" />
						</div>
						<button class="btn-secundario px-2.5" title="Buscar dados na Receita" :disabled="buscando === 'cnpj'" @click="buscarCnpj">
							<LoaderCircle v-if="buscando === 'cnpj'" class="size-4 animate-spin" /><Search v-else class="size-4" />
							<span class="hidden sm:inline">Buscar</span>
						</button>
					</div>
					<p v-if="d.cnpj_cpf && !docOk" class="mt-1 text-xs text-rose-600">Número inválido: confira os dígitos.</p>
				</div>
				<div class="sm:col-span-3">
					<label class="rotulo">Razão social / nome</label>
					<input v-model="d.razao_social" class="campo" />
				</div>
				<div class="sm:col-span-2">
					<label class="rotulo">Contribuinte de ICMS</label>
					<select v-model="d.contribuinte_icms" class="campo">
						<option>Não contribuinte</option>
						<option>Contribuinte</option>
						<option>Isento</option>
					</select>
				</div>
				<div class="sm:col-span-2">
					<label class="rotulo">Inscrição estadual {{ d.contribuinte_icms === "Contribuinte" ? "*" : "" }}</label>
					<input v-model="d.inscricao_estadual" class="campo" :placeholder="d.contribuinte_icms === 'Contribuinte' ? 'obrigatória' : 'se houver'" />
				</div>
				<div class="sm:col-span-2">
					<label class="rotulo">Inscrição municipal</label>
					<input v-model="d.inscricao_municipal" class="campo" placeholder="se houver" />
				</div>
				<div class="sm:col-span-6">
					<label class="rotulo">E-mail que recebe notas e boletos</label>
					<input v-model="d.email_nota" type="email" class="campo" placeholder="financeiro@cliente.com.br" />
				</div>
			</div>

			<div>
				<p class="mb-2 text-xs font-semibold tracking-wider text-suave uppercase">Endereço</p>
				<div class="grid gap-3 sm:grid-cols-6">
					<div class="sm:col-span-2">
						<label class="rotulo">CEP</label>
						<div class="relative">
							<input v-model="d.cep" class="campo" placeholder="00000-000" @blur="buscarCep" @keyup.enter="buscarCep" />
							<LoaderCircle v-if="buscando === 'cep'" class="absolute top-2.5 right-2.5 size-4 animate-spin text-suave" />
						</div>
					</div>
					<div class="sm:col-span-4"><label class="rotulo">Rua</label><input v-model="d.logradouro" class="campo" /></div>
					<div class="sm:col-span-1"><label class="rotulo">Número</label><input v-model="d.numero" class="campo" /></div>
					<div class="sm:col-span-2"><label class="rotulo">Complemento</label><input v-model="d.complemento" class="campo" /></div>
					<div class="sm:col-span-3"><label class="rotulo">Bairro</label><input v-model="d.bairro" class="campo" /></div>
					<div class="sm:col-span-3"><label class="rotulo">Município</label><input v-model="d.municipio" class="campo" /></div>
					<div class="sm:col-span-1">
						<label class="rotulo">UF</label>
						<select v-model="d.uf" class="campo px-2"><option value="" /><option v-for="u in UFS" :key="u">{{ u }}</option></select>
					</div>
					<div class="sm:col-span-2">
						<label class="rotulo">Código IBGE</label>
						<input v-model="d.codigo_municipio" class="campo" placeholder="vem pelo CEP" />
					</div>
				</div>
			</div>

			<div v-if="tipoParte === 'Customer'" class="rounded-xl border border-borda p-3">
				<p class="mb-2 text-xs font-semibold tracking-wider text-suave uppercase">O cliente retém impostos?</p>
				<label class="flex items-start gap-2 text-sm"><input v-model="d.iss_retido" type="checkbox" :true-value="1" :false-value="0" class="mt-0.5 accent-marca-600" />
					<span><b class="text-tinta">Retém o ISS</b> <span class="text-suave">— ele recolhe o ISS à prefeitura e paga o boleto pelo valor líquido</span></span></label>
				<label class="mt-2 flex items-start gap-2 text-sm"><input v-model="d.retem_impostos_federais" type="checkbox" :true-value="1" :false-value="0" class="mt-0.5 accent-marca-600" />
					<span><b class="text-tinta">Retém PIS, COFINS, CSLL e IR</b> <span class="text-suave">— comum em empresas grandes e órgãos públicos; confirme com o cliente ou o contador</span></span></label>
			</div>
			<p v-if="erro" class="rounded-xl bg-rose-500/10 px-3 py-2 text-sm whitespace-pre-line text-rose-700 dark:text-rose-300">{{ erro }}</p>
		</div>
		<template #rodape>
			<button class="btn-secundario" @click="emit('fechar')">Cancelar</button>
			<button class="btn-primario" :disabled="!d || salvando" @click="salvar">{{ salvando ? "Salvando…" : "Salvar cadastro" }}</button>
		</template>
	</Modal>
</template>
