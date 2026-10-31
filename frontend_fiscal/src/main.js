import { createApp } from "vue"
import { createRouter, createWebHistory } from "vue-router"
import App from "./App.vue"
import "./style.css"

const routes = [
	{ path: "/", name: "emitir", component: () => import("./pages/ParaEmitir.vue"), meta: { titulo: "Para emitir" } },
	{ path: "/notas", name: "notas", component: () => import("./pages/Notas.vue"), meta: { titulo: "Notas emitidas" } },
	{ path: "/notas/:id", name: "nota", component: () => import("./pages/Nota.vue"), props: true, meta: { titulo: "Nota fiscal" } },
	{ path: "/boletos", name: "boletos", component: () => import("./pages/Boletos.vue"), meta: { titulo: "Boletos" } },
	{ path: "/remessas", name: "remessas", component: () => import("./pages/Remessas.vue"), meta: { titulo: "Remessa e retorno" } },
	{ path: "/remessas/nova", name: "nova-remessa", component: () => import("./pages/NovaRemessa.vue"), meta: { titulo: "Nova remessa ou retorno" } },
	{ path: "/producao", name: "producao", component: () => import("./pages/Producao.vue"), meta: { titulo: "Ir para produção" } },
	{ path: "/ajuda", name: "ajuda", component: () => import("./pages/Ajuda.vue"), meta: { titulo: "Manual" } },
	{ path: "/:pathMatch(.*)*", redirect: "/" },
]
const router = createRouter({ history: createWebHistory("/fiscal/"), routes, scrollBehavior: () => ({ top: 0 }) })
createApp(App).use(router).mount("#app")
