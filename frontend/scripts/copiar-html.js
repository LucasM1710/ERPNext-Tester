// Copia o index.html gerado para solucoes/www/cliente.html (página Jinja do Frappe).
import { copyFileSync } from "node:fs"

copyFileSync("../solucoes/public/portal/index.html", "../solucoes/www/cliente.html")
console.log("index.html -> solucoes/www/cliente.html")
