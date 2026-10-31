app_name = "solucoes"
app_title = "Solucoes"
app_publisher = "Lucas"
app_description = "Solucoes customizadas para ERPNext"
app_email = "lucasmatheusc@hotmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "solucoes",
# 		"logo": "/assets/solucoes/logo.png",
# 		"title": "Solucoes",
# 		"route": "/solucoes",
# 		"has_permission": "solucoes.api.permission.has_app_permission",
# 	}
# ]

# The dock, the rail down the left of the desk, is a document rather than a hook. Author it in
# Manage Dock on a developer-mode site and press Export to App, and it is written to
# `solucoes/dock/solucoes/solucoes.json` for git to carry. An app that ships none has no
# rail: its sidebar gets a switcher in the header instead.
#
# A companion app, one that extends a host app rather than standing on its own, says so with
# `mount_on` on that same record, and its entries are appended to the host's rail. Mounting keeps
# the companion off the apps screen, so it takes precedence over any add_to_apps_screen above.

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/solucoes/css/solucoes.css"
# app_include_js = "/assets/solucoes/js/solucoes.js"

# include js, css files in header of web template
# web_include_css = "/assets/solucoes/css/solucoes.css"
# web_include_js = "/assets/solucoes/js/solucoes.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "solucoes/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_kanban_js = {"doctype" : "public/js/doctype_kanban.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "solucoes/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# Página inicial do cliente: a de consulta (dados reais da empresa). /cliente segue acessível pelo endereço.
role_home_page = {"Customer": "consulta"}
# O Builder também define a página inicial de usuários de site (e tem prioridade);
# este gancho manda os usuários do portal para /consulta e devolve os demais ao Builder.
get_website_user_home_page = "solucoes.portal.pagina_inicial.pagina_inicial"

# Portal do Cliente (SPA Vue): todas as sub-rotas de /cliente servem a mesma página
website_route_rules = [
	{"from_route": "/cliente/<path:app_path>", "to_route": "cliente"},
	{"from_route": "/consulta/<path:app_path>", "to_route": "consulta"},
	# Central de TI (módulo Central TI): todas as sub-rotas de /ti servem a mesma página
	{"from_route": "/ti/<path:app_path>", "to_route": "ti"},
	# Fiscal (notas e boletos): todas as sub-rotas de /fiscal servem a mesma página
	{"from_route": "/fiscal/<path:app_path>", "to_route": "fiscal"},
]

# Central de TI: e-mails recebidos pela conta da TI (Append To = Chamado TI) entram na conversa do chamado
doc_events = {
	"Communication": {
		"after_insert": "solucoes.central_ti.email.ao_receber_email",
	},
	# Fiscal: emissão automática ao confirmar a fatura (só se ligada na Configuracao Fiscal)
	"Sales Invoice": {
		"on_submit": "solucoes.fiscal.emissao.ao_confirmar_fatura",
	},
}

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "solucoes.utils.jinja_methods",
# 	"filters": "solucoes.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "solucoes.install.before_install"
# after_install = "solucoes.install.after_install"
after_migrate = "solucoes.setup.after_migrate"

# Uninstallation
# ------------

# before_uninstall = "solucoes.uninstall.before_uninstall"
# after_uninstall = "solucoes.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "solucoes.utils.before_app_install"
# after_app_install = "solucoes.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "solucoes.utils.before_app_uninstall"
# after_app_uninstall = "solucoes.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "solucoes.build.after_build"

# To hook into the build process of other apps
# The list of apps being built is passed as an argument

# after_app_build = "solucoes.build.after_app_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "solucoes.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["solucoes.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"solucoes.tasks.all"
# 	],
# 	"daily": [
# 		"solucoes.tasks.daily"
# 	],
# 	"hourly": [
# 		"solucoes.tasks.hourly"
# 	],
# 	"weekly": [
# 		"solucoes.tasks.weekly"
# 	],
# 	"monthly": [
# 		"solucoes.tasks.monthly"
# 	],
# }
scheduler_events = {
	"daily": [
		"solucoes.metrologia.utils.atualizar_situacao_equipamentos",
		"solucoes.metrologia.utils.atualizar_situacao_padroes",
		# Fiscal: boletos vencidos, lembretes e cobranças
		"solucoes.fiscal.emissao.atualizar_boletos",
	],
	"weekly": [
		"solucoes.portal.notificacoes.enviar_resumos_semanais",
	],
	# Central de TI: situação do SLA e alertas a cada 15 min; fechamento automático de resolvidos
	"cron": {
		"*/15 * * * *": ["solucoes.central_ti.tarefas.atualizar_sla"],
	},
	"hourly": [
		"solucoes.central_ti.tarefas.fechar_resolvidos",
	],
}

# Testing
# -------

# before_tests = "solucoes.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "solucoes.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "solucoes.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "solucoes.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["solucoes.utils.before_request"]
# after_request = ["solucoes.utils.after_request"]

# Job Events
# ----------
# before_job = ["solucoes.utils.before_job"]
# after_job = ["solucoes.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"solucoes.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


# Atalhos do ERP para a central do portal (não altera o doctype; só um botão no formulário)
doctype_js = {"Customer": "public/js/customer_portal.js"}

# Conexões do Cliente: seção "Portal do cliente" (acesso, distritos, usuários, equipamentos, logs)
override_doctype_dashboards = {"Customer": "solucoes.portal.conexoes.customer_dashboard"}
