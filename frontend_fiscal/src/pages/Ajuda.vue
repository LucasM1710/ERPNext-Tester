<script setup>
import { ChevronDown } from "lucide-vue-next"
import { ref } from "vue"

const aberta = ref(0)
const PASSOS = [
	["A fatura é confirmada no ERP", "O comercial ou o faturamento confirma a fatura de venda (Sales Invoice) normalmente. Ela aparece sozinha em Para emitir."],
	["O sistema confere tudo", "Para cada fatura, ele decide o que emitir (serviço vira NFS-e, produto vira NF-e), calcula impostos e retenções e confere o cadastro do cliente. O verde está certo, o amarelo é aviso e o vermelho precisa ser ajustado."],
	["Você ajusta o que estiver vermelho", "Quase sempre é o cadastro fiscal do cliente: clique em Completar cadastro. Digite o CEP para o endereço vir sozinho, ou use Buscar para puxar os dados da Receita pelo CNPJ."],
	["Você clica em Emitir", "Confira o resumo e confirme. A nota é transmitida, o boleto com Pix é gerado e tudo vai por e-mail ao cliente."],
	["O cliente paga e o sistema dá baixa", "Quando o banco avisa o pagamento, o boleto fica Pago e o recebimento é lançado na fatura do ERP. Boletos vencidos recebem cobrança automática."],
]
const GLOSSARIO = [
	["NFS-e", "Nota fiscal de serviço (calibração, manutenção). É da prefeitura e, a partir de 2026, segue o padrão nacional."],
	["NF-e", "Nota fiscal de mercadoria: venda de produtos e também remessa e retorno de equipamentos. É da SEFAZ do estado."],
	["DANFE / DANFSe", "A versão impressa (PDF) da NF-e / NFS-e. O documento que vale é o XML."],
	["Chave de acesso", "Número de 44 dígitos (NF-e) que identifica a nota em todo o Brasil. O último dígito confere os outros, por isso o sistema sabe quando foi digitado errado."],
	["CFOP", "Código que diz o tipo da operação: 5102 venda, 5915 remessa para conserto, 5916 retorno de conserto. Começa com 5 dentro do estado e com 6 para outro estado."],
	["Retenção", "Imposto que o próprio cliente desconta e recolhe (ISS, PIS, COFINS, CSLL, IR). Por isso o boleto pode sair menor que a fatura: está certo."],
	["Remessa e retorno", "Notas que acompanham o equipamento quando ele sai ou volta sem ser vendido. Não geram cobrança. O imposto fica suspenso, por isso o prazo de retorno é acompanhado."],
	["Homologação", "Ambiente de testes oficial: tudo funciona como de verdade, mas sem valor fiscal."],
	["CBS e IBS", "Novos impostos da reforma tributária. Em 2026 aparecem nas notas só como informação (alíquotas de teste) e não são cobrados."],
]
const DUVIDAS = [
	["A nota voltou rejeitada. E agora?", "O aviso vermelho em Para emitir diz o motivo e o que fazer. Corrija (geralmente o cadastro) e clique em Tentar de novo: a nota rejeitada fica no histórico e uma nova é enviada."],
	["Errei a nota. Posso cancelar?", "Sim. Na nota, clique em Cancelar e escreva o motivo (mínimo 15 letras). NF-e: até 24 horas depois da emissão. NFS-e: depende da prefeitura. O boleto em aberto é cancelado junto. Depois emita de novo pela fatura."],
	["O cliente pediu outro vencimento", "Em Boletos, use Prorrogar (2ª via): sai um boleto novo com a nova data e o antigo é cancelado."],
	["O cliente pagou por transferência", "Em Boletos, use Marcar como pago. O recebimento é lançado na fatura."],
	["Chegou um equipamento do cliente com nota", "Guarde a chave da nota dele. Quando o equipamento estiver pronto, vá em Remessa e retorno > Devolver equipamento ao cliente e informe essa chave. O serviço é cobrado à parte, pela fatura (NFS-e)."],
	["Vamos mandar um padrão para calibrar fora", "Remessa e retorno > Enviar equipamento nosso para fora. Ele fica em Nossos equipamentos fora da empresa até você clicar em Chegou de volta."],
	["Uma fatura não aparece em Para emitir", "Confira se ela está confirmada no ERP e se é de depois da data inicial da configuração fiscal. Faturas que já têm boleto não aparecem."],
]
</script>

<template>
	<div class="mx-auto max-w-3xl space-y-8">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight text-tinta">Manual</h1>
			<p class="mt-1 text-sm text-suave">Como emitir notas e boletos, do começo ao fim, e o que fazer quando algo dá errado.</p>
		</div>

		<section>
			<h2 class="mb-3 text-sm font-semibold text-tinta">O caminho de uma fatura</h2>
			<ol class="space-y-3">
				<li v-for="([t, d], k) in PASSOS" :key="k" class="card flex gap-4 p-4">
					<span class="grid size-8 shrink-0 place-items-center rounded-full bg-marca-600 text-sm font-semibold text-white">{{ k + 1 }}</span>
					<div><p class="font-medium text-tinta">{{ t }}</p><p class="mt-0.5 text-sm text-suave">{{ d }}</p></div>
				</li>
			</ol>
		</section>

		<section>
			<h2 class="mb-3 text-sm font-semibold text-tinta">Perguntas frequentes</h2>
			<div class="card divide-y divide-borda">
				<div v-for="([q, r], k) in DUVIDAS" :key="k">
					<button class="flex w-full items-center gap-3 px-4 py-3 text-left text-sm font-medium text-tinta" @click="aberta = aberta === k ? -1 : k">
						<span class="flex-1">{{ q }}</span><ChevronDown class="size-4 text-suave transition" :class="aberta === k && 'rotate-180'" />
					</button>
					<p v-if="aberta === k" class="px-4 pb-4 text-sm text-suave">{{ r }}</p>
				</div>
			</div>
		</section>

		<section>
			<h2 class="mb-3 text-sm font-semibold text-tinta">Palavras que aparecem no sistema</h2>
			<dl class="card divide-y divide-borda">
				<div v-for="[t, d] in GLOSSARIO" :key="t" class="grid gap-1 px-4 py-3 sm:grid-cols-4">
					<dt class="text-sm font-semibold text-tinta">{{ t }}</dt>
					<dd class="text-sm text-suave sm:col-span-3">{{ d }}</dd>
				</div>
			</dl>
		</section>

		<section class="card space-y-2 p-5 text-sm text-suave">
			<h2 class="text-sm font-semibold text-tinta">Para a TI</h2>
			<p>Módulo <b>Fiscal</b> do app <code>solucoes</code>. Instalação e atualização: <code>bench --site SEU-SITE execute solucoes.setup.instalar</code> (sem migrate nem build: o build vai no git).</p>
			<p>Configuração: <code>/app/configuracao-fiscal</code>. Naturezas de operação (CFOP/CSOSN): <code>/app/natureza-operacao-fiscal</code>. Os valores de imposto vêm da configuração, que o contador valida.</p>
			<p>Demonstração (só em Simulação, nunca em produção): <code>execute solucoes.fiscal.demo.criar</code> e, para apagar, <code>solucoes.fiscal.demo.apagar</code>.</p>
			<p>Provedores reais: <code>solucoes/fiscal/provedores.py</code>. Basta uma classe com <code>emitir</code>/<code>cancelar</code> (notas) ou <code>registrar</code>/<code>cancelar</code> (boletos).</p>
		</section>
	</div>
</template>
