// Cada campo filtrado pelo que já foi escolhido: equipamento → cliente → distritos e donos do cliente.
frappe.ui.form.on("Distrito Equipamento", {
	setup(frm) {
		frm.set_query("equipamento", () => (frm.doc.cliente ? { filters: { customer: frm.doc.cliente } } : {}))
		frm.set_query("distrito", () => ({ filters: { cliente: frm.doc.cliente || "__escolha_o_cliente__" } }))
		frm.set_query("dono", () => ({
			query: "solucoes.api.central.usuarios_do_cliente",
			filters: { cliente: frm.doc.cliente || "" },
		}))
	},
	onload(frm) {
		if (!frm.doc.equipamento_doctype) frm.set_value("equipamento_doctype", "Equipamentos")
	},
	async equipamento(frm) {
		if (!frm.doc.equipamento || frm.doc.equipamento_doctype !== "Equipamentos") return
		const { message } = await frappe.db.get_value("Equipamentos", frm.doc.equipamento, "customer")
		if (message?.customer) frm.set_value("cliente", message.customer)
	},
	cliente(frm) {
		frm.set_value("distrito", null)
		frm.set_value("dono", null)
	},
})
