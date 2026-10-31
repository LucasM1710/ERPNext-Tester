function paraData(valor) {
	if (!valor) return null
	const s = String(valor)
	return new Date(s.length === 10 ? s + "T12:00:00" : s.replace(" ", "T"))
}

export function moeda(valor) {
	return Number(valor || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
}

/** R$ 12,3 mil — para números grandes nos cartões */
export function moedaCurta(valor) {
	const v = Number(valor || 0)
	if (Math.abs(v) < 10000) return moeda(v)
	return "R$ " + (v / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + " mil"
}

export function data(valor) {
	const d = paraData(valor)
	return d ? d.toLocaleDateString("pt-BR") : "—"
}

export function dataHora(valor) {
	const d = paraData(valor)
	return d ? d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : "—"
}

export function hojeISO(somarDias = 0) {
	const d = new Date()
	d.setDate(d.getDate() + somarDias)
	return d.toLocaleDateString("sv-SE")
}

/** "vence hoje", "vence em 3 dias", "venceu há 5 dias" */
export function vencimento(dias) {
	if (dias === 0) return "vence hoje"
	if (dias === 1) return "vence amanhã"
	if (dias > 1) return `vence em ${dias} dias`
	if (dias === -1) return "venceu ontem"
	return `venceu há ${-dias} dias`
}

export function plural(n, um, varios) {
	return `${n} ${n === 1 ? um : varios}`
}

// ------------------------------------------------------------- documentos (mesmas regras do servidor)
export function limparDocumento(v) {
	return String(v || "")
		.replace(/[^0-9A-Za-z]/g, "")
		.toUpperCase()
}

function dvCnpj(base) {
	const pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2].slice(-base.length)
	const soma = [...base].reduce((s, c, i) => s + (c.charCodeAt(0) - 48) * pesos[i], 0)
	const resto = soma % 11
	return resto < 2 ? "0" : String(11 - resto)
}

export function documentoValido(v) {
	const c = limparDocumento(v)
	if (c.length === 11) {
		if (/^(\d)\1+$/.test(c) || /\D/.test(c)) return false
		for (const n of [9, 10]) {
			let soma = 0
			for (let i = 0; i < n; i++) soma += Number(c[i]) * (n + 1 - i)
			if (((soma * 10) % 11) % 10 !== Number(c[n])) return false
		}
		return true
	}
	if (!/^[0-9A-Z]{12}\d{2}$/.test(c) || /^(.)\1+$/.test(c)) return false
	return dvCnpj(c.slice(0, 12)) === c[12] && dvCnpj(c.slice(0, 13)) === c[13]
}

export function formatarDocumento(v) {
	const c = limparDocumento(v)
	if (c.length === 14) return `${c.slice(0, 2)}.${c.slice(2, 5)}.${c.slice(5, 8)}/${c.slice(8, 12)}-${c.slice(12)}`
	if (c.length === 11) return `${c.slice(0, 3)}.${c.slice(3, 6)}.${c.slice(6, 9)}-${c.slice(9)}`
	return v || ""
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
