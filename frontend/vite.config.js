import { fileURLToPath, URL } from "node:url"
import tailwindcss from "@tailwindcss/vite"
import vue from "@vitejs/plugin-vue"
import { defineConfig } from "vite"

// Build: arquivos em solucoes/public/portal (servidos em /assets/solucoes/portal/)
// e o index.html é copiado para solucoes/www/cliente.html (rota /cliente).
// Dev: `yarn dev` em http://localhost:8080/cliente, com proxy para o bench.
const BENCH = "http://127.0.0.1:8000"
const SITE = "erp.localhost"

export default defineConfig(({ command }) => ({
	base: command === "build" ? "/assets/solucoes/portal/" : "/cliente/",
	plugins: [vue(), tailwindcss()],
	resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
	build: {
		outDir: "../solucoes/public/portal",
		emptyOutDir: true,
		chunkSizeWarningLimit: 1200,
	},
	server: {
		port: 8080,
		proxy: Object.fromEntries(
			["/api", "/assets", "/files", "/private", "/login", "/app"].map((p) => [
				p,
				{ target: BENCH, changeOrigin: false, headers: { Host: SITE } },
			]),
		),
	},
}))
