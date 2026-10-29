import { store } from "./store"

const RAIZ = "/api/method/solucoes.central_ti.api."
const BASE = RAIZ + "central."

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

/**
 * Chama solucoes.central_ti.api.central.<metodo> — ou solucoes.central_ti.api.<modulo>.<metodo> quando o nome tem ponto
 * (ex.: "inventario.estoque"). `arquivos` (lista de File) vai em multipart.
 */
export async function api(metodo, params = {}, { post = false, arquivos = null } = {}) {
	const url = (metodo.includes(".") ? RAIZ : BASE) + metodo
	const limpos = Object.fromEntries(
		Object.entries(params)
			.filter(([, v]) => v !== undefined && v !== null && v !== "")
			.map(([k, v]) => [k, typeof v === "object" ? JSON.stringify(v) : v]),
	)
	let res
	if (post) {
		let body = new URLSearchParams(limpos)
		if (arquivos?.length) {
			body = new FormData()
			for (const [k, v] of Object.entries(limpos)) body.append(k, v)
			for (const a of arquivos) body.append("arquivos", a, a.name)
		}
		res = await fetch(url, {
			method: "POST",
			headers: { Accept: "application/json", "X-Frappe-CSRF-Token": window.csrf_token },
			body,
		})
	} else {
		res = await fetch(url + "?" + new URLSearchParams(limpos), { headers: { Accept: "application/json" } })
	}
	const data = await res.json().catch(() => ({}))
	if (!res.ok) {
		if (res.status === 403 && !store.contexto) window.location.href = "/login?redirect-to=" + encodeURIComponent(location.pathname)
		throw new Error(mensagemDeErro(data, res.status))
	}
	return data.message
}

export function urlAnexo(chamado, arquivo) {
	return BASE + "baixar_anexo?" + new URLSearchParams({ id: chamado, arquivo })
}
