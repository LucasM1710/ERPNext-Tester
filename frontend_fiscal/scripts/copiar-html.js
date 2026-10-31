// Copia o index.html gerado para solucoes/www/fiscal.html (página Jinja do Frappe).
import { copyFileSync } from "node:fs"

copyFileSync("../solucoes/public/fiscal/index.html", "../solucoes/www/fiscal.html")
console.log("index.html -> solucoes/www/fiscal.html")
