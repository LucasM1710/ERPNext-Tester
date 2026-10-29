// Copia o index.html gerado para solucoes/www/ti.html (página Jinja do Frappe).
import { copyFileSync } from "node:fs"

copyFileSync("../solucoes/public/central/index.html", "../solucoes/www/ti.html")
console.log("index.html -> solucoes/www/ti.html")
