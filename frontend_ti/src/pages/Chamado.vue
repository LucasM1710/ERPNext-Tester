<script setup>
import {
	ArrowLeft,
	Ban,
	CheckCheck,
	CircleCheckBig,
	Clock,
	FileText,
	Hand,
	Lock,
	RotateCcw,
	Send,
} from "lucide-vue-next"
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue"
import { useRoute } from "vue-router"
import { api, urlAnexo } from "@/api"
import Anexador from "@/components/Anexador.vue"
import Avatar from "@/components/Avatar.vue"
import Esqueleto from "@/components/Esqueleto.vue"
import Estrelas from "@/components/Estrelas.vue"
import Etiqueta from "@/components/Etiqueta.vue"
import IconeCategoria from "@/components/IconeCategoria.vue"
import IconeEquipamento from "@/components/IconeEquipamento.vue"
import Modal from "@/components/Modal.vue"
import { dataHora, horas, prazo, relativo, tamanho, textoParaHtml } from "@/format"
import { store, toast } from "@/store"

const props = defineProps({ id: String })
const route = useRoute()
const c = ref(null)
const erro = ref(null)
const texto = ref("")
const anexos = ref([])
const interna = ref(false)
const enviando = ref(false)
const nota = ref(0)
const comentario = ref("")
const modal = ref(null) // "resolver" | "reabrir" | "cancelar"
const solucao = ref("")
const motivo = ref("")
const fimConversa = ref(null)
const avaliacaoRef = ref(null)

async function carregar(rolar = false) {
	try {
		c.value = await api("chamado", { id: props.id })
		if (rolar) {
			await nextTick()
			if (route.query.avaliar && avaliacaoRef.value) avaliacaoRef.value.scrollIntoView({ behavior: "smooth", block: "center" })
		}
	} catch (e) {
		erro.value = e.message
	}
}
let relogio
onMounted(() => {
	carregar(true)
	// atualiza sozinho enquanto a aba está visível (resposta da outra parte aparece sem recarregar)
	relogio = setInterval(() => document.visibilityState === "visible" && !enviando.value && carregar(), 30000)
})
onBeforeUnmount(() => clearInterval(relogio))

const tecnico = computed(() => c.value?.pode.gerenciar)
const porUrl = computed(() => Object.fromEntries((c.value?.anexos || []).map((a) => [a.url, a])))

async function acao(metodo, params, msg) {
	enviando.value = true
	try {
		c.value = await api(metodo, { id: props.id, ...params }, { post: true })
		if (msg) toast(msg)
		modal.value = null
		return true
	} catch (e) {
		toast(e.message, "erro")
		return false
	} finally {
		enviando.value = false
	}
}

async function responder() {
	if (!texto.value.trim() && !anexos.value.length) return
	enviando.value = true
	try {
		c.value = await api(
			"responder",
			{ id: props.id, mensagem: texto.value.trim() ? textoParaHtml(texto.value) : "<p>(anexo)</p>", interna: interna.value ? 1 : 0 },
			{ post: true, arquivos: anexos.value },
		)
		texto.value = ""
		anexos.value = []
		await nextTick()
		fimConversa.value?.scrollIntoView({ behavior: "smooth", block: "end" })
	} catch (e) {
		toast(e.message, "erro")
	} finally {
		enviando.value = false
	}
}

function tecla(e) {
	if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) responder()
}

// barra de prazo: fração do tempo (corrido) já consumida entre a abertura e o prazo
function consumo(fim, concluidoEm) {
	if (!c.value || !fim) return 0
	const ini = new Date(c.value.aberto_em.replace(" ", "T"))
	const ate = new Date(fim.replace(" ", "T"))
	const agora = concluidoEm ? new Date(concluidoEm.replace(" ", "T")) : new Date()
	return Math.max(0, Math.min(100, Math.round((100 * (agora - ini)) / (ate - ini || 1))))
}
const COR_SLA = { "No Prazo": "bg-emerald-500", "Em Risco": "bg-amber-500", Violado: "bg-rose-500", Cumprido: "bg-emerald-500" }
</script>

<template>
	<div class="space-y-5">
		<RouterLink :to="tecnico ? '/fila' : '/chamados'" class="inline-flex items-center gap-1.5 text-sm text-suave hover:text-tinta">
			<ArrowLeft class="size-4" /> {{ tecnico ? "Fila de atendimento" : "Meus chamados" }}
		</RouterLink>

		<div v-if="erro" class="card p-6 text-sm text-rose-600">{{ erro }}</div>
		<div v-else-if="!c" class="card p-6"><Esqueleto :linhas="8" /></div>

		<template v-else>
			<!-- Cabeçalho -->
			<div class="card flex flex-wrap items-start gap-4 p-5">
				<span class="grid size-12 shrink-0 place-items-center rounded-2xl bg-marca-500/10 text-marca-600 dark:text-marca-300"><IconeCategoria :nome="c.icone" class="size-6" /></span>
				<div class="min-w-0 flex-1">
					<p class="font-mono text-xs text-suave">{{ c.id }} · {{ c.categoria || "Sem categoria" }}</p>
					<h1 class="mt-0.5 text-xl font-semibold tracking-tight text-tinta">{{ c.assunto }}</h1>
					<div class="mt-2 flex flex-wrap gap-2">
						<Etiqueta :valor="c.status" />
						<Etiqueta :valor="c.prioridade" :ponto="false">Prioridade {{ c.prioridade }}</Etiqueta>
					</div>
				</div>
			</div>

			<div class="grid gap-5 lg:grid-cols-3">
				<!-- Conversa -->
				<div class="space-y-4 lg:col-span-2">
					<section class="card p-5">
						<ol class="space-y-4">
							<!-- descrição inicial -->
							<li class="flex gap-3">
								<Avatar :nome="c.solicitante_nome" />
								<div class="min-w-0 flex-1">
									<p class="text-sm"><b class="font-semibold text-tinta">{{ c.solicitante_nome }}</b> <span class="text-xs text-suave">abriu o chamado · {{ dataHora(c.aberto_em) }}</span></p>
									<div class="conteudo mt-1.5 rounded-2xl rounded-tl-sm border border-borda bg-realce px-4 py-3 text-sm text-texto" v-html="c.descricao || '<p><i>Sem descrição.</i></p>'" />
								</div>
							</li>

							<template v-for="i in c.interacoes" :key="i.id">
								<li v-if="i.tipo === 'Sistema'" class="flex items-center gap-3 py-0.5 text-xs text-suave">
									<span class="h-px flex-1 bg-borda" />
									<span class="text-center">{{ i.mensagem.replace(/<[^>]+>/g, "") }} · {{ relativo(i.em) }}</span>
									<span class="h-px flex-1 bg-borda" />
								</li>
								<li v-else class="flex gap-3" :class="i.eu && 'flex-row-reverse'">
									<Avatar :nome="i.autor_nome" />
									<div class="min-w-0 max-w-[85%]" :class="i.eu && 'text-right'">
										<p class="text-sm">
											<b class="font-semibold text-tinta">{{ i.eu ? "Você" : i.autor_nome }}</b>
											<span v-if="i.de_tecnico && !i.eu" class="ml-1 rounded bg-marca-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-marca-700 dark:text-marca-300">TI</span>
											<span class="ml-1 text-xs text-suave">{{ relativo(i.em) }}<template v-if="i.via === 'E-mail'"> · por e-mail</template></span>
										</p>
										<div
											class="conteudo mt-1.5 inline-block rounded-2xl px-4 py-3 text-left text-sm"
											:class="
												i.tipo === 'Nota Interna'
													? 'border border-dashed border-amber-500/50 bg-amber-500/10 text-texto'
													: i.eu
														? 'rounded-tr-sm bg-marca-600 text-white [&_a]:text-white'
														: 'rounded-tl-sm border border-borda bg-realce text-texto'
											"
										>
											<p v-if="i.tipo === 'Nota Interna'" class="mb-1 flex items-center gap-1 text-xs font-semibold text-amber-700 dark:text-amber-400"><Lock class="size-3" /> Nota interna · só a TI vê</p>
											<div v-html="i.mensagem" />
											<div v-if="i.anexos.length" class="mt-2 flex flex-wrap gap-1.5">
												<a
													v-for="u in i.anexos.filter((u) => porUrl[u])"
													:key="u"
													:href="urlAnexo(c.id, porUrl[u].id)"
													target="_blank"
													class="inline-flex items-center gap-1 rounded-lg bg-black/10 px-2 py-1 text-xs no-underline"
												>
													<FileText class="size-3.5" /> {{ porUrl[u].nome }}
												</a>
											</div>
										</div>
									</div>
								</li>
							</template>
							<li ref="fimConversa" />
						</ol>
					</section>

					<!-- Avaliação -->
					<section v-if="c.pode.avaliar" ref="avaliacaoRef" class="card border-emerald-500/30 p-5">
						<p class="flex items-center gap-2 font-semibold text-tinta"><CircleCheckBig class="size-5 text-emerald-600" /> A TI marcou este chamado como resolvido</p>
						<div v-if="c.solucao" class="conteudo mt-3 rounded-xl bg-emerald-500/10 px-4 py-3 text-sm text-texto" v-html="c.solucao" />
						<p class="mt-4 text-sm text-suave">Como foi o atendimento?</p>
						<Estrelas v-model="nota" class="mt-1" />
						<textarea v-if="nota" v-model="comentario" rows="2" class="campo mt-3" placeholder="Quer comentar algo? (opcional)" />
						<div class="mt-4 flex flex-wrap gap-2">
							<button class="btn-sucesso" :disabled="!nota || enviando" @click="acao('avaliar', { nota, comentario }, 'Obrigado pela avaliação!')">Enviar avaliação</button>
							<button class="btn-secundario" @click="modal = 'reabrir'"><RotateCcw class="size-4" /> Não resolveu</button>
						</div>
					</section>
					<section v-else-if="c.avaliacao" class="card flex flex-wrap items-center gap-4 p-5">
						<Estrelas :model-value="c.avaliacao" leitura tamanho="size-5" />
						<p class="text-sm text-suave">{{ c.comentario_avaliacao || "Atendimento avaliado." }}</p>
						<button v-if="c.pode.reabrir" class="btn-fantasma ml-auto text-xs" @click="modal = 'reabrir'"><RotateCcw class="size-3.5" /> Reabrir</button>
					</section>

					<!-- Responder -->
					<section v-if="c.pode.responder" class="card p-3" :class="interna && 'border-amber-500/50'">
						<textarea
							v-model="texto"
							rows="3"
							class="w-full resize-y bg-transparent px-2 py-1.5 text-sm text-tinta placeholder:text-suave/70 focus:outline-none"
							:placeholder="interna ? 'Nota interna: só a equipe de TI verá…' : 'Escreva uma mensagem… (Ctrl+Enter envia)'"
							@keydown="tecla"
						/>
						<Anexador v-model="anexos" compacto />
						<div class="flex flex-wrap items-center gap-2 border-t border-borda pt-2">
							<label v-if="tecnico" class="flex cursor-pointer items-center gap-2 px-1 text-xs font-medium" :class="interna ? 'text-amber-600 dark:text-amber-400' : 'text-suave'">
								<input v-model="interna" type="checkbox" class="accent-amber-500" /> <Lock class="size-3.5" /> Nota interna
							</label>
							<button class="btn-primario ml-auto" :disabled="enviando || (!texto.trim() && !anexos.length)" @click="responder">
								<Send class="size-4" /> {{ enviando ? "Enviando…" : "Enviar" }}
							</button>
						</div>
					</section>
					<p v-else class="rounded-xl bg-realce p-4 text-center text-sm text-suave">
						Chamado {{ c.status.toLowerCase() }}.
						<button v-if="c.pode.reabrir" class="font-medium text-marca-600 dark:text-marca-300" @click="modal = 'reabrir'">Reabrir</button>
					</p>
				</div>

				<!-- Lateral -->
				<aside class="space-y-4">
					<!-- Ações da TI -->
					<section v-if="tecnico" class="card space-y-3 p-5">
						<p class="text-xs font-semibold tracking-wider text-suave uppercase">Atendimento</p>
						<button
							v-if="c.responsavel !== store.contexto.usuario.email && c.aberto"
							class="btn-secundario w-full"
							@click="acao('alterar', { responsavel: store.contexto.usuario.email, status: c.status === 'Aberto' ? 'Em Atendimento' : null }, 'Chamado assumido.')"
						>
							<Hand class="size-4" /> Assumir chamado
						</button>
						<div>
							<label class="rotulo">Responsável</label>
							<select class="campo" :value="c.responsavel || ''" @change="acao('alterar', { responsavel: $event.target.value || '-' })">
								<option value="">— sem responsável —</option>
								<option v-for="t in store.contexto.tecnicos" :key="t.id" :value="t.id">{{ t.nome }}</option>
							</select>
						</div>
						<div class="grid grid-cols-2 gap-2">
							<div>
								<label class="rotulo">Status</label>
								<select class="campo" :value="c.status" :disabled="!c.aberto" @change="acao('alterar', { status: $event.target.value })">
									<option>Aberto</option><option>Em Atendimento</option><option>Aguardando Usuário</option>
									<option v-if="!c.aberto">{{ c.status }}</option>
								</select>
							</div>
							<div>
								<label class="rotulo">Prioridade</label>
								<select class="campo" :value="c.prioridade" @change="acao('alterar', { prioridade: $event.target.value }, 'Prioridade alterada; prazos recalculados.')">
									<option>Crítica</option><option>Alta</option><option>Média</option><option>Baixa</option>
								</select>
							</div>
						</div>
						<div>
							<label class="rotulo">Categoria</label>
							<select class="campo" :value="c.categoria || ''" @change="acao('alterar', { categoria: $event.target.value })">
								<option v-for="cat in store.contexto.categorias" :key="cat.nome">{{ cat.nome }}</option>
							</select>
						</div>
						<div v-if="c.aberto" class="flex gap-2 pt-1">
							<button class="btn-sucesso flex-1" @click="(solucao = ''), (modal = 'resolver')"><CheckCheck class="size-4" /> Resolver</button>
							<button class="btn-secundario" title="Cancelar chamado" @click="modal = 'cancelar'"><Ban class="size-4" /></button>
						</div>
					</section>

					<!-- Equipamento -->
					<section v-if="c.equipamento_info" class="card p-5">
						<p class="text-xs font-semibold tracking-wider text-suave uppercase">Equipamento</p>
						<component :is="tecnico ? 'RouterLink' : 'div'" :to="`/inventario/${c.equipamento_info.id}`" class="mt-3 flex items-center gap-3 rounded-xl p-1" :class="tecnico && 'transition hover:bg-realce'">
							<span class="grid size-10 shrink-0 place-items-center rounded-xl bg-marca-500/10 text-marca-600 dark:text-marca-300"><IconeEquipamento :nome="c.equipamento_info.icone" class="size-5" /></span>
							<span class="min-w-0">
								<span class="block font-semibold text-tinta">{{ c.equipamento_info.id }}</span>
								<span class="block truncate text-xs text-suave">{{ c.equipamento_info.modelo || c.equipamento_info.tipo }}</span>
							</span>
						</component>
						<p v-if="c.equipamento_info.resumo" class="mt-2 text-xs text-texto">{{ c.equipamento_info.resumo }}</p>
						<p v-if="tecnico" class="mt-1 text-xs text-suave">
							{{ c.equipamento_info.qtd_chamados }} chamado(s) neste equipamento<template v-if="c.equipamento_info.garantia_ate"> · garantia até {{ dataHora(c.equipamento_info.garantia_ate).slice(0, 10) }}</template>
						</p>
					</section>

					<!-- Prazos -->
					<section class="card space-y-4 p-5">
						<p class="flex items-center gap-1.5 text-xs font-semibold tracking-wider text-suave uppercase"><Clock class="size-3.5" /> Prazos</p>
						<div v-for="p in [
							{ titulo: '1ª resposta', prazo: c.prazo_resposta, sla: c.sla_resposta, feito: c.respondido, horas: c.horas_primeira_resposta },
							{ titulo: 'Resolução', prazo: c.prazo_resolucao, sla: c.sla_resolucao, feito: !!c.resolvido_em, horas: c.horas_resolucao, em: c.resolvido_em },
						]" :key="p.titulo">
							<div class="flex items-center justify-between text-sm">
								<span class="font-medium text-tinta">{{ p.titulo }}</span>
								<Etiqueta :valor="p.sla" :ponto="false" />
							</div>
							<div class="mt-1.5 h-1.5 overflow-hidden rounded-full bg-realce">
								<div class="h-full rounded-full" :class="COR_SLA[p.sla] || 'bg-slate-400'" :style="{ width: (p.feito ? 100 : consumo(p.prazo, p.em)) + '%' }" />
							</div>
							<p class="mt-1 text-xs text-suave">
								<template v-if="p.feito && p.horas !== null">Em {{ horas(p.horas) }} úteis · prazo {{ dataHora(p.prazo) }}</template>
								<template v-else-if="c.status === 'Aguardando Usuário' && p.titulo === 'Resolução'">Pausado: aguardando sua resposta</template>
								<template v-else>{{ prazo(p.prazo) }} · {{ dataHora(p.prazo) }}</template>
							</p>
						</div>
					</section>

					<!-- Detalhes -->
					<section class="card p-5">
						<p class="text-xs font-semibold tracking-wider text-suave uppercase">Detalhes</p>
						<dl class="mt-3 space-y-2.5 text-sm">
							<div class="flex justify-between gap-3"><dt class="text-suave">Solicitante</dt><dd class="text-right font-medium text-tinta">{{ c.solicitante_nome }}</dd></div>
							<div v-if="c.departamento" class="flex justify-between gap-3"><dt class="text-suave">Departamento</dt><dd class="text-right text-tinta">{{ c.departamento }}</dd></div>
							<div v-if="tecnico && c.email_solicitante" class="flex justify-between gap-3"><dt class="text-suave">E-mail</dt><dd class="truncate text-right text-tinta">{{ c.email_solicitante }}</dd></div>
							<div class="flex justify-between gap-3"><dt class="text-suave">Responsável</dt><dd class="text-right text-tinta">{{ c.responsavel_nome || "—" }}</dd></div>
							<div class="flex justify-between gap-3"><dt class="text-suave">Canal</dt><dd class="text-right text-tinta">{{ c.canal }}</dd></div>
							<div v-if="c.impacto" class="flex justify-between gap-3"><dt class="text-suave">Impacto</dt><dd class="text-right text-tinta">{{ c.impacto }}</dd></div>
							<div class="flex justify-between gap-3"><dt class="text-suave">Aberto em</dt><dd class="text-right text-tinta">{{ dataHora(c.aberto_em) }}</dd></div>
							<div v-if="c.reaberturas" class="flex justify-between gap-3"><dt class="text-suave">Reaberturas</dt><dd class="text-right text-tinta">{{ c.reaberturas }}</dd></div>
						</dl>
						<div v-if="c.pode.cancelar && !tecnico" class="mt-4 border-t border-borda pt-3">
							<button class="text-xs text-suave hover:text-rose-600" @click="modal = 'cancelar'">Não preciso mais: cancelar chamado</button>
						</div>
					</section>

					<!-- Anexos -->
					<section v-if="c.anexos.length" class="card p-5">
						<p class="text-xs font-semibold tracking-wider text-suave uppercase">Anexos ({{ c.anexos.length }})</p>
						<ul class="mt-3 space-y-1.5">
							<li v-for="a in c.anexos" :key="a.id">
								<a :href="urlAnexo(c.id, a.id)" target="_blank" class="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-texto hover:bg-realce">
									<FileText class="size-4 shrink-0 text-suave" /><span class="flex-1 truncate">{{ a.nome }}</span><span class="text-xs text-suave">{{ tamanho(a.tamanho) }}</span>
								</a>
							</li>
						</ul>
					</section>
				</aside>
			</div>
		</template>

		<!-- Modais -->
		<Modal v-if="modal === 'resolver'" titulo="Resolver chamado" subtitulo="A solução vai para o colaborador junto com o pedido de avaliação." @fechar="modal = null">
			<label class="rotulo">O que foi feito? *</label>
			<textarea v-model="solucao" rows="5" class="campo" placeholder="Ex.: senha redefinida e MFA reconfigurado; testado com o usuário." />
			<template #rodape>
				<button class="btn-secundario" @click="modal = null">Voltar</button>
				<button class="btn-sucesso" :disabled="!solucao.trim() || enviando" @click="acao('alterar', { status: 'Resolvido', solucao: textoParaHtml(solucao) }, 'Chamado resolvido. O colaborador foi avisado.')">
					<CheckCheck class="size-4" /> Resolver
				</button>
			</template>
		</Modal>
		<Modal v-if="modal === 'reabrir'" titulo="Reabrir chamado" subtitulo="Conte o que ainda não está funcionando." @fechar="modal = null">
			<textarea v-model="motivo" rows="4" class="campo" placeholder="Ex.: voltou a acontecer depois que reiniciei o computador." />
			<template #rodape>
				<button class="btn-secundario" @click="modal = null">Voltar</button>
				<button class="btn-primario" :disabled="!motivo.trim() || enviando" @click="acao('reabrir', { motivo: textoParaHtml(motivo) }, 'Chamado reaberto.')"><RotateCcw class="size-4" /> Reabrir</button>
			</template>
		</Modal>
		<Modal v-if="modal === 'cancelar'" titulo="Cancelar chamado?" subtitulo="O chamado será encerrado sem atendimento." @fechar="modal = null">
			<textarea v-model="motivo" rows="3" class="campo" placeholder="Motivo (opcional)" />
			<template #rodape>
				<button class="btn-secundario" @click="modal = null">Voltar</button>
				<button class="btn-perigo" :disabled="enviando" @click="acao('cancelar', { motivo: motivo.trim() ? textoParaHtml(motivo) : '' }, 'Chamado cancelado.')">Cancelar chamado</button>
			</template>
		</Modal>
	</div>
</template>
