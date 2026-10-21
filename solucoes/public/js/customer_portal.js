// Botões no cadastro do cliente: "Portal do cliente" abre a central do portal já com o cliente;
// "Manual do portal" abre o manual na parte da ER.
frappe.ui.form.on("Customer", {
	refresh(frm) {
		if (frm.is_new()) return
		frm.add_custom_button(__("Portal do cliente"), () =>
			window.open(`/consulta/central?cliente=${encodeURIComponent(frm.doc.name)}`, "_blank"),
		)
		frm.add_custom_button(__("Manual do portal"), () => window.open("/consulta/manual?parte=er", "_blank"))
	},
})
