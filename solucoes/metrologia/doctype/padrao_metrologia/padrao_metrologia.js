frappe.ui.form.on("Padrao Metrologia", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Análise de impacto"), () => analise_de_impacto(frm));
		if (frm.doc.situacao === "Vencido" || frm.doc.status === "Bloqueado") {
			frm.dashboard.set_headline_alert(
				__("Este padrão não pode ser usado em novas calibrações ({0}).", [
					frm.doc.status === "Bloqueado" ? __("bloqueado") : __("vencido"),
				]),
				"red"
			);
		}
	},
});

// Quais certificados de clientes usaram este padrão? Útil quando ele é reprovado ou danificado.
function analise_de_impacto(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Análise de impacto — {0}", [frm.doc.codigo]),
		size: "extra-large",
		fields: [
			{
				fieldname: "desde",
				fieldtype: "Date",
				label: __("Certificados emitidos a partir de"),
				default: frm.doc.data_calibracao,
				description: __("Normalmente, a data da última calibração aprovada do padrão."),
				change: () => carregar(),
			},
			{ fieldname: "resultado", fieldtype: "HTML" },
		],
	});
	const carregar = () =>
		frappe
			.xcall("solucoes.metrologia.doctype.padrao_metrologia.padrao_metrologia.certificados_afetados", {
				padrao: frm.doc.name,
				desde: d.get_value("desde"),
			})
			.then((linhas) => {
				const clientes = new Set(linhas.map((l) => l.cliente));
				d.fields_dict.resultado.$wrapper.html(
					linhas.length
						? `<p><b>${linhas.length}</b> ${__("certificado(s)")} · <b>${clientes.size}</b> ${__("cliente(s)")}</p>
						<table class="table table-bordered table-sm"><thead><tr>
						<th>${__("Certificado")}</th><th>${__("Equipamento")}</th><th>${__("Cliente")}</th><th>${__("Data")}</th><th>${__("Resultado")}</th>
						</tr></thead><tbody>${linhas
							.map(
								(l) => `<tr><td><a href="/app/certificado-calibracao/${l.name}">${l.name}</a></td>
								<td>${frappe.utils.escape_html(l.tag || "")} · ${frappe.utils.escape_html(l.descricao_equipamento || "")}</td>
								<td>${frappe.utils.escape_html(l.cliente || "")}</td><td>${frappe.datetime.str_to_user(l.data_calibracao)}</td><td>${l.resultado || ""}</td></tr>`
							)
							.join("")}</tbody></table>`
						: `<p class="text-muted">${__("Nenhum certificado emitido com este padrão no período.")}</p>`
				);
			});
	d.show();
	carregar();
}
