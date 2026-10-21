// Copia o index.html gerado para solucoes/www/cliente.html (página Jinja do Frappe).
import { copyFileSync } from "node:fs"

for (const pagina of ["cliente", "consulta"]) {
	copyFileSync("../solucoes/public/portal/index.html", `../solucoes/www/${pagina}.html`)
	console.log(`index.html -> solucoes/www/${pagina}.html`)
}
