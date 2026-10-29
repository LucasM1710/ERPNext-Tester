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
		localStorage.setItem("ti.tema", store.escuro ? "escuro" : "claro")
	} catch {
		// sem armazenamento: vale só nesta visita
	}
}

export function eTecnico() {
	return !!store.contexto?.usuario.tecnico
}

let seq = 0
export function toast(mensagem, tipo = "sucesso") {
	const id = ++seq
	store.toasts.push({ id, mensagem, tipo })
	setTimeout(() => (store.toasts = store.toasts.filter((t) => t.id !== id)), 4500)
}
