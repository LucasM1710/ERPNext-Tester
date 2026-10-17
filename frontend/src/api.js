import { store } from "./store"

const RAIZ = "/api/method/solucoes.api."
const BASE = RAIZ + "portal."

function mensagemDeErro(data, status) {
	try {
		if (data._server_messages) {
			const msgs = JSON.parse(data._server_messages).map((m) => JSON.parse(m).message)
			return msgs.join("\n").replace(/<[^>]+>/g, "")
		}
	} catch {
		// segue para o fallback
	}
	if (data.exception) return String(data.exception).split(":").slice(1).join(":").trim() || data.exception
	return status === 403 ? "Acesso negado." : "Não foi possível completar a operação."
}

function serializar(params) {
	const out = {}
	for (const [k, v] of Object.entries(params)) {
		if (v === undefined || v === null || v === "") continue
		out[k] = typeof v === "object" && !(v instanceof File) ? JSON.stringify(v) : v
	}
	return out
}

/**
 * Chama solucoes.api.portal.<metodo> (ou solucoes.api.<modulo>.<metodo> se o nome tiver ponto).
 * Injeta o cliente e o distrito selecionados no topo.
 */
export async function api(metodo, params = {}, { post = false, form = null } = {}) {
	const dados = serializar({ cliente: store.cliente, distrito: store.distrito, ...params })
	const url = (metodo.includes(".") ? RAIZ : BASE) + metodo
	let res
	if (post) {
		let body
		if (form) {
			body = form
			for (const [k, v] of Object.entries(dados)) body.append(k, v)
		} else {
			body = new URLSearchParams(dados)
		}
		res = await fetch(url, {
			method: "POST",
			headers: { Accept: "application/json", "X-Frappe-CSRF-Token": window.csrf_token },
			body,
		})
	} else {
		res = await fetch(url + "?" + new URLSearchParams(dados), { headers: { Accept: "application/json" } })
	}

	const data = await res.json().catch(() => ({}))
	if (!res.ok) {
		if (res.status === 403 && data.exc_type === "PermissionError" && !store.contexto) {
			window.location.href = "/login?redirect-to=" + encodeURIComponent(location.pathname)
		}
		throw new Error(mensagemDeErro(data, res.status))
	}
	return data.message
}

export function urlDownloadCertificado(id) {
	return BASE + "baixar_certificado?" + new URLSearchParams(serializar({ id, cliente: store.cliente, distrito: store.distrito }))
}
