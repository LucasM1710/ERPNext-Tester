import { createApp } from "vue"
import { createRouter, createWebHistory } from "vue-router"
import App from "./App.vue"
import "./style.css"

// Painel da TV (/ti/tv?chave=…): tela própria, sem login, sem menu.
if (location.pathname.replace(/\/$/, "") === "/ti/tv") {
	import("./pages/Tv.vue").then(({ default: Tv }) => createApp(Tv).mount("#app"))
} else {
	const routes = [
		{ path: "/", name: "inicio", component: () => import("./pages/Inicio.vue"), meta: { titulo: "Início" } },
		{ path: "/novo", name: "novo", component: () => import("./pages/NovoChamado.vue"), meta: { titulo: "Abrir chamado" } },
		{ path: "/chamados", name: "meus", component: () => import("./pages/MeusChamados.vue"), meta: { titulo: "Meus chamados" } },
		{ path: "/chamados/:id", name: "chamado", component: () => import("./pages/Chamado.vue"), props: true, meta: { titulo: "Chamado" } },
		{ path: "/fila", name: "fila", component: () => import("./pages/Fila.vue"), meta: { titulo: "Fila de atendimento", tecnico: true } },
		{ path: "/painel", name: "painel", component: () => import("./pages/Painel.vue"), meta: { titulo: "Indicadores", tecnico: true } },
		{ path: "/gestao", name: "gestao", component: () => import("./pages/Gestao.vue"), meta: { titulo: "Visão do gestor", tecnico: true } },
		{ path: "/inventario", name: "inventario", component: () => import("./pages/Inventario.vue"), meta: { titulo: "Inventário", tecnico: true } },
		{ path: "/inventario/:id", name: "equipamento", component: () => import("./pages/EquipamentoTI.vue"), props: true, meta: { titulo: "Equipamento", tecnico: true } },
		{ path: "/estoque", name: "estoque", component: () => import("./pages/Estoque.vue"), meta: { titulo: "Estoque de TI", tecnico: true } },
		{ path: "/compras", name: "compras", component: () => import("./pages/Compras.vue"), meta: { titulo: "Compras de TI", tecnico: true } },
		{ path: "/ajuda", name: "ajuda", component: () => import("./pages/Ajuda.vue"), meta: { titulo: "Manual" } },
		{ path: "/:pathMatch(.*)*", redirect: "/" },
	]
	const router = createRouter({ history: createWebHistory("/ti/"), routes, scrollBehavior: () => ({ top: 0 }) })
	createApp(App).use(router).mount("#app")
}
