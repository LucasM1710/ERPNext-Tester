<script setup>
import { BookOpen, ChevronDown } from "lucide-vue-next"
import { computed, ref } from "vue"
import { eTecnico, store } from "@/store"

const aberta = ref(location.hash.slice(1) || "abrir")
const emailTi = computed(() => store.contexto.email_ti || "o e-mail da TI")

// Cada seção: id, título, público ("todos" | "ti") e conteúdo em HTML simples.
const SECOES = computed(() =>
	[
		{
			id: "abrir",
			titulo: "Como abrir um chamado",
			publico: "todos",
			html: `
<ol>
<li>Clique em <b>Abrir chamado</b> (menu lateral) ou escolha a categoria na tela inicial.</li>
<li>Escolha <b>sobre o que é</b> (Acesso e Senha, Computador, E-mail e Microsoft 365, Impressora…). Na dúvida, use <b>Outros</b>.</li>
<li>Escreva um <b>título curto</b> e descreva o que acontece: o que você estava fazendo, a mensagem de erro, desde quando.</li>
<li><b>Anexe prints</b>: arraste o arquivo, clique para escolher ou simplesmente <b>cole com Ctrl+V</b> um print tirado com <kbd>Win</kbd>+<kbd>Shift</kbd>+<kbd>S</kbd>.</li>
<li>Responda <b>quanto isso atrapalha</b> seu trabalho — é isso que define a prioridade e o prazo de atendimento.</li>
</ol>
<p>Também dá para abrir chamado <b>enviando um e-mail</b> para ${emailTi.value}: o assunto vira o título e o texto vira a descrição.</p>`,
		},
		{
			id: "acompanhar",
			titulo: "Acompanhar, responder e anexar",
			publico: "todos",
			html: `
<ul>
<li>Em <b>Meus chamados</b> você vê tudo o que pediu e a situação de cada um.</li>
<li>A conversa funciona como um chat: escreva e envie (atalho <kbd>Ctrl</kbd>+<kbd>Enter</kbd>). Você recebe por e-mail cada resposta da TI e <b>pode responder pelo próprio Outlook</b> — a resposta entra no chamado.</li>
<li><b>"Aguardando sua resposta"</b>: a TI precisa de uma informação sua. Enquanto isso, o prazo de resolução fica pausado. Responda para o atendimento continuar.</li>
<li>Não precisa mais? Enquanto ninguém começou o atendimento, use <b>Cancelar chamado</b>.</li>
</ul>`,
		},
		{
			id: "avaliar",
			titulo: "Resolvido: avaliar ou reabrir",
			publico: "todos",
			html: `
<p>Quando a TI resolve, você recebe a <b>solução aplicada</b> e um pedido de avaliação (1 a 5 estrelas, leva 5 segundos). As avaliações mostram o que está funcionando e o que precisa melhorar.</p>
<p>Se o problema voltar, clique em <b>Não resolveu / Reabrir</b> e conte o que ainda acontece. Chamados resolvidos sem retorno são <b>fechados automaticamente</b> após alguns dias úteis.</p>`,
		},
		{
			id: "prazos",
			titulo: "Prioridades e prazos (SLA)",
			publico: "todos",
			html: `
<p>Cada chamado tem dois prazos, contados em <b>horas úteis</b> (expediente da TI, sem fins de semana e feriados):</p>
<table><thead><tr><th>Prioridade</th><th>Quando</th><th>1ª resposta</th><th>Resolução</th></tr></thead><tbody>
${(store.contexto.prazos || [])
	.map((p) => `<tr><td><b>${p.prioridade}</b></td><td>${p.quando}</td><td>${p.resposta} h</td><td>${p.resolucao} h</td></tr>`)
	.join("")}
</tbody></table>
<p>A TI pode ajustar a prioridade depois de analisar; nesse caso os prazos são recalculados.</p>`,
		},
		{
			id: "fila",
			titulo: "Equipe de TI: fila e atendimento",
			publico: "ti",
			html: `
<ul>
<li><b>Distribuição automática</b>: o chamado novo vai para o técnico padrão da categoria ou, se não houver, para quem tem menos chamados em aberto (no empate, quem recebeu menos nos últimos 30 dias).</li>
<li>A <b>Fila</b> é ordenada pelo que vence primeiro: prazos vencidos, depois em risco, depois prioridade. Atualiza sozinha a cada minuto.</li>
<li><b>Assumir</b>, trocar responsável, status, prioridade e categoria ficam no painel lateral do chamado.</li>
<li><b>Nota interna</b> (cadeado): visível só para a TI — use para senhas temporárias, diagnóstico, links internos.</li>
<li><b>Aguardando Usuário</b> pausa o prazo de resolução. Quando o colaborador responde (portal ou e-mail), o chamado volta sozinho para Em Atendimento.</li>
<li><b>Resolver</b> exige descrever a solução: ela vai para o colaborador e vira histórico para casos parecidos.</li>
<li><b>Registrar chamado</b> em nome de outra pessoa (ligação, corredor): no formulário de abertura, campo "Solicitante" e canal Telefone/Presencial. Assim nada fica fora dos indicadores.</li>
<li>Alertas por e-mail: quando um prazo entra <b>em risco</b> (padrão: 80% consumido) e quando <b>vence</b>.</li>
</ul>`,
		},
		{
			id: "indicadores",
			titulo: "Equipe de TI: como ler os indicadores",
			publico: "ti",
			html: `
<table><thead><tr><th>Indicador</th><th>Como é calculado</th><th>Referência</th></tr></thead><tbody>
<tr><td><b>SLA de 1ª resposta</b></td><td>% dos chamados respondidos no período cuja 1ª resposta saiu dentro do prazo</td><td>≥ 90%</td></tr>
<tr><td><b>SLA de resolução</b></td><td>% dos resolvidos no período dentro do prazo de resolução (descontadas as pausas)</td><td>≥ 85%</td></tr>
<tr><td><b>Tempo médio de 1ª resposta</b></td><td>Média, em horas úteis, entre a abertura e a 1ª resposta da TI</td><td>≤ 2 h</td></tr>
<tr><td><b>MTTR</b> (tempo médio de resolução)</td><td>Média, em horas úteis, entre abertura e resolução, sem o tempo aguardando o colaborador</td><td>≤ 8 h</td></tr>
<tr><td><b>CSAT</b> (satisfação)</td><td>Média das notas de 1 a 5; "satisfeitos" = notas 4 e 5</td><td>≥ 4,3</td></tr>
<tr><td><b>FCR</b> (resolução no 1º contato)</td><td>% dos resolvidos com no máximo uma resposta da TI e sem reabertura</td><td>≥ 70%</td></tr>
<tr><td><b>Reabertos</b></td><td>% dos resolvidos que voltaram a ser abertos</td><td>≤ 5%</td></tr>
<tr><td><b>Abertos x resolvidos</b></td><td>Volume diário; abertos acima dos resolvidos por vários dias = fila crescendo</td><td>—</td></tr>
</tbody></table>
<p>As cores dos números seguem essas referências (verde, âmbar, vermelho). Use o gráfico <b>Por categoria</b> para atacar causas recorrentes — ex.: muitos chamados de senha pedem autoatendimento de redefinição no Microsoft 365.</p>`,
		},
		{
			id: "inventario",
			titulo: "Patrimônio: inventário de equipamentos",
			publico: "ti",
			html: `
<ul>
<li>Cada equipamento tem um <b>nome/hostname</b> único (ex.: NB-007), tipo, modelo, série, patrimônio e <b>com quem está</b>.</li>
<li>Os campos de configuração mudam pelo grupo do tipo: <b>Computador</b> (processador, memória, disco, sistema), <b>Rede e Servidores / Impressora</b> (IP, MAC, firmware), <b>Celular</b> (IMEI, linha, operadora).</li>
<li><b>Entregar</b> = escolher a pessoa em "Com quem está": o status vira <i>Em Uso</i> e a troca entra no <b>histórico de responsáveis</b>. <b>Devolver</b> = tirar a pessoa: volta para <i>Em Estoque</i>. Equipamentos coletivos (impressora, switch) ficam Em Uso sem responsável.</li>
<li>Alertas automáticos: <b>fora da garantia</b>, garantia vencendo (60 dias), <b>vida útil vencida</b> e vencendo (6 meses). A vida útil de cada tipo fica em <i>Tipo Equipamento TI</i>.</li>
<li>O colaborador vê os equipamentos que estão com ele na tela inicial e pode escolher um ao abrir chamado; os chamados entram no histórico e no custo do equipamento.</li>
</ul>`,
		},
		{
			id: "upgrades",
			titulo: "Patrimônio: upgrades e manutenções",
			publico: "ti",
			html: `
<p>No equipamento, <b>Manutenção / upgrade</b> substitui a observação da planilha. Escolha o tipo (Upgrade, Corretiva, Preventiva, Formatação, Troca de Peça).</p>
<p>Em upgrades, informe o <b>componente</b> e <b>como ficou</b> (ex.: Memória RAM → 16 GB): o cadastro do equipamento é <b>atualizado sozinho</b> e o valor antigo fica registrado ("8 GB → 16 GB"). O custo soma no <b>custo total</b> do equipamento.</p>
<p>Quando as manutenções passam de 50% do valor de compra, a Central avisa: normalmente vale mais trocar do que consertar.</p>`,
		},
		{
			id: "compras",
			titulo: "Patrimônio: compras de TI (ligadas ao ERP)",
			publico: "ti",
			html: `
<ol>
<li>No ERP, garanta que os itens de TI estejam em <b>Grupos de Item</b> próprios (ex.: TI &gt; Notebooks, TI &gt; Impressoras, TI &gt; Periféricos). Subgrupos contam junto.</li>
<li>Em <i>Tipo Equipamento TI</i>, preencha <b>Grupo de Item no ERP</b> de cada tipo.</li>
<li>Pronto: <b>Compras de TI</b> mostra, por ano, as <b>Notas de Compra lançadas</b> desses grupos — valores, fornecedores e gasto por mês/categoria.</li>
<li>Em cada item comprado, <b>Cadastrar</b>: você só dá o nome de cada unidade; modelo, valor, fornecedor, data e a nota vêm do ERP. Tipos marcados como "controlado em estoque" (mouse, teclado) viram <b>entrada no estoque</b>.</li>
</ol>
<p>A Central só <b>lê</b> as notas; nada é alterado no ERP. Devoluções (notas de retorno) não entram.</p>`,
		},
		{
			id: "estoque",
			titulo: "Patrimônio: estoque de periféricos",
			publico: "ti",
			html: `
<ul>
<li>Itens controlados por <b>quantidade</b> (mouse, teclado, cabos, toner) — não viram equipamento individual.</li>
<li><b>Entregar</b> (saída para uma pessoa), <b>Entrada</b> e <b>Ajuste</b> (diferença da contagem física). O saldo nunca fica negativo.</li>
<li>Abaixo do <b>mínimo</b>, o item fica vermelho e aparece na Visão do gestor: hora de comprar.</li>
</ul>`,
		},
		{
			id: "gestor",
			titulo: "Patrimônio: como ler a visão do gestor",
			publico: "ti",
			html: `
<table><thead><tr><th>Indicador</th><th>O que responde</th></tr></thead><tbody>
<tr><td><b>Valor do parque</b></td><td>Quanto vale (pelo preço pago) o que está ativo</td></tr>
<tr><td><b>Idade média</b></td><td>Quão "velho" está o parque; acima de 4 anos em computadores costuma significar lentidão e falhas</td></tr>
<tr><td><b>Plano de renovação</b></td><td>Quantos equipamentos vencem a vida útil em cada ano e quanto custa repor — base do orçamento</td></tr>
<tr><td><b>Gastos por ano</b></td><td>Compras (do ERP) + manutenções; mostra se o gasto está crescendo e onde</td></tr>
<tr><td><b>Maior custo total</b></td><td>Equipamentos que já custaram mais (compra + consertos): candidatos à troca</td></tr>
<tr><td><b>Modelos que mais dão problema</b></td><td>(Chamados + corretivas) por unidade: critério para a próxima compra</td></tr>
<tr><td><b>Fora da garantia / estoque baixo</b></td><td>Riscos e compras a fazer</td></tr>
</tbody></table>`,
		},
		{
			id: "tv",
			titulo: "Painel na TV",
			publico: "ti",
			html: `
<ol>
<li>Em <b>Indicadores → Modo TV</b>, clique em <b>Gerar link</b> e copie.</li>
<li>Abra o link no navegador da TV. Funciona melhor em <b>Chromecast com Google TV, Fire TV Stick ou um mini PC</b> ligado à TV; navegadores antigos de Smart TV podem não abrir a página.</li>
<li>Clique duas vezes (ou tecla <kbd>F</kbd>) para tela cheia. Setas trocam de slide. A tela não apaga sozinha (onde o navegador permite).</li>
</ol>
<p>Três slides alternados: <b>Atendimento agora</b> (abertos, sem responsável, em risco, vencidos, lista de atenção, equipe), <b>Desempenho do mês</b> (SLA, satisfação, tempo médio, gráfico de 14 dias) e <b>Patrimônio</b> (estoque baixo, garantias vencendo, vida útil, renovação). Atualiza a cada minuto; sem rede, mostra os últimos dados com aviso.</p>
<p><b>Segurança</b>: a TV não fica logada no ERP — o link só mostra este painel. Trate o link como senha; <b>Gerar novo link</b> ou <b>Desativar</b> invalida o anterior na hora. Por padrão não aparecem nomes de colaboradores (ajuste em Configurações → Painel na TV).</p>`,
		},
		{
			id: "orcamento",
			titulo: "Patrimônio: orçamento e custo por colaborador",
			publico: "ti",
			html: `
<p>Em <b>Configurações → Orçamento de TI</b>, informe por ano o valor planejado de <b>compras</b> e de <b>manutenções</b>. A Visão do gestor compara com o realizado (Notas de Compra do ERP + manutenções registradas) e mostra quanto do orçamento já foi usado — vermelho quando passa.</p>
<p>O <b>custo de TI por colaborador</b> divide o gasto do ano pelo número de colaboradores (campo da configuração ou, se vazio, os funcionários ativos do ERP). É o número que a diretoria costuma pedir para comparar com o mercado.</p>`,
		},
		{
			id: "configurar",
			titulo: "Equipe de TI: configurações",
			publico: "ti",
			html: `
<p>Em <b>Configurações</b> (menu lateral → abre <i>Configuracao Central TI</i> no ERP):</p>
<ul>
<li><b>Técnicos</b>: quem atende e quem recebe distribuição automática. Dê também o papel <b>Tecnico TI</b> ao usuário.</li>
<li><b>Prazos por prioridade</b> (horas úteis), <b>expediente</b>, sábado e <b>Lista de Feriados</b> do ERPNext.</li>
<li><b>Alerta de SLA</b> (% do prazo), <b>fechamento automático</b> de resolvidos (dias úteis) e pesquisa de satisfação.</li>
<li><b>Categorias</b>: em <i>Categoria Chamado TI</i> — nome, ícone, descrição, técnico padrão e ordem.</li>
</ul>
<p><b>Colaboradores sem acesso ao ERP</b>: crie o usuário como <i>Website User</i> — ele entra direto na Central, sem ver o restante do sistema. Quem já usa o ERP acessa por <b>/ti</b> (ou pelo menu do usuário).</p>`,
		},
		{
			id: "email",
			titulo: "Equipe de TI: e-mail com Microsoft 365",
			publico: "ti",
			html: `
<p>Uma caixa da TI (ex.: <b>ti@empresa.com.br</b>, pode ser caixa compartilhada) recebe chamados e envia as notificações.</p>
<ol>
<li><b>Microsoft Entra ID</b> (portal.azure.com) → Registros de aplicativo → Novo registro. URI de redirecionamento (Web):
<br><code>https://SEU-ERP/api/method/frappe.integrations.doctype.connected_app.connected_app.callback</code></li>
<li>Em <i>Permissões de API</i> → Microsoft Graph → delegadas: <code>IMAP.AccessAsUser.All</code>, <code>SMTP.Send</code>, <code>offline_access</code> → conceder consentimento do administrador. Crie um <i>segredo do cliente</i>.</li>
<li>No ERP, <b>Connected App</b> → novo: Client ID, Client Secret e OpenID Configuration
<br><code>https://login.microsoftonline.com/ID-DO-TENANT/v2.0/.well-known/openid-configuration</code>; adicione os mesmos escopos e clique em <i>Connect to</i> com a conta da caixa.</li>
<li>No ERP, <b>Email Account</b> → novo: e-mail da TI, método de autenticação <b>OAuth</b> com o Connected App; entrada IMAP <code>outlook.office365.com</code> (993, SSL), saída SMTP <code>smtp.office365.com</code> (587, TLS).</li>
<li>Marque <b>Enable Incoming</b> com <b>Append To = Chamado TI</b> e <b>Enable Outgoing</b> (padrão de saída, se for a única conta).</li>
<li>Em <i>Configurações</i> da Central, preencha <b>E-mail da TI</b>.</li>
</ol>
<p>Teste: envie um e-mail de outra conta para a caixa — em até alguns minutos ele aparece na Fila como chamado (canal E-mail). Os nomes exatos dos campos podem variar conforme a versão do Frappe; a lógica é a mesma.</p>`,
		},
		{
			id: "instalar",
			titulo: "Equipe de TI: instalação e atualização",
			publico: "ti",
			html: `
<p><b>Primeira vez</b> (no servidor):</p>
<pre>bench get-app URL-DO-REPOSITORIO
bench --site SEU-SITE install-app solucoes</pre>
<p><b>A cada atualização</b> (depois do <code>git pull</code> em apps/solucoes):</p>
<pre>bench --site SEU-SITE execute solucoes.setup.instalar
bench restart</pre>
<p>O comando <code>instalar</code> sincroniza os DocTypes, cria o papel Tecnico TI e garante prazos, categorias e tipos padrão (portal e Central de TI juntos) — sem <code>bench migrate</code> e sem <code>bench build</code> (a página já vai compilada no git). Não cria campos em DocTypes nativos.</p>`,
		},
	].filter((s) => s.publico === "todos" || eTecnico()),
)
</script>

<template>
	<div class="mx-auto max-w-3xl space-y-6">
		<div class="flex items-start gap-4">
			<span class="grid size-12 shrink-0 place-items-center rounded-2xl bg-marca-500/10 text-marca-600 dark:text-marca-300"><BookOpen class="size-6" /></span>
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-tinta">Manual da Central de TI</h1>
				<p class="mt-1 text-sm text-suave">Tudo o que você precisa para pedir ajuda à TI{{ eTecnico() ? " — e, para a equipe de TI, como atender, medir e configurar" : "" }}.</p>
			</div>
		</div>

		<div class="space-y-3">
			<section v-for="s in SECOES" :id="s.id" :key="s.id" class="card overflow-hidden">
				<button class="flex w-full items-center gap-3 px-5 py-4 text-left" @click="aberta = aberta === s.id ? '' : s.id">
					<span v-if="s.publico === 'ti'" class="rounded bg-marca-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-marca-700 dark:text-marca-300">TI</span>
					<span class="flex-1 font-semibold text-tinta">{{ s.titulo }}</span>
					<ChevronDown class="size-4 text-suave transition" :class="aberta === s.id && 'rotate-180'" />
				</button>
				<div
					v-if="aberta === s.id"
					class="manual border-t border-borda px-5 py-4 text-sm leading-relaxed text-texto"
					v-html="s.html"
				/>
			</section>
		</div>
	</div>
</template>

<style scoped>
.manual :deep(ol) {
	list-style: decimal;
	padding-left: 1.25rem;
}
.manual :deep(ul) {
	list-style: disc;
	padding-left: 1.25rem;
}
.manual :deep(li) {
	margin: 0.35rem 0;
}
.manual :deep(p) {
	margin: 0.6rem 0;
}
.manual :deep(b) {
	color: var(--tinta);
	font-weight: 600;
}
.manual :deep(kbd),
.manual :deep(code) {
	border: 1px solid var(--borda);
	border-radius: 0.375rem;
	padding: 0 0.3rem;
	font-size: 0.8em;
	background: var(--realce);
}
.manual :deep(pre) {
	background: var(--realce);
	border: 1px solid var(--borda);
	border-radius: 0.75rem;
	padding: 0.75rem 1rem;
	overflow-x: auto;
	font-size: 0.8rem;
}
.manual :deep(table) {
	width: 100%;
	margin: 0.75rem 0;
	border-collapse: collapse;
	font-size: 0.8rem;
}
.manual :deep(th),
.manual :deep(td) {
	border-bottom: 1px solid var(--borda);
	padding: 0.45rem 0.5rem;
	text-align: left;
	vertical-align: top;
}
.manual :deep(th) {
	color: var(--suave);
	font-weight: 600;
}
</style>
