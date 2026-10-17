import { reactive } from "vue"

const CHAVE_CLIENTE = "portal.cliente"
const CHAVE_DISTRITO = "portal.distrito"

function ler(chave) {
	try {
		return localStorage.getItem(chave) || null
	} catch {
		return null
	}
}

function gravar(chave, valor) {
	try {
		valor ? localStorage.setItem(chave, valor) : localStorage.removeItem(chave)
	} catch {
		// armazenamento indisponível: segue só em memória
	}
}

export const store = reactive({
	contexto: null,
	cliente: ler(CHAVE_CLIENTE), // null = todos os clientes do usuário
	distrito: ler(CHAVE_DISTRITO), // null = todos os distritos visíveis
	toasts: [],
})

export function definirCliente(cliente) {
	store.cliente = cliente || null
	gravar(CHAVE_CLIENTE, store.cliente)
	definirDistrito(null)
}

export function definirDistrito(distrito) {
	store.distrito = distrito || null
	gravar(CHAVE_DISTRITO, store.distrito)
}

export function infoCliente(id) {
	return store.contexto?.clientes.find((c) => c.id === id) || null
}

/** Cliente "em foco": o selecionado no topo, ou o único que o usuário tem. */
export function clienteAtual() {
	const lista = store.contexto?.clientes || []
	return infoCliente(store.cliente) || (lista.length === 1 ? lista[0] : null)
}

/** Pode gravar? Sem cliente informado, considera o cliente em foco (ou qualquer um dos clientes). */
export function podeEditar(cliente) {
	if (cliente) return infoCliente(cliente)?.pode_editar ?? false
	const atual = clienteAtual()
	return atual ? atual.pode_editar : (store.contexto?.clientes || []).some((c) => c.pode_editar)
}

export function algumComDistritos() {
	return (store.contexto?.clientes || []).some((c) => c.usa_distritos)
}

/** Precisa escolher um cliente antes de gravar algo? (usuário com vários clientes e "Todos" selecionado) */
export function precisaEscolherCliente() {
	return !store.cliente && (store.contexto?.clientes.length || 0) > 1
}

let seq = 0
export function toast(mensagem, tipo = "sucesso") {
	const id = ++seq
	store.toasts.push({ id, mensagem, tipo })
	setTimeout(() => (store.toasts = store.toasts.filter((t) => t.id !== id)), 4500)
}
