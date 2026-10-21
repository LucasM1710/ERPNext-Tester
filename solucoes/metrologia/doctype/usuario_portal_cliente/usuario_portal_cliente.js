// Distritos e oportunidades filtrados pelo cliente escolhido (oportunidades: busca também por contato e e-mail).
frappe.ui.form.on("Usuario Portal Cliente", {
	setup(frm) {
		frm.set_query("distrito", "distritos", () => ({ filters: { cliente: frm.doc.cliente || "__escolha_o_cliente__" } }))
		frm.set_query("oportunidade", "oportunidades", () => ({
			query: "solucoes.api.central.oportunidades_query",
			filters: { cliente: frm.doc.cliente || "__escolha_o_cliente__" },
		}))
	},
})
