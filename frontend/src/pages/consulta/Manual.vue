<script setup>
// Manual do portal. MANTER ATUALIZADO junto com cada mudança de tela, regra, perfil ou e-mail do portal.
// Capturas em apps/solucoes/solucoes/public/img/manual/ (servidas em /assets/solucoes/img/manual/).
import { BookOpen, Building2, Mail, Printer, UserRound } from "lucide-vue-next"
import { computed, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { api } from "@/api"
import { store } from "@/store"

const ATUALIZADO_EM = "21/10/2026"
const IMG = "/assets/solucoes/img/manual/"

const route = useRoute()
const router = useRouter()
const interno = computed(() => !!store.contexto?.usuario.interno)
const escolha = ref(route.query.parte === "er" ? "er" : "cliente")
// Quem não é da ER sempre vê a parte do cliente, mesmo com ?parte=er no link
const parte = computed(() => (interno.value ? escolha.value : "cliente"))
watch(escolha, (p) => router.replace({ query: p === "er" ? { parte: "er" } : {} }))

const SECOES = {
	cliente: [
		["primeiro-acesso", "Primeiro acesso"],
		["menu", "O que você encontra"],
		["status", "Status e situações"],
		["equipamento", "Ficha do equipamento"],
		["gestor", "Gestor: distritos e equipe"],
		["terceiros", "Equipamentos de terceiros"],
		["historico", "Histórico de atendimento"],
		["duvidas", "Dúvidas frequentes"],
	],
	er: [
		["antes", "Antes de começar"],
		["central", "Passo a passo na Central"],
		["perfis", "Qual perfil escolher"],
		["vinculos", "O que faz aparecer no portal"],
		["conferencia", "Conferência final"],
		["emails", "Modelos de e-mail"],
	],
}
function imprimir() {
	window.print()
}
function ir(id) {
	document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" })
}

// Prévia dos e-mails (parte da ER)
const MODELOS = [
	["convite", "Convite (criar senha)"],
	["acesso_liberado", "Acesso pronto (senha inicial)"],
	["recuperar_senha", "Redefinir senha"],
	["resumo_semanal", "Resumo semanal"],
]
const modelo = ref("convite")
const previa = ref("")
async function carregarPrevia() {
	previa.value = ""
	previa.value = await api("central.previa_email", { modelo: modelo.value })
}
watch([parte, modelo], () => parte.value === "er" && carregarPrevia(), { immediate: true })
</script>

<template>
	<div class="manual space-y-6">
		<!-- Cabeçalho -->
		<section class="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-900 via-brand-700 to-brand-600 p-6 text-white shadow-pop sm:p-8 print:hidden">
			<div class="pointer-events-none absolute -top-24 -right-10 size-72 rounded-full bg-white/5" />
			<div class="relative flex flex-wrap items-end justify-between gap-6">
				<div>
					<p class="flex items-center gap-2 text-sm text-white/70"><BookOpen class="size-4" /> Manual do Portal do Cliente</p>
					<h1 class="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">{{ parte === "er" ? "Liberar o acesso de um cliente" : "Como usar o portal" }}</h1>
					<p class="mt-1 text-sm text-white/75">Atualizado em {{ ATUALIZADO_EM }}</p>
				</div>
				<div class="flex flex-wrap gap-2">
					<div v-if="interno" class="flex rounded-xl bg-white/10 p-1 ring-1 ring-white/20">
						<button class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm" :class="parte === 'cliente' ? 'bg-white text-brand-800' : 'text-white'" @click="escolha = 'cliente'"><UserRound class="size-4" /> Para o cliente</button>
						<button class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm" :class="parte === 'er' ? 'bg-white text-brand-800' : 'text-white'" @click="escolha = 'er'"><Building2 class="size-4" /> Para a ER</button>
					</div>
					<button class="flex items-center gap-1.5 rounded-xl bg-white/10 px-3 py-2 text-sm ring-1 ring-white/20 hover:bg-white/20" @click="imprimir"><Printer class="size-4" /> Imprimir / PDF</button>
				</div>
			</div>
		</section>

		<div class="grid gap-6 lg:grid-cols-[220px_1fr]">
			<!-- Índice -->
			<nav class="hidden lg:block print:hidden">
				<div class="sticky top-24 space-y-1">
					<p class="px-3 pb-2 text-[10px] font-semibold tracking-widest text-slate-400 uppercase">Nesta página</p>
					<button v-for="[id, titulo] in SECOES[parte]" :key="id" class="block w-full rounded-lg px-3 py-1.5 text-left text-sm text-slate-600 hover:bg-brand-50 hover:text-brand-800" @click="ir(id)">{{ titulo }}</button>
				</div>
			</nav>

			<!-- ====================================================== PARA O CLIENTE -->
			<article v-if="parte === 'cliente'" class="manual-corpo card space-y-10 p-6 sm:p-10">
				<section id="primeiro-acesso">
					<h2>1. Primeiro acesso</h2>
					<p>Você recebe o acesso de duas formas: um <b>convite por e-mail</b> ou uma <b>senha inicial</b> entregue pela ER Analítica.</p>
					<ol>
						<li><b>Convite por e-mail:</b> abra o e-mail “Seu acesso ao Portal do Cliente” e clique em <b>Criar minha senha</b>. O link vale por tempo limitado.</li>
						<li><b>Senha inicial:</b> use o e-mail cadastrado e a senha recebida da nossa equipe.</li>
						<li>Na página de entrada, informe <b>e-mail</b> e <b>senha</b> e clique em <b>Entrar</b>.</li>
						<li>Esqueceu a senha? Clique em <b>Esqueci minha senha</b>, informe o e-mail e siga o link que chegar.</li>
					</ol>
					<figure><img :src="IMG + 'm07-acesso.jpg'" alt="Página de entrada do portal" /><figcaption>Página de entrada do portal</figcaption></figure>
				</section>

				<section id="menu">
					<h2>2. O que você encontra</h2>
					<p>A <b>Visão operacional</b> mostra a saúde do parque: quanto está em dia, o que está crítico ou vencido, os vencimentos do ano e cada distrito. No topo, o seletor de <b>distrito</b> filtra todas as telas.</p>
					<figure><img :src="IMG + 'm08-painel.jpg'" alt="Visão operacional" /><figcaption>Visão operacional</figcaption></figure>
					<table>
						<thead><tr><th>Menu</th><th>Para quê</th></tr></thead>
						<tbody>
							<tr><td>Visão operacional</td><td>Indicadores, gráficos, resumo por distrito e equipamentos urgentes</td></tr>
							<tr><td>Equipamentos</td><td>Todo o parque, com situação, validade, distrito e responsável</td></tr>
							<tr><td>Certificados</td><td>Todos os certificados em PDF, vigentes e anteriores</td></tr>
							<tr><td>Ordens de Serviço</td><td>O andamento de cada OS no laboratório, etapa por etapa</td></tr>
							<tr><td>Relatórios</td><td>Filtros e exportação em Excel e PDF</td></tr>
							<tr><td>Logs de auditoria (Gestor)</td><td>Quem acessou, baixou certificados ou alterou algo</td></tr>
							<tr><td>Distritos e equipe (Gestor)</td><td>Distritos, usuários e distribuição dos equipamentos</td></tr>
						</tbody>
					</table>
					<p class="nota">O perfil <b>Usuário</b> vê apenas Equipamentos, Certificados e Ordens de Serviço dos equipamentos sob sua responsabilidade.</p>
				</section>

				<section id="status">
					<h2>3. Status e situações</h2>
					<p><b>Status de calibração do equipamento</b>, pela data da próxima calibração:</p>
					<table>
						<thead><tr><th>Status</th><th>Significa</th></tr></thead>
						<tbody>
							<tr><td><span class="selo bg-emerald-50 text-emerald-700">Calibrado</span></td><td>Mais de 60 dias de validade</td></tr>
							<tr><td><span class="selo bg-amber-50 text-amber-700">Alerta 60</span></td><td>Vence entre 46 e 60 dias</td></tr>
							<tr><td><span class="selo bg-orange-50 text-orange-700">Crítico</span></td><td>Vence em até 45 dias — programe o envio ao laboratório</td></tr>
							<tr><td><span class="selo bg-rose-50 text-rose-700">Vencido</span></td><td>A validade já passou</td></tr>
							<tr><td><span class="selo bg-brand-50 text-brand-700">Agendado</span></td><td>Em atendimento no laboratório</td></tr>
							<tr><td><span class="selo bg-slate-100 text-slate-600">Sem calibração</span></td><td>Nenhum certificado registrado ainda</td></tr>
						</tbody>
					</table>
					<p><b>Situação do certificado:</b> <b>Vigente</b> (o mais recente, dentro da validade), <b>Vencido</b> (o mais recente, fora da validade) ou <b>Anterior</b> (já substituído por um mais novo).</p>
				</section>

				<section id="equipamento">
					<h2>4. Ficha do equipamento</h2>
					<p>Em <b>Equipamentos</b>, filtre pelos status (Vencido, Crítico…), pelo responsável ou por quem calibra, e clique na linha para abrir a ficha.</p>
					<figure><img :src="IMG + 'm09-equipamentos.jpg'" alt="Lista de equipamentos" /><figcaption>Lista de equipamentos</figcaption></figure>
					<ol>
						<li><b>Topo:</b> situação, próxima calibração e quanto da validade ainda resta.</li>
						<li><b>Histórico de calibrações:</b> cada certificado com data, validade, laboratório e o botão <b>PDF</b>.</li>
						<li><b>Rastreabilidade:</b> os padrões usados na calibração vigente, a validade de cada um e o <b>PDF do certificado do padrão</b>.</li>
						<li><b>Ordens de serviço</b> do equipamento e em que etapa estão.</li>
						<li><b>Etiqueta com QR:</b> imprime uma etiqueta para colar no equipamento.</li>
					</ol>
					<figure><img :src="IMG + 'm10-equipamento.jpg'" alt="Ficha do equipamento" /><figcaption>Ficha do equipamento</figcaption></figure>
					<p>Em <b>Certificados</b> ficam todos os certificados do parque, com busca e as abas Vigentes e Vencidos.</p>
					<figure><img :src="IMG + 'm11-certificados.jpg'" alt="Certificados" /><figcaption>Certificados</figcaption></figure>
				</section>

				<section id="gestor">
					<h2>5. Gestor: distritos e equipe</h2>
					<figure><img :src="IMG + 'm12-gestao.jpg'" alt="Distritos e equipe" /><figcaption>Distritos e equipe</figcaption></figure>
					<ul>
						<li><b>Distritos:</b> <b>Novo distrito</b> ou o lápis para editar nome, responsável, cidade e UF. O aviso amarelo mostra equipamentos sem distrito; <b>Organizar agora</b> distribui vários de uma vez.</li>
						<li><b>Equipe:</b> <b>Convidar</b>, informe o e-mail e o perfil — <b>Líder</b> com os distritos dele ou <b>Usuário</b> com os equipamentos dele. A pessoa recebe o convite por e-mail.</li>
					</ul>
					<table>
						<thead><tr><th>Perfil</th><th>Vê</th><th>Pode</th></tr></thead>
						<tbody>
							<tr><td><b>Gestor</b></td><td>Todo o parque</td><td>Distritos, equipe, terceiros, observações, relatórios e logs</td></tr>
							<tr><td><b>Líder</b></td><td>Só os distritos atribuídos</td><td>Terceiros e observações nos seus distritos; relatórios</td></tr>
							<tr><td><b>Usuário</b></td><td>Só os equipamentos sob sua responsabilidade</td><td>Somente consulta</td></tr>
						</tbody>
					</table>
				</section>

				<section id="terceiros">
					<h2>6. Equipamentos de terceiros</h2>
					<p>Gestor e Líder podem acompanhar no portal também os instrumentos calibrados por <b>outros laboratórios</b>:</p>
					<ol>
						<li>Em <b>Equipamentos</b>, clique em <b>Equipamento de terceiro</b> e cadastre o instrumento e o laboratório.</li>
						<li>Na ficha dele, clique em <b>Enviar certificado</b> e anexe o PDF com número, laboratório e datas.</li>
						<li>A validade passa a contar na Visão operacional e nos relatórios.</li>
					</ol>
					<p class="nota">Nos equipamentos calibrados pela ER Analítica, você pode anotar uma <b>Observação</b> (onde fica, quem usa). Ela não altera os dados do laboratório.</p>
				</section>

				<section id="historico">
					<h2>7. Histórico de atendimento</h2>
					<p>Para <b>Gestor</b> e <b>Líder</b>, a ER Analítica pode liberar o histórico dos seus atendimentos: os registros do que foi combinado, agendado e realizado em cada contrato ou serviço.</p>
					<ol>
						<li>Quando liberado, aparece no menu o item <b>Histórico de atendimento</b>.</li>
						<li>À esquerda ficam os atendimentos; clique em um para ver os registros, do mais recente para o mais antigo.</li>
						<li>Use a busca para achar um assunto, número de série ou data em todos os registros.</li>
					</ol>
					<p class="nota">Você vê apenas os atendimentos liberados para o seu acesso. Precisa de outro? Fale com a ER Analítica.</p>
				</section>

				<section id="duvidas">
					<h2>8. Dúvidas frequentes</h2>
					<table>
						<thead><tr><th>Situação</th><th>O que fazer</th></tr></thead>
						<tbody>
							<tr><td>Não vejo nenhum equipamento</td><td>Confira se o seletor de distrito no topo está em “Todos os distritos”. Se continuar, fale com o Gestor da sua empresa ou com a ER Analítica.</td></tr>
							<tr><td>O convite não chegou</td><td>Verifique o spam ou peça uma senha inicial à ER Analítica.</td></tr>
							<tr><td>Esqueci minha senha</td><td>“Esqueci minha senha” na página de entrada.</td></tr>
							<tr><td>Um colega saiu da empresa</td><td>O Gestor desativa o acesso em Distritos e equipe → Equipe.</td></tr>
							<tr><td>Um equipamento aparece “Sem calibração”</td><td>Fale com a ER Analítica: o certificado pode ainda não ter sido anexado.</td></tr>
						</tbody>
					</table>
				</section>
			</article>

			<!-- ====================================================== PARA A ER -->
			<article v-else-if="interno" class="manual-corpo card space-y-10 p-6 sm:p-10">
				<section id="antes">
					<h2>1. Antes de começar</h2>
					<p>Tudo parte do cadastro do cliente no ERP. Confira se ele já tem:</p>
					<table>
						<thead><tr><th>O que conferir</th><th>Onde</th><th>Por que importa</th></tr></thead>
						<tbody>
							<tr><td>CNPJ e IE</td><td>Vendas → Cliente</td><td>É a raiz de tudo o que aparece no portal</td></tr>
							<tr><td>Contato com e-mail</td><td>Cliente → Endereço e Contato</td><td>A OS exige contato; o e-mail vira o login</td></tr>
							<tr><td>Endereços das unidades (opcional)</td><td>Cliente → Endereço e Contato</td><td>Cada endereço vira um distrito com um clique</td></tr>
						</tbody>
					</table>
					<p>Abra o cliente e clique em <b>Portal do cliente</b> (abre a Central já nele) ou em <b>Manual do portal</b> (esta página).</p>
					<figure><img :src="IMG + 'm01-cliente-erp.jpg'" alt="Botão Portal do cliente no cadastro" /><figcaption>Botões no cadastro do cliente</figcaption></figure>
				</section>

				<section id="central">
					<h2>2. Passo a passo na Central do portal</h2>
					<p>Seis etapas da esquerda para a direita. <b>✓ verde</b> = pronta; <b>número amarelo</b> = pendências.</p>
					<h3>Etapa 1 — Portal</h3>
					<p>Marque <b>Controle por distritos</b> se o cliente tem filiais ou setores que devem ver só o que é deles. Se pular, o portal é liberado sozinho no primeiro acesso criado.</p>
					<figure><img :src="IMG + 'm02-central-portal.jpg'" alt="Etapa Portal" /></figure>
					<h3>Etapa 2 — Contatos</h3>
					<p><b>Dar acesso</b> ao lado de um contato abre o cadastro do acesso já com nome e e-mail.</p>
					<h3>Etapa 3 — Distritos</h3>
					<p><b>Criar distritos pelos endereços</b> transforma cada endereço em distrito (cidade e UF). Depois, <b>Editar</b> cada um e informar o responsável (sugere os contatos).</p>
					<figure><img :src="IMG + 'm03-central-distritos.jpg'" alt="Etapa Distritos" /></figure>
					<h3>Etapa 4 — Usuários</h3>
					<ol>
						<li><b>Novo acesso</b>: e-mail (sugere os contatos) e nome.</li>
						<li>Perfil — o primeiro do cliente já vem como <b>Gestor</b>.</li>
						<li><b>Líder:</b> marque os distritos. <b>Usuário:</b> marque os equipamentos.</li>
						<li><b>Histórico de atendimento</b> (só Gestor/Líder, opcional): marque <b>Habilitar histórico de atendimento</b> e escolha as oportunidades cujas notas ele vai ver. A lista já vem só com as oportunidades do cliente; filtre pelo <b>e-mail do contato</b> (ou “Só do e-mail deste acesso”), por status ou por texto, e marque uma a uma ou <b>marcar todas</b> as filtradas. “Só as liberadas” mostra o que já está marcado. Nada antigo entra sem ser escolhido.</li>
						<li><b>Senha inicial:</b> em branco envia o convite por e-mail; preenchida, envia só o aviso “acesso pronto” (a senha nunca vai por e-mail).</li>
						<li><b>Salvar acesso</b>.</li>
					</ol>
					<figure><img :src="IMG + 'm04-central-usuarios.jpg'" alt="Etapa Usuários" /></figure>
					<h3>Etapa 5 — Equipamentos</h3>
					<p>Distrito e dono direto na linha, ou em massa: marque as caixas e use <b>Mover para o distrito</b> / <b>Definir dono</b>. Filtros <b>Sem distrito</b> e <b>Sem dono</b> mostram o que falta.</p>
					<figure><img :src="IMG + 'm05-central-equipamentos.jpg'" alt="Etapa Equipamentos" /></figure>
					<h3>Etapa 6 — OS e certificados</h3>
					<p>OS <b>sem equipamento ligado</b> (sugestão pela série ou TAG → <b>Ligar</b>) e OS <b>encerradas sem certificado</b> (abrir a OS e anexar o PDF).</p>
					<figure><img :src="IMG + 'm06-central-os.jpg'" alt="Etapa OS e certificados" /></figure>
				</section>

				<section id="perfis">
					<h2>3. Qual perfil escolher</h2>
					<table>
						<thead><tr><th>Perfil</th><th>Para quem</th><th>Vê</th><th>Pode</th></tr></thead>
						<tbody>
							<tr><td><b>Gestor</b></td><td>Responsável do cliente pelo parque</td><td>Tudo, inclusive sem distrito</td><td>Distritos, equipe, terceiros, observações, relatórios, logs</td></tr>
							<tr><td><b>Líder</b></td><td>Filial, unidade ou setor</td><td>Só os distritos marcados (mín. 1)</td><td>Terceiros e observações nos seus distritos; relatórios</td></tr>
							<tr><td><b>Usuário</b></td><td>Quem responde por alguns equipamentos</td><td>Só os equipamentos dos quais é dono (mín. 1)</td><td>Somente consulta</td></tr>
						</tbody>
					</table>
					<p class="nota">Cliente sem controle por distritos: o Líder vê o parque inteiro. Um e-mail pode ter acesso a mais de um cliente. O <b>histórico de atendimento</b> é liberado à parte, por oportunidade, e só para Gestor ou Líder.</p>
					<p class="nota">Atenção: tudo o que for escrito na aba <b>Comentários</b> de uma oportunidade liberada — inclusive notas futuras — aparece para o cliente. Escreva sabendo disso.</p>
				</section>

				<section id="vinculos">
					<h2>4. O que faz o equipamento e a OS aparecerem certos</h2>
					<table>
						<thead><tr><th>No portal aparece…</th><th>…quando no ERP</th><th>Campo</th></tr></thead>
						<tbody>
							<tr><td>O equipamento</td><td>Salvo com o cliente</td><td>Equipamentos → Cliente</td></tr>
							<tr><td>Marca, grandeza, tipo, capacidade</td><td>O modelo tem a ficha</td><td>Equipamentos → Modelo</td></tr>
							<tr><td>A OS no histórico</td><td>A OS aponta para o equipamento</td><td>OS → Digite o número de série do equipamento</td></tr>
							<tr><td>Última e próxima calibração</td><td>OS Encerrada com a data</td><td>OS → Data da Calibração (+365 = recomendada)</td></tr>
							<tr><td>Certificado em PDF</td><td>PDF anexado na OS encerrada</td><td>OS → Anexar Certificado</td></tr>
							<tr><td>Selo RBC</td><td>Calibração RBC</td><td>OS → CALIBRAÇÃO RBC</td></tr>
							<tr><td>Padrões e PDF de cada um</td><td>Lidos do PDF ao anexar</td><td>OS → Rastreabilidade dos Padrões</td></tr>
							<tr><td>Status “Agendado”</td><td>OS em aberto</td><td>Status da OS (regra em definição)</td></tr>
							<tr><td>Histórico de atendimento</td><td>Oportunidade do cliente (Customer, não Lead) liberada no acesso</td><td>Oportunidade → aba Comentários (notas)</td></tr>
						</tbody>
					</table>
				</section>

				<section id="conferencia">
					<h2>5. Conferência antes de avisar o cliente</h2>
					<ul class="checklist">
						<li>Central com <b>6/6 etapas sem pendência</b></li>
						<li>O Gestor tem o e-mail correto</li>
						<li>Todos os equipamentos com distrito (se usa distritos)</li>
						<li>Cada Usuário com os equipamentos dele</li>
						<li>OS encerradas com certificado anexado</li>
						<li>Senha inicial (se houver) passada por canal seguro</li>
					</ul>
					<p>Sem abrir a Central: cadastro do cliente → aba <b>Dashboard</b> → seções <b>Equipamentos e OS</b> e <b>Portal do cliente</b>.</p>
				</section>

				<section id="emails">
					<h2 class="flex items-center gap-2"><Mail class="size-5 text-brand-600" /> 6. Modelos de e-mail</h2>
					<p>O portal envia estes e-mails com a marca da ER. Remetente: <b>portal@eranalitica.com.br</b> quando a conta existir no ERP; senão, a conta padrão de saída. Uma falha de e-mail nunca impede o cadastro.</p>
					<div class="flex flex-wrap gap-2">
						<button v-for="[id, nome] in MODELOS" :key="id" class="chip" :class="modelo === id ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-200 bg-white text-slate-600'" @click="modelo = id">{{ nome }}</button>
					</div>
					<iframe v-if="previa" :srcdoc="previa" title="Prévia do e-mail" class="mt-4 h-[640px] w-full rounded-2xl border border-slate-200 bg-slate-100" />
					<p v-else class="mt-4 text-sm text-slate-500">Carregando prévia…</p>
				</section>
			</article>
		</div>
	</div>
</template>

<style scoped>
.manual-corpo h2 { font-size: 1.35rem; font-weight: 600; color: #0f172a; letter-spacing: -0.01em; margin-bottom: 0.75rem; scroll-margin-top: 6rem; }
.manual-corpo h3 { font-size: 1rem; font-weight: 600; color: #063e5e; margin: 1.25rem 0 0.4rem; }
.manual-corpo section { scroll-margin-top: 6rem; }
.manual-corpo p { color: #334155; line-height: 1.7; margin: 0.5rem 0; }
.manual-corpo ol, .manual-corpo ul { margin: 0.75rem 0; padding-left: 1.4rem; color: #334155; line-height: 1.7; }
.manual-corpo ol { list-style: decimal; }
.manual-corpo ul { list-style: disc; }
.manual-corpo li { margin: 0.25rem 0; }
.manual-corpo ul.checklist { list-style: none; padding-left: 0; }
.manual-corpo ul.checklist li::before { content: "☐"; color: #045a88; margin-right: 0.6rem; }
.manual-corpo table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.875rem; }
.manual-corpo th { text-align: left; background: #045a88; color: #fff; font-weight: 600; padding: 0.6rem 0.8rem; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; }
.manual-corpo td { padding: 0.6rem 0.8rem; border-bottom: 1px solid #eef2f7; color: #334155; vertical-align: top; }
.manual-corpo figure { margin: 1.25rem 0; }
.manual-corpo img { width: 100%; border-radius: 1rem; border: 1px solid #e2e8f0; box-shadow: 0 10px 30px -18px rgb(15 23 42 / 0.35); }
.manual-corpo figcaption { font-size: 0.75rem; color: #64748b; margin-top: 0.4rem; text-align: center; }
.manual-corpo .nota { background: #eef7fb; border-left: 3px solid #009bdb; padding: 0.7rem 0.9rem; border-radius: 0.6rem; color: #063e5e; }
.manual-corpo .selo { display: inline-block; border-radius: 999px; padding: 0.1rem 0.6rem; font-size: 0.75rem; font-weight: 600; }
@media print {
	.manual-corpo { box-shadow: none; border: 0; padding: 0; }
	.manual-corpo img { break-inside: avoid; }
}
</style>
