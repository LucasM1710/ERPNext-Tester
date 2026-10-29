function paraData(valor) {
	if (!valor) return null
	return new Date(String(valor).replace(" ", "T"))
}

export function dataHora(valor) {
	const d = paraData(valor)
	return d ? d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : "—"
}

export function data(valor) {
	const d = paraData(valor)
	return d ? d.toLocaleDateString("pt-BR") : "—"
}

/** "há 5 min", "há 3 h", "ontem", "12/10" */
export function relativo(valor) {
	const d = paraData(valor)
	if (!d) return ""
	const seg = (Date.now() - d) / 1000
	if (seg < 60) return "agora"
	if (seg < 3600) return `há ${Math.round(seg / 60)} min`
	if (seg < 86400) return `há ${Math.round(seg / 3600)} h`
	if (seg < 172800) return "ontem"
	if (seg < 604800) return `há ${Math.round(seg / 86400)} dias`
	return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })
}

/** Prazo legível: "vence em 2 h", "atrasado há 1 dia", "vence seg 10:00" */
export function prazo(valor) {
	const d = paraData(valor)
	if (!d) return ""
	const min = Math.round((d - Date.now()) / 60000)
	const fmt = (m) => (m < 60 ? `${m} min` : m < 1440 ? `${Math.round(m / 60)} h` : `${Math.round(m / 1440)} dia(s)`)
	if (min < 0) return `atrasado há ${fmt(-min)}`
	if (min < 1440) return `vence em ${fmt(min)}`
	return "vence " + d.toLocaleString("pt-BR", { weekday: "short", hour: "2-digit", minute: "2-digit" }).replace(".", "")
}

export function horas(valor) {
	if (valor === null || valor === undefined) return "—"
	if (valor < 1) return `${Math.round(valor * 60)} min`
	return `${Number(valor).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} h`
}

export function tamanho(bytes) {
	if (!bytes) return ""
	return bytes < 1024 * 1024 ? `${Math.round(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

/** Texto digitado -> HTML seguro (parágrafos e quebras), para mensagens e descrições. */
export function textoParaHtml(texto) {
	const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
	return esc(texto.trim())
		.split(/\n{2,}/)
		.map((p) => `<p>${p.replace(/\n/g, "<br>")}</p>`)
		.join("")
}

export function iniciais(nome) {
	return (nome || "?")
		.split(" ")
		.filter(Boolean)
		.slice(0, 2)
		.map((p) => p[0])
		.join("")
		.toUpperCase()
}
