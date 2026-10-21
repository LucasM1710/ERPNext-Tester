"""Resumo semanal de vencimentos para usuários do portal.

Cada usuário recebe apenas o que enxerga no portal (mesmo Escopo da API): o responsável
de distrito, os seus distritos; o gestor, o cliente inteiro com o ranking de distritos.
"""

import frappe
from frappe import _

from solucoes.metrologia.utils import get_dias_alerta
from solucoes.portal.adapters import get_adapter
from solucoes.portal.sessao import get_escopo, is_usuario_interno


def usuarios_do_portal() -> set[str]:
	# Só quem tem acesso explícito ao portal (nunca qualquer contato com usuário).
	usuarios = set(frappe.get_all("Usuario Portal Cliente", filters={"ativo": 1}, pluck="usuario"))
	ativos = set(frappe.get_all("User", filters={"name": ["in", list(usuarios) or [""]], "enabled": 1}, pluck="name"))
	return {u for u in ativos if not is_usuario_interno(u)}


def enviar_resumos_semanais():
	if not frappe.db.get_single_value("Configuracao Portal Metrologia", "enviar_resumo_semanal"):
		return
	for usuario in usuarios_do_portal():
		try:
			enviar_resumo(usuario)
		except Exception:
			frappe.log_error(title=f"Resumo semanal do portal: {usuario}")


def montar_resumo(usuario: str) -> dict | None:
	from solucoes.portal.adapters.er import AdapterER

	escopo = get_escopo(usuario)
	if not escopo:
		return None
	frappe.form_dict.portal = "consulta"
	equipamentos = [e for e in AdapterER().listar_equipamentos(escopo) if e.get("status") not in ("Inativo", "Sucateado")]
	vencidos = [e for e in equipamentos if e["status_calibracao"] == "Vencido"]
	criticos = [e for e in equipamentos if e["status_calibracao"] == "Crítico"]
	if not vencidos and not criticos:
		return None
	clientes = {e.get("cliente_nome") for e in equipamentos}
	return {"vencidos": vencidos, "criticos": criticos, "cliente": next(iter(clientes)) if len(clientes) == 1 else None}


def enviar_resumo(usuario: str):
	from solucoes.portal.emails import enviar

	resumo = montar_resumo(usuario)
	if not resumo:
		return
	enviar(
		usuario,
		_("Calibrações: {0} vencido(s) e {1} crítico(s)").format(len(resumo["vencidos"]), len(resumo["criticos"])),
		"resumo_semanal",
		**resumo,
	)
