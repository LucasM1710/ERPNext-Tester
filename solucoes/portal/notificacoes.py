"""Resumo semanal de vencimentos para usuários do portal.

Cada usuário recebe apenas o que enxerga no portal (mesmo Escopo da API): o responsável
de distrito, os seus distritos; o gestor, o cliente inteiro com o ranking de distritos.
"""

import frappe
from frappe import _
from frappe.utils import get_url

from solucoes.metrologia.utils import get_dias_alerta
from solucoes.portal.adapters import get_adapter
from solucoes.portal.sessao import get_escopo, is_usuario_interno


def usuarios_do_portal() -> set[str]:
	usuarios = set(frappe.get_all("Portal User", filters={"parenttype": "Customer"}, pluck="user"))
	usuarios |= set(frappe.get_all("Usuario Portal Cliente", filters={"ativo": 1}, pluck="usuario"))
	usuarios |= set(frappe.get_all("Contact", filters={"user": ["is", "set"]}, pluck="user"))
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
	escopo = get_escopo(usuario)
	if not escopo:
		return None
	adapter = get_adapter()
	equipamentos = [
		e for e in adapter.listar_equipamentos(escopo) if e.get("status") not in ("Inativo", "Sucateado")
	]
	vencidos = [e for e in equipamentos if e["situacao"] == "Vencido"]
	a_vencer = [e for e in equipamentos if e["situacao"] == "A Vencer"]
	if not vencidos and not a_vencer:
		return None
	gestor = any(escopo.eh_gestor(c) for c in escopo)
	return {
		"vencidos": vencidos,
		"a_vencer": a_vencer,
		"ranking": adapter.resumo_por_distrito(equipamentos) if gestor else [],
		"dias_alerta": get_dias_alerta(),
	}


def enviar_resumo(usuario: str):
	resumo = montar_resumo(usuario)
	if not resumo:
		return
	titulo = frappe.db.get_single_value("Configuracao Portal Metrologia", "titulo_portal") or "Portal do Cliente"
	frappe.sendmail(
		recipients=[usuario],
		subject=_("{0}: {1} vencido(s) e {2} a vencer").format(titulo, len(resumo["vencidos"]), len(resumo["a_vencer"])),
		message=frappe.render_template(TEMPLATE, {**resumo, "url": get_url("/cliente"), "titulo": titulo}),
		reference_doctype="User",
		reference_name=usuario,
	)


TEMPLATE = """
<div style="font-family:Inter,Arial,sans-serif;max-width:640px;margin:auto;color:#0f172a">
  <h2 style="margin:0 0 4px">Resumo semanal de calibrações</h2>
  <p style="color:#64748b;margin:0 0 20px">Equipamentos que precisam de atenção nos próximos {{ dias_alerta }} dias.</p>

  {% if ranking %}
  <h3 style="font-size:14px;margin:20px 0 8px">Distritos</h3>
  <table style="width:100%;border-collapse:collapse;font-size:13px">
    <tr style="background:#f8fafc;color:#64748b;text-align:left">
      <th style="padding:8px">Distrito</th><th style="padding:8px">% em dia</th><th style="padding:8px">Vencidos</th><th style="padding:8px">A vencer</th>
    </tr>
    {% for d in ranking %}
    <tr style="border-top:1px solid #eef2f7">
      <td style="padding:8px">{{ d.nome }}</td>
      <td style="padding:8px;font-weight:600;color:{{ '#e11d48' if d.em_dia_pct < 75 else ('#d97706' if d.em_dia_pct < 90 else '#059669') }}">{{ d.em_dia_pct }}%</td>
      <td style="padding:8px">{{ d['Vencido'] }}</td><td style="padding:8px">{{ d['A Vencer'] }}</td>
    </tr>
    {% endfor %}
  </table>
  {% endif %}

  {% for titulo_lista, lista, cor in [("Vencidos", vencidos, "#e11d48"), ("A vencer", a_vencer, "#d97706")] if lista %}
  <h3 style="font-size:14px;margin:24px 0 8px;color:{{ cor }}">{{ titulo_lista }} ({{ lista|length }})</h3>
  <table style="width:100%;border-collapse:collapse;font-size:13px">
    {% for e in lista[:30] %}
    <tr style="border-top:1px solid #eef2f7">
      <td style="padding:8px"><b>{{ e.tag }}</b> · {{ e.descricao }}</td>
      <td style="padding:8px;color:#64748b">{{ e.distrito_nome or e.localizacao or "" }}</td>
      <td style="padding:8px;text-align:right">{{ frappe.utils.formatdate(e.proxima_calibracao) }}</td>
    </tr>
    {% endfor %}
  </table>
  {% if lista|length > 30 %}<p style="color:#64748b;font-size:12px">… e mais {{ lista|length - 30 }}.</p>{% endif %}
  {% endfor %}

  <p style="margin:28px 0"><a href="{{ url }}/solicitar" style="background:#2549ea;color:#fff;padding:10px 18px;border-radius:10px;text-decoration:none;font-weight:600">Solicitar calibração</a></p>
  <p style="color:#94a3b8;font-size:12px">Você recebe este e-mail por ter acesso ao {{ titulo }}.</p>
</div>
"""
