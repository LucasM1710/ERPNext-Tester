import { store } from "./store"

const BASE = "/api/method/solucoes.fiscal.api."

function mensagemDeErro(data, status) {
	try {
		if (data._server_messages) {
			const msgs = JSON.parse(data._server_messages).map((m) => JSON.parse(m).message)
			return msgs.join("\n").replace(/<br\s*\/?>/g, "\n").replace(/<[^>]+>/g, "")
		}
	} catch {
		// segue para o fallback
	}
	if (data.exception) return String(data.exception).split(":").slice(1).join(":").trim() || data.exception
	return status === 403 ? "Acesso negado." : "Não foi possível completar a operação."
}

/** Chama solucoes.fiscal.api.<metodo>. Objetos vão como JSON. */
export async function api(metodo, params = {}, { post = false } = {}) {
	const limpos = Object.fromEntries(
		Object.entries(params)
			.filter(([, v]) => v !== undefined && v !== null && v !== "")
			.map(([k, v]) => [k, typeof v === "object" ? JSON.stringify(v) : v]),
	)
	const res = post
		? await fetch(BASE + metodo, {
				method: "POST",
				headers: { Accept: "application/json", "X-Frappe-CSRF-Token": window.csrf_token },
				body: new URLSearchParams(limpos),
			})
		: await fetch(BASE + metodo + "?" + new URLSearchParams(limpos), { headers: { Accept: "application/json" } })
	const data = await res.json().catch(() => ({}))
	if (!res.ok) {
		if (res.status === 403 && !store.contexto) window.location.href = "/login?redirect-to=" + encodeURIComponent(location.pathname)
		throw new Error(mensagemDeErro(data, res.status))
	}
	return data.message
}

/** Link do PDF da nota/boleto ou do XML (abre em nova aba). */
export function urlDocumento(tipo, id, formato = "pdf") {
	return BASE + "documento?" + new URLSearchParams({ tipo, id, formato })
}
