import { reactive } from "vue"

export const store = reactive({
	contexto: null,
	toasts: [],
	escuro: document.documentElement.classList.contains("dark"),
})

export function alternarTema() {
	store.escuro = !store.escuro
	document.documentElement.classList.toggle("dark", store.escuro)
	try {
		localStorage.setItem("fiscal.tema", store.escuro ? "escuro" : "claro")
	} catch {
		// sem armazenamento: vale só nesta visita
	}
}

export function simulacao() {
	return !!store.contexto?.simulacao
}

let seq = 0
export function toast(mensagem, tipo = "sucesso") {
	const id = ++seq
	store.toasts.push({ id, mensagem, tipo })
	setTimeout(() => (store.toasts = store.toasts.filter((t) => t.id !== id)), 5000)
}
