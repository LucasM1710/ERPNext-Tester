<script setup>
import { ArrowLeft, Ban, CircleAlert, Code, ExternalLink, Mail, Printer, Receipt, RotateCcw } from "lucide-vue-next"
import { computed, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { api, urlDocumento } from "@/api"
import CadastroFiscal from "@/components/CadastroFiscal.vue"
import Copiar from "@/components/Copiar.vue"
import Esqueleto from "@/components/Esqueleto.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import Modal from "@/components/Modal.vue"
import Resultado from "@/components/Resultado.vue"
import { data, dataHora, formatarDocumento, moeda } from "@/format"
import { toast } from "@/store"

const props = defineProps({ id: String })
const router = useRouter()
const n = ref(null)
const cancelando = ref(false)
const motivo = ref("")
const ocupado = ref(false)
const resultado = ref(null)
const cadastro = ref(false)

const horasDesde = computed(() => (n.value?.data_emissao ? (Date.now() - new Date(n.value.data_emissao.replace(" ", "T"))) / 36e5 : 0))
const d = computed(() => n.value?.destinatario || {})
const retencoes = computed(() =>
	[
		["ISS retido", n.value.iss_retido ? n.value.valores.valor_iss : 0],
		["PIS", n.value.valores.valor_pis_retido],
		["COFINS", n.value.valores.valor_cofins_retido],
		["CSLL", n.value.valores.valor_csll_retido],
		["IR", n.value.valores.valor_ir_retido],
	].filter(([, v]) => v),
)

async function carregar() {
	n.value = await api("nota", { id: props.id })
}

async function cancelar() {
	ocupado.value = true
	try {
		await api("cancelar_nota", { id: props.id, motivo: motivo.value }, { post: true })
		toast("Nota cancelada.")
		cancelando.value = false
		await carregar()
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		ocupado.value = false
	}
}

async function tentarDeNovo() {
	ocupado.value = true
	try {
		resultado.value = await api("tentar_de_novo", { id: props.id }, { post: true })
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		ocupado.value = false
	}
}

async function reenviar() {
	try {
		const r = await api("reenviar_email", { id: props.id }, { post: true })
		toast(r.simulacao ? "E-mail registrado no histórico (simulação: não saiu de verdade)." : "E-mail enviado ao cliente.")
		await carregar()
	} catch (e) {
		toast(e.message, "erro")
	}
}

onMounted(carregar)
</script>

<template>
	<div class="space-y-5">
		<button class="btn-fantasma -ml-2" @click="router.back()"><ArrowLeft class="size-4" /> Voltar</button>
		<div v-if="!n" class="card p-6"><Esqueleto :linhas="8" /></div>
		<template v-else>
			<div class="card p-5">
				<div class="flex flex-wrap items-start gap-4">
					<div class="min-w-0 flex-1">
						<div class="flex flex-wrap items-center gap-2">
							<Etiqueta :valor="n.tipo_documento" :ponto="false" />
							<Etiqueta :valor="n.status" />
							<span v-if="n.situacao_remessa" class="text-xs font-medium" :class="n.atrasada ? 'text-rose-600' : 'text-suave'">
								Remessa {{ n.situacao_remessa.toLowerCase() }}{{ n.atrasada ? " · retorno atrasado" : "" }}
							</span>
						</div>
						<h1 class="mt-2 text-2xl font-semibold tracking-tight text-tinta">{{ n.numero ? `${n.tipo_documento} nº ${n.numero}` : n.tipo_documento }} <span class="text-lg font-normal text-suave">· {{ moeda(n.valor_total) }}</span></h1>
						<p class="text-sm text-suave">{{ n.natureza }} · {{ n.nome_parte }}<span v-if="n.data_emissao"> · emitida em {{ dataHora(n.data_emissao) }}</span></p>
					</div>
					<div class="flex flex-wrap gap-2">
						<template v-if="['Autorizada', 'Cancelada'].includes(n.status)">
							<a :href="urlDocumento('nota', n.id)" target="_blank" class="btn-secundario"><Printer class="size-4" /> {{ n.tipo_documento === "NF-e" ? "DANFE" : "DANFSe" }}</a>
							<a :href="urlDocumento('xml', n.id)" class="btn-secundario"><Code class="size-4" /> XML</a>
						</template>
						<button v-if="n.status === 'Autorizada'" class="btn-secundario" @click="reenviar"><Mail class="size-4" /> Reenviar</button>
						<button v-if="n.pode_cancelar" class="btn-secundario text-rose-600" @click="cancelando = true"><Ban class="size-4" /> Cancelar</button>
						<template v-if="n.status === 'Rejeitada'">
							<button class="btn-secundario" @click="cadastro = true">Corrigir cadastro</button>
							<button class="btn-primario" :disabled="ocupado" @click="tentarDeNovo"><RotateCcw class="size-4" /> Tentar de novo</button>
						</template>
					</div>
				</div>

				<div v-if="n.status === 'Rejeitada'" class="mt-4 flex gap-3 rounded-xl border border-rose-500/30 bg-rose-500/6 p-3 text-sm">
					<CircleAlert class="mt-0.5 size-5 shrink-0 text-rose-500" />
					<div><p class="font-medium text-tinta">{{ n.mensagem_retorno }}</p><p v-if="n.orientacao" class="mt-0.5 text-rose-700 dark:text-rose-300">O que fazer: {{ n.orientacao }}</p></div>
				</div>
				<div v-if="n.status === 'Cancelada'" class="mt-4 rounded-xl bg-realce p-3 text-sm text-suave">Cancelada. Motivo: {{ n.motivo_cancelamento }}</div>

				<div v-if="n.chave_acesso" class="mt-4 flex flex-wrap items-center gap-3 rounded-xl bg-realce/70 px-3 py-2">
					<div class="min-w-0 flex-1">
						<p class="text-[11px] font-medium text-suave">Chave de acesso · protocolo {{ n.protocolo }}</p>
						<p class="font-mono text-sm break-all text-tinta">{{ n.chave_formatada }}</p>
					</div>
					<Copiar :texto="n.chave_acesso" rotulo="Copiar chave" />
				</div>
			</div>

			<div class="grid gap-5 lg:grid-cols-3">
				<div class="space-y-5 lg:col-span-2">
					<section class="card p-5">
						<h2 class="mb-3 text-sm font-semibold text-tinta">Destinatário</h2>
						<dl class="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
							<div><dt class="text-xs text-suave">Nome</dt><dd class="text-tinta">{{ d.razao_social }}</dd></div>
							<div><dt class="text-xs text-suave">CNPJ/CPF</dt><dd class="text-tinta">{{ formatarDocumento(d.cnpj_cpf) }}</dd></div>
							<div class="sm:col-span-2"><dt class="text-xs text-suave">Endereço</dt><dd class="text-tinta">{{ [d.logradouro, d.numero, d.bairro].filter(Boolean).join(", ") }} — {{ d.municipio }}/{{ d.uf }}</dd></div>
							<div><dt class="text-xs text-suave">Inscrição estadual</dt><dd class="text-tinta">{{ d.inscricao_estadual || d.contribuinte_icms }}</dd></div>
							<div><dt class="text-xs text-suave">E-mail</dt><dd class="text-tinta">{{ d.email_nota || "—" }}</dd></div>
						</dl>
						<div v-if="n.nf_referenciada" class="mt-3 rounded-xl bg-realce/70 px-3 py-2 text-sm">
							<p class="text-[11px] text-suave">Nota de origem (o equipamento chegou com ela)</p>
							<p class="font-mono text-tinta">{{ n.nf_referenciada }}</p>
						</div>
					</section>

					<section class="card overflow-hidden">
						<h2 class="px-5 pt-5 pb-3 text-sm font-semibold text-tinta">{{ n.tipo_documento === "NFS-e" ? "Serviços" : "Itens" }}</h2>
						<table class="w-full">
							<thead class="border-y border-borda bg-realce/50"><tr><th class="th">Descrição</th><th class="th hidden sm:table-cell">NCM / CFOP</th><th class="th text-right">Qtd</th><th class="th text-right">Total</th></tr></thead>
							<tbody class="divide-y divide-borda">
								<tr v-for="(i, k) in n.itens" :key="k">
									<td class="td text-tinta">{{ i.descricao }}<span v-if="i.numero_serie" class="block text-xs text-suave">Série {{ i.numero_serie }}</span></td>
									<td class="td hidden text-suave sm:table-cell">{{ i.ncm || "—" }} / {{ i.cfop || "—" }}</td>
									<td class="td text-right text-suave tabular-nums">{{ i.quantidade }} × {{ moeda(i.valor_unitario) }}</td>
									<td class="td text-right font-medium text-tinta tabular-nums">{{ moeda(i.valor_total) }}</td>
								</tr>
							</tbody>
						</table>
						<p v-if="n.discriminacao" class="border-t border-borda px-5 py-3 text-sm whitespace-pre-line text-suave">{{ n.discriminacao }}</p>
						<p v-if="n.informacoes_complementares" class="border-t border-borda px-5 py-3 text-sm text-suave">{{ n.informacoes_complementares }}</p>
					</section>
				</div>

				<div class="space-y-5">
					<section class="card p-5">
						<h2 class="mb-3 text-sm font-semibold text-tinta">Valores</h2>
						<dl class="space-y-1.5 text-sm">
							<div class="flex justify-between"><dt class="text-suave">Valor da nota</dt><dd class="font-medium text-tinta tabular-nums">{{ moeda(n.valores.valor_total) }}</dd></div>
							<div v-if="n.valores.valor_iss" class="flex justify-between"><dt class="text-suave">ISS ({{ n.valores.aliquota_iss }}%)</dt><dd class="text-tinta tabular-nums">{{ moeda(n.valores.valor_iss) }}</dd></div>
							<div v-if="n.valores.valor_icms" class="flex justify-between"><dt class="text-suave">ICMS ({{ n.valores.aliquota_icms }}%)</dt><dd class="text-tinta tabular-nums">{{ moeda(n.valores.valor_icms) }}</dd></div>
							<div v-if="n.valores.valor_cbs || n.valores.valor_ibs" class="flex justify-between text-xs"><dt class="text-suave">CBS / IBS (só informativo)</dt><dd class="text-suave tabular-nums">{{ moeda(n.valores.valor_cbs) }} / {{ moeda(n.valores.valor_ibs) }}</dd></div>
							<template v-if="retencoes.length">
								<p class="pt-2 text-xs font-semibold text-suave">O cliente retém e recolhe:</p>
								<div v-for="[r, v] in retencoes" :key="r" class="flex justify-between"><dt class="text-suave">− {{ r }}</dt><dd class="text-tinta tabular-nums">{{ moeda(v) }}</dd></div>
							</template>
							<div class="flex justify-between border-t border-borda pt-2"><dt class="font-medium text-tinta">A receber</dt><dd class="font-semibold text-tinta tabular-nums">{{ moeda(n.valores.valor_liquido || n.valores.valor_total) }}</dd></div>
						</dl>
					</section>

					<section v-if="n.boleto_detalhe" class="card p-5">
						<h2 class="mb-2 flex items-center gap-2 text-sm font-semibold text-tinta"><Receipt class="size-4 text-amber-500" /> Boleto</h2>
						<div class="flex items-center justify-between text-sm"><span class="text-suave">{{ moeda(n.boleto_detalhe.valor) }} · vence {{ data(n.boleto_detalhe.vencimento) }}</span><Etiqueta :valor="n.boleto_detalhe.status" /></div>
						<div class="mt-3 flex flex-wrap gap-2">
							<a :href="urlDocumento('boleto', n.boleto_detalhe.id)" target="_blank" class="btn-secundario px-2.5 py-1.5 text-xs"><Printer class="size-3.5" /> Ver boleto</a>
							<RouterLink to="/boletos" class="btn-fantasma px-2.5 py-1.5 text-xs">Ir para boletos</RouterLink>
						</div>
					</section>
					<a v-if="n.fatura" :href="`/app/sales-invoice/${n.fatura}`" target="_blank" class="btn-fantasma w-full justify-start"><ExternalLink class="size-4" /> Fatura {{ n.fatura }} no ERP</a>

					<section class="card p-5">
						<h2 class="mb-3 text-sm font-semibold text-tinta">Histórico</h2>
						<ol class="relative space-y-3 border-l border-borda pl-4">
							<li v-for="(e, k) in n.eventos" :key="k" class="relative">
								<span class="absolute top-1.5 -left-[21px] size-2.5 rounded-full bg-marca-500 ring-4 ring-superficie" />
								<p class="text-sm font-medium text-tinta">{{ e.evento }}</p>
								<p v-if="e.detalhe" class="text-xs text-suave">{{ e.detalhe }}</p>
								<p class="text-[11px] text-suave/80">{{ dataHora(e.data) }}</p>
							</li>
						</ol>
					</section>
				</div>
			</div>
		</template>

		<Modal v-if="cancelando" titulo="Cancelar nota" :subtitulo="`${n.tipo_documento} nº ${n.numero} · ${moeda(n.valor_total)}`" @fechar="cancelando = false">
			<div class="space-y-3 text-sm">
				<p v-if="n.tipo_documento === 'NF-e'" class="rounded-xl px-3 py-2" :class="horasDesde > 24 ? 'bg-rose-500/10 text-rose-700 dark:text-rose-300' : 'bg-blue-500/8 text-blue-700 dark:text-blue-300'">
					{{ horasDesde > 24 ? "Passaram mais de 24 horas: a SEFAZ não aceita mais o cancelamento. Fale com o contador (nota de devolução ou estorno)." : `A NF-e pode ser cancelada em até 24 horas. Restam cerca de ${Math.max(0, Math.floor(24 - horasDesde))} h.` }}
				</p>
				<p v-else class="rounded-xl bg-blue-500/8 px-3 py-2 text-blue-700 dark:text-blue-300">O prazo para cancelar NFS-e depende da prefeitura. Se passou do prazo, o pedido pode precisar de análise.</p>
				<p v-if="n.boleto_detalhe && n.boleto_detalhe.status !== 'Pago'" class="text-suave">O boleto em aberto desta nota também será cancelado.</p>
				<div>
					<label class="rotulo">Motivo (mínimo 15 caracteres, vai para a SEFAZ/prefeitura)</label>
					<textarea v-model="motivo" rows="3" class="campo" placeholder="Ex.: Nota emitida com valor errado, será reemitida." />
					<p class="mt-1 text-xs" :class="motivo.trim().length >= 15 ? 'text-emerald-600' : 'text-suave'">{{ motivo.trim().length }}/15</p>
				</div>
			</div>
			<template #rodape>
				<button class="btn-secundario" @click="cancelando = false">Voltar</button>
				<button class="btn-perigo" :disabled="motivo.trim().length < 15 || ocupado" @click="cancelar"><Ban class="size-4" /> Cancelar nota</button>
			</template>
		</Modal>

		<CadastroFiscal v-if="cadastro" :tipo-parte="n.tipo_parte" :parte="n.parte" @fechar="cadastro = false" @salvo="cadastro = false" />
		<Resultado v-if="resultado" :resultado="resultado" @fechar="resultado = null; router.push('/')" @abrir-nota="(id) => { resultado = null; router.push(`/notas/${id}`) }" />
	</div>
</template>
