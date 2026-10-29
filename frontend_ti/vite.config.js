import { fileURLToPath, URL } from "node:url"
import tailwindcss from "@tailwindcss/vite"
import vue from "@vitejs/plugin-vue"
import { defineConfig } from "vite"

// Build: arquivos em solucoes/public/central (servidos em /assets/solucoes/central/)
// e o index.html copiado para solucoes/www/ti.html (rota /ti). Dev: `yarn dev` em :8081/ti.
const BENCH = "http://127.0.0.1:8000"
const SITE = "erp.localhost"

export default defineConfig(({ command }) => ({
	base: command === "build" ? "/assets/solucoes/central/" : "/ti/",
	plugins: [vue(), tailwindcss()],
	resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
	build: { outDir: "../solucoes/public/central", emptyOutDir: true, chunkSizeWarningLimit: 1200 },
	server: {
		port: 8081,
		proxy: Object.fromEntries(
			["/api", "/assets", "/files", "/private", "/login", "/app"].map((p) => [p, { target: BENCH, headers: { Host: SITE } }]),
		),
	},
}))
