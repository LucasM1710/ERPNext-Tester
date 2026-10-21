import { createApp } from "vue"
import { createRouter, createWebHistory } from "vue-router"
import App from "./App.vue"
import "./style.css"
import { BASE, CONSULTA } from "./modo"

// /consulta: visão operacional e gestão do parque (dados do laboratório + equipamentos de terceiros).
const rotasConsulta = [
	{ path: "/", name: "painel", component: () => import("./pages/consulta/PainelOperacional.vue"), meta: { titulo: "Visão operacional" } },
	{ path: "/equipamentos", name: "equipamentos", component: () => import("./pages/consulta/GestaoEquipamentos.vue"), meta: { titulo: "Equipamentos" } },
	{ path: "/equipamentos/:id", name: "equipamento", component: () => import("./pages/consulta/EquipamentoConsulta.vue"), props: true, meta: { titulo: "Equipamento" } },
	{ path: "/certificados", name: "certificados", component: () => import("./pages/Certificados.vue"), meta: { titulo: "Certificados" } },
	{ path: "/certificados/:id", name: "certificado", component: () => import("./pages/CertificadoDetalhe.vue"), props: true, meta: { titulo: "Certificado" } },
	{ path: "/ordens", name: "ordens", component: () => import("./pages/Ordens.vue"), meta: { titulo: "Ordens de Serviço" } },
	{ path: "/ordens/:id", name: "ordem", component: () => import("./pages/OrdemDetalhe.vue"), props: true, meta: { titulo: "Ordem de Serviço" } },
	{ path: "/relatorios", name: "relatorios", component: () => import("./pages/consulta/Relatorios.vue"), meta: { titulo: "Relatórios" } },
	{ path: "/logs", name: "logs", component: () => import("./pages/consulta/Logs.vue"), meta: { titulo: "Logs de auditoria" } },
	{ path: "/gestao", name: "gestao", component: () => import("./pages/Gestao.vue"), meta: { titulo: "Distritos e equipe" } },
	{ path: "/central", name: "central", component: () => import("./pages/consulta/Central.vue"), meta: { titulo: "Central do portal" } },
	{ path: "/historico", name: "historico", component: () => import("./pages/consulta/HistoricoAtendimento.vue"), meta: { titulo: "Histórico de atendimento" } },
	{ path: "/manual", name: "manual", component: () => import("./pages/consulta/Manual.vue"), meta: { titulo: "Manual do portal" } },
	{ path: "/:pathMatch(.*)*", redirect: "/" },
]

const rotasCompleto = [
	{ path: "/", name: "painel", component: () => import("./pages/Painel.vue"), meta: { titulo: "Painel" } },
	{ path: "/equipamentos", name: "equipamentos", component: () => import("./pages/Equipamentos.vue"), meta: { titulo: "Equipamentos" } },
	{ path: "/equipamentos/:id", name: "equipamento", component: () => import("./pages/EquipamentoDetalhe.vue"), props: true, meta: { titulo: "Equipamento" } },
	{ path: "/certificados", name: "certificados", component: () => import("./pages/Certificados.vue"), meta: { titulo: "Certificados" } },
	{ path: "/certificados/:id", name: "certificado", component: () => import("./pages/CertificadoDetalhe.vue"), props: true, meta: { titulo: "Certificado" } },
	{ path: "/ordens", name: "ordens", component: () => import("./pages/Ordens.vue"), meta: { titulo: "Ordens de Serviço" } },
	{ path: "/ordens/:id", name: "ordem", component: () => import("./pages/OrdemDetalhe.vue"), props: true, meta: { titulo: "Ordem de Serviço" } },
	{ path: "/solicitar", name: "solicitar", component: () => import("./pages/SolicitarServico.vue"), meta: { titulo: "Solicitar Serviço" } },
	{ path: "/gestao", name: "gestao", component: () => import("./pages/Gestao.vue"), meta: { titulo: "Distritos e equipe" } },
	{ path: "/:pathMatch(.*)*", redirect: "/" },
]

const router = createRouter({
	history: createWebHistory(BASE),
	routes: CONSULTA ? rotasConsulta : rotasCompleto,
	scrollBehavior: () => ({ top: 0 }),
})

createApp(App).use(router).mount("#app")
