const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

function paraData(valor) {
	if (!valor) return null
	const [a, m, d] = String(valor).slice(0, 10).split("-").map(Number)
	return new Date(a, m - 1, d)
}

export function data(valor) {
	const d = paraData(valor)
	return d ? d.toLocaleDateString("pt-BR") : "—"
}

export function dataHora(valor) {
	if (!valor) return "—"
	const d = new Date(String(valor).replace(" ", "T"))
	return d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })
}

export function mesCurto(chave) {
	const [a, m] = chave.split("-")
	return `${MESES[Number(m) - 1]}/${a.slice(2)}`
}

export function diasAte(valor) {
	const d = paraData(valor)
	if (!d) return null
	const hoje = new Date()
	hoje.setHours(0, 0, 0, 0)
	return Math.round((d - hoje) / 86400000)
}

export function relativo(valor) {
	const dias = diasAte(valor)
	if (dias === null) return ""
	if (dias === 0) return "hoje"
	if (dias === 1) return "amanhã"
	if (dias === -1) return "ontem"
	if (dias > 0) return dias < 60 ? `em ${dias} dias` : `em ${Math.round(dias / 30)} meses`
	return -dias < 60 ? `há ${-dias} dias` : `há ${Math.round(-dias / 30)} meses`
}

export function numero(valor, casas = 4) {
	if (valor === null || valor === undefined || valor === "") return "—"
	return Number(valor).toLocaleString("pt-BR", { maximumFractionDigits: casas })
}

export function exportarCsv(nome, colunas, linhas) {
	const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`
	const csv = [colunas.map((c) => esc(c.label)).join(";")]
		.concat(linhas.map((l) => colunas.map((c) => esc(c.valor(l))).join(";")))
		.join("\n")
	const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" })
	const a = document.createElement("a")
	a.href = URL.createObjectURL(blob)
	a.download = nome
	a.click()
	URL.revokeObjectURL(a.href)
}
