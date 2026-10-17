import { createApp } from "vue"
import { createRouter, createWebHistory } from "vue-router"
import App from "./App.vue"
import "./style.css"

const routes = [
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
	history: createWebHistory("/cliente/"),
	routes,
	scrollBehavior: () => ({ top: 0 }),
})

createApp(App).use(router).mount("#app")
