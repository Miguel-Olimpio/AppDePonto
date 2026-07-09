"""Janela principal com sidebar, dashboard e telas operacionais."""

from __future__ import annotations

from datetime import date
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

import ttkbootstrap as ttb

from app.bot.bot_service import BotService

from app.config.settings import (
    APP_TITLE,
    OCCURRENCE_POINT_MISSING,
    OCCURRENCE_STATUS_OPEN,
    OCCURRENCE_STATUS_RESOLVED,
    OCCURRENCE_TASK_LATE,
    OCCURRENCE_TASK_MISSED,
    SCALE_TYPE_SCALE,
)
from app.repositories.excel_database import ExcelSaveError
from app.services.collaborator_service import CollaboratorService
from app.services.dashboard_service import DashboardService
from app.services.journey_service import JourneyService
from app.services.monthly_report_service import MonthlyReportService
from app.services.goal_service import GoalService
from app.services.maintenance_service import MaintenanceService
from app.services.occurrence_service import OccurrenceService
from app.services.sector_service import SectorService
from app.services.task_service import TaskService
from app.services.time_clock_service import TimeClockService
from app.ui.bot_panel import BotPanel
from app.ui.collaborator_editor import CollaboratorEditor
from app.ui.frequency_dialog import FrequencyDialog
from app.ui.goal_editor import GoalEditor
from app.ui.journey_editor import JourneyEditor
from app.ui.maintenance_panel import MaintenancePanel
from app.ui.occurrence_editor import OccurrenceEditor
from app.ui.sector_editor import SectorEditor
from app.ui.task_check_panel import TaskCheckPanel
from app.ui.task_editor import TaskEditor
from app.ui.waiver_dialog import WaiverDialog
from app.utils.formatting import yes_no
from app.utils.open_file_location import prompt_open_generated_file


PRIMARY = "#005CA9"
PRIMARY_DARK = "#003F7D"
ACTIVE_BLUE = "#D9ECFF"
BACKGROUND = "#F4F8FC"
WHITE = "#FFFFFF"
MUTED = "#64748B"


class MainWindow(ttb.Frame):
    def __init__(
        self,
        master: tk.Misc,
        collaborator_service: CollaboratorService,
        time_clock_service: TimeClockService,
        task_service: TaskService,
        occurrence_service: OccurrenceService,
        dashboard_service: DashboardService,
        journey_service: JourneyService,
        monthly_report_service: MonthlyReportService,
        sector_service: SectorService,
        goal_service: GoalService,
        bot_service: BotService,
        maintenance_service: MaintenanceService,
        on_logout=None,
    ):
        super().__init__(master, padding=0, style="App.TFrame")
        self.collaborator_service = collaborator_service
        self.time_clock_service = time_clock_service
        self.task_service = task_service
        self.occurrence_service = occurrence_service
        self.dashboard_service = dashboard_service
        self.journey_service = journey_service
        self.monthly_report_service = monthly_report_service
        self.sector_service = sector_service
        self.goal_service = goal_service
        self.bot_service = bot_service
        self.maintenance_service = maintenance_service
        self.on_logout = on_logout
        self._nav_buttons: dict[str, ttb.Button] = {}
        self._current = "dashboard"
        self._status_var = tk.StringVar(value="Pronto.")
        self._dash_vars = {
            "presentes": tk.StringVar(value="0"),
            "tarefas_dia": tk.StringVar(value="0"),
            "tarefas_cumpridas": tk.StringVar(value="0"),
            "tarefas_parciais": tk.StringVar(value="0"),
            "tarefas_atrasadas": tk.StringVar(value="0"),
            "tarefas_nao_cumpridas": tk.StringVar(value="0"),
            "ocorrencias_periodo": tk.StringVar(value="0"),
            "atrasos_periodo": tk.StringVar(value="0"),
        }
        self._dashboard_start_var = tk.StringVar()
        self._dashboard_end_var = tk.StringVar()
        self._occ_start_var = tk.StringVar()
        self._occ_end_var = tk.StringVar()
        self._occ_collaborator_var = tk.StringVar()
        self._occ_type_var = tk.StringVar(value="Todos")
        self._occ_status_var = tk.StringVar(value="Todos")
        self._point_date_var = tk.StringVar(value=self._today_text())
        self._point_collaborator_var = tk.StringVar()
        self._report_month_var = tk.StringVar(value=self._current_month_text())
        self.pack(fill="both", expand=True)
        self._configure_styles()
        self._build()
        self._show("dashboard")
        self._refresh_all()

    def _configure_styles(self) -> None:
        style = ttb.Style()
        style.configure("App.TFrame", background=BACKGROUND)
        style.configure("Content.TFrame", background=BACKGROUND)
        style.configure("Card.TFrame", background=WHITE, relief="flat")
        style.configure("Sidebar.TFrame", background=PRIMARY)
        style.configure("SidebarTitle.TLabel", background=PRIMARY, foreground=WHITE, font=("Segoe UI", 14, "bold"))
        style.configure("SidebarSub.TLabel", background=PRIMARY, foreground="#D8EBFF", font=("Segoe UI", 9))
        style.configure("SidebarFooter.TLabel", background=PRIMARY, foreground="#D8EBFF", font=("Segoe UI", 8))
        style.configure("SidebarFooterName.TLabel", background=PRIMARY, foreground=WHITE, font=("Segoe UI", 9, "bold"))
        style.configure("PageTitle.TLabel", background=BACKGROUND, foreground=PRIMARY_DARK, font=("Segoe UI", 16, "bold"))
        style.configure("Hint.TLabel", background=BACKGROUND, foreground=MUTED)
        style.configure("Section.TLabel", background=BACKGROUND, foreground="#1F2D3D", font=("Segoe UI", 12, "bold"))
        style.configure("CardTitle.TLabel", background=WHITE, foreground=MUTED)
        style.configure("CardValue.TLabel", background=WHITE, foreground=PRIMARY, font=("Segoe UI", 20, "bold"))
        style.configure("Status.TFrame", background=WHITE)
        style.configure("Status.TLabel", background=WHITE, foreground="#475569")
        style.configure(
            "Sidebar.TButton",
            font=("Segoe UI", 10),
            background=PRIMARY,
            foreground=WHITE,
            bordercolor=PRIMARY,
            focusthickness=0,
            padding=(10, 8),
        )
        style.map(
            "Sidebar.TButton",
            background=[("active", PRIMARY_DARK), ("pressed", PRIMARY_DARK)],
            foreground=[("active", WHITE), ("pressed", WHITE)],
        )
        style.configure(
            "SidebarActive.TButton",
            font=("Segoe UI", 10, "bold"),
            background=ACTIVE_BLUE,
            foreground=PRIMARY_DARK,
            bordercolor=ACTIVE_BLUE,
            focusthickness=0,
            padding=(10, 8),
        )
        style.map(
            "SidebarActive.TButton",
            background=[("active", ACTIVE_BLUE), ("pressed", ACTIVE_BLUE)],
            foreground=[("active", PRIMARY_DARK), ("pressed", PRIMARY_DARK)],
        )
        style.configure("Treeview", rowheight=30, font=("Segoe UI", 10), background=WHITE, fieldbackground=WHITE)
        style.configure(
            "Treeview.Heading",
            anchor="center",
            background=PRIMARY,
            foreground=WHITE,
            font=("Segoe UI", 10, "bold"),
        )

    def _build(self) -> None:
        self.winfo_toplevel().title(APP_TITLE)
        self.winfo_toplevel().configure(background=BACKGROUND)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar = ttb.Frame(self, style="Sidebar.TFrame", padding=(16, 18), width=230)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        ttb.Label(
            sidebar,
            text="Controle de\nPonto",
            style="SidebarTitle.TLabel",
            anchor="center",
            justify="center",
        ).pack(fill="x")
        ttb.Label(
            sidebar,
            text="Ponto, tarefas e ocorrências",
            style="SidebarSub.TLabel",
            anchor="center",
            justify="center",
            wraplength=180,
        ).pack(fill="x", pady=(4, 18))

        nav_area = ttb.Frame(sidebar, style="Sidebar.TFrame")
        nav_area.pack(fill="x")
        for key, label in [
            ("dashboard", "Dashboard"),
            ("colaboradores", "Colaboradores"),
            ("setores", "Setores"),
            ("metas", "Metas"),
            ("ponto", "Jornadas / Ponto"),
            ("tarefas", "Tarefas / POPs"),
            ("ocorrencias", "Ocorrências"),
            ("bot", "Bot WhatsApp"),
            ("manutencao", "Manutenção"),
        ]:
            btn = ttb.Button(nav_area, text=label, style="Sidebar.TButton", command=lambda k=key: self._show(k))
            btn.pack(fill="x", pady=(0, 8))
            self._nav_buttons[key] = btn

        footer = ttb.Frame(sidebar, style="Sidebar.TFrame")
        footer.pack(side="bottom", fill="x", pady=(18, 0))
        if self.on_logout:
            ttb.Button(
                footer,
                text="Sair do administrador",
                command=self.on_logout,
                bootstyle="light-outline",
            ).pack(fill="x", pady=(0, 12))
        ttb.Label(
            footer,
            text="Desenvolvido por",
            style="SidebarFooter.TLabel",
            anchor="center",
            justify="center",
        ).pack(fill="x")
        ttb.Label(
            footer,
            text="Miguel Olimpio",
            style="SidebarFooterName.TLabel",
            anchor="center",
            justify="center",
        ).pack(fill="x", pady=(2, 0))
        ttb.Label(
            footer,
            text="Agente Local de Inovação",
            style="SidebarFooter.TLabel",
            anchor="center",
            justify="center",
            wraplength=170,
        ).pack(fill="x", pady=(2, 0))

        host = ttb.Frame(self, padding=(20, 16), style="Content.TFrame")
        host.grid(row=0, column=1, sticky="nsew")
        host.columnconfigure(0, weight=1)
        host.rowconfigure(0, weight=1)

        self.pages = {key: ttb.Frame(host, style="Content.TFrame") for key in self._nav_buttons}
        for page in self.pages.values():
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._build_dashboard(self.pages["dashboard"])
        self._build_collaborators(self.pages["colaboradores"])
        self._build_sectors(self.pages["setores"])
        self._build_goals(self.pages["metas"])
        self._build_time_clock(self.pages["ponto"])
        self._build_tasks(self.pages["tarefas"])
        self._build_occurrences(self.pages["ocorrencias"])
        self._build_bot(self.pages["bot"])
        self._build_maintenance(self.pages["manutencao"])

        status = ttb.Frame(self, padding=(12, 6), style="Status.TFrame")
        status.grid(row=1, column=0, columnspan=2, sticky="ew")
        ttb.Label(status, textvariable=self._status_var, style="Status.TLabel").pack(side="left")

    def _show(self, key: str) -> None:
        self._current = key
        for nav_key, btn in self._nav_buttons.items():
            btn.configure(style="SidebarActive.TButton" if nav_key == key else "Sidebar.TButton")
        self.pages[key].tkraise()
        self._refresh_all()

    def _section_title(self, parent: ttb.Frame, title: str, hint: str) -> None:
        ttb.Label(parent, text=title, style="PageTitle.TLabel", wraplength=820, justify="left").pack(anchor="w")
        ttb.Label(parent, text=hint, style="Hint.TLabel", wraplength=860, justify="left").pack(anchor="w", pady=(2, 14))

    def _build_dashboard(self, parent: ttb.Frame) -> None:
        parent = self._make_scrollable_page(parent)
        self._section_title(
            parent,
            "Dashboard",
            "Visão operacional por período, com pendências, ocorrências e rankings para o gestor agir mais rápido.",
        )
        today_text = self._today_text()
        self._dashboard_start_var.set(today_text)
        self._dashboard_end_var.set(today_text)

        filters = ttb.Frame(parent, style="Content.TFrame")
        filters.pack(fill="x", pady=(0, 12))
        ttb.Label(filters, text="Data inicial").pack(side="left")
        ttb.Entry(filters, textvariable=self._dashboard_start_var, width=12).pack(side="left", padx=(6, 12))
        ttb.Label(filters, text="Data final").pack(side="left")
        ttb.Entry(filters, textvariable=self._dashboard_end_var, width=12).pack(side="left", padx=(6, 12))
        ttb.Button(filters, text="Atualizar", command=self._refresh_dashboard, bootstyle="secondary-outline").pack(side="left")
        ttb.Label(filters, text="M\u00eas pagamento").pack(side="left", padx=(18, 6))
        ttb.Entry(filters, textvariable=self._report_month_var, width=10).pack(side="left", padx=(0, 8))
        ttb.Button(
            filters,
            text="Gerar relat\u00f3rio de pagamento",
            command=self._generate_payment_report,
            bootstyle="info-outline",
        ).pack(side="left")
        ttb.Button(
            filters,
            text="Ver frequência",
            command=self._show_frequency_report,
            bootstyle="secondary-outline",
        ).pack(side="left", padx=(8, 0))
        ttb.Button(
            filters,
            text="Verificar pendências",
            command=self._verify_dashboard_pending,
            bootstyle="warning",
        ).pack(side="right")

        cards = ttb.Frame(parent, style="Content.TFrame")
        cards.pack(fill="x", pady=(0, 14))
        card_defs = [
            ("presentes", "Presentes"),
            ("tarefas_dia", "Tarefas do dia"),
            ("tarefas_cumpridas", "Cumpridas"),
            ("tarefas_parciais", "Parciais"),
            ("tarefas_atrasadas", "Atrasadas"),
            ("tarefas_nao_cumpridas", "Não cumpridas"),
            ("ocorrencias_periodo", "Ocorrências"),
            ("atrasos_periodo", "Atrasos"),
        ]
        for idx, (key, label) in enumerate(card_defs):
            card = ttb.Frame(cards, padding=10, style="Card.TFrame")
            card.grid(row=idx // 4, column=idx % 4, sticky="ew", padx=(0, 10), pady=(0, 10))
            cards.columnconfigure(idx % 4, weight=1)
            ttb.Label(card, text=label, style="CardTitle.TLabel").pack(anchor="w")
            ttb.Label(card, textvariable=self._dash_vars[key], style="CardValue.TLabel").pack(anchor="w")

        overview = ttb.Frame(parent, style="Content.TFrame")
        overview.pack(fill="both", expand=True)
        overview.columnconfigure(0, weight=1)
        overview.columnconfigure(1, weight=1)

        chart_box = ttb.Labelframe(overview, text="Gráfico de ocorrências por tipo", padding=10)
        chart_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 10))
        self.dashboard_occurrence_chart = ttb.Frame(chart_box)
        self.dashboard_occurrence_chart.pack(fill="both", expand=True)

        critical_box = ttb.Labelframe(overview, text="Tarefas críticas", padding=8)
        critical_box.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 10))
        self.dashboard_critical_tree = self._make_tree(
            critical_box,
            [("nome", "Tarefa", 180), ("horario", "Horário", 120), ("status", "Status", 110), ("setor", "Setor", 100)],
            height=5,
        )

        failed_box = ttb.Labelframe(overview, text="Ranking de tarefas com mais falhas", padding=8)
        failed_box.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(0, 10))
        self.dashboard_failed_tasks_tree = self._make_tree(
            failed_box,
            [("tarefa", "Tarefa", 240), ("falhas", "Falhas", 80)],
            height=5,
        )

        late_box = ttb.Labelframe(overview, text="Ranking de colaboradores com atrasos", padding=8)
        late_box.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=(0, 10))
        self.dashboard_late_collaborators_tree = self._make_tree(
            late_box,
            [("colaborador", "Colaborador", 240), ("atrasos", "Atrasos", 80)],
            height=5,
        )

        ttb.Label(parent, text="Últimas ocorrências do período", style="Section.TLabel").pack(anchor="w", pady=(4, 0))
        self.dashboard_occ_tree = self._make_tree(
            parent,
            [("data", "Data", 90), ("tipo", "Tipo", 180), ("colaborador", "Colaborador", 160), ("tarefa", "Tarefa", 180)],
            height=6,
        )

    def _build_collaborators(self, parent: ttb.Frame) -> None:
        self._section_title(parent, "Colaboradores", "Cadastro simples de equipe ativa e inativa.")
        bar = ttb.Frame(parent, style="Content.TFrame")
        bar.pack(fill="x", pady=(0, 8))
        ttb.Button(bar, text="Novo colaborador", command=self._new_collaborator, bootstyle="primary").pack(side="left")
        ttb.Button(bar, text="Editar", command=self._edit_collaborator, bootstyle="secondary-outline").pack(
            side="left", padx=(8, 0)
        )
        ttb.Button(bar, text="Ativar", command=lambda: self._set_collaborator_active(True), bootstyle="success").pack(
            side="left", padx=(8, 0)
        )
        ttb.Button(
            bar,
            text="Inativar",
            command=lambda: self._set_collaborator_active(False),
            bootstyle="danger-outline",
        ).pack(side="left", padx=(8, 0))
        self.collaborator_tree = self._make_tree(
            parent,
            [
                ("nome", "Nome", 220),
                ("cargo", "Cargo", 130),
                ("telefone", "Telefone", 120),
                ("setor", "Setor", 140),
                ("jornada", "Jornada", 180),
                ("salario", "Salário", 110),
                ("status", "Status", 90),
                ("data_cadastro", "Cadastro", 110),
            ],
        )

    def _build_sectors(self, parent: ttb.Frame) -> None:
        self._section_title(
            parent,
            "Setores",
            "Cadastre os setores da empresa. Colaboradores e tarefas usam esta lista para definir responsabilidades.",
        )
        bar = ttb.Frame(parent, style="Content.TFrame")
        bar.pack(fill="x", pady=(0, 8))
        ttb.Button(bar, text="Novo setor", command=self._new_sector, bootstyle="primary").pack(side="left")
        ttb.Button(bar, text="Editar", command=self._edit_sector, bootstyle="secondary-outline").pack(side="left", padx=(8, 0))
        ttb.Button(bar, text="Ativar", command=lambda: self._set_sector_active(True), bootstyle="success").pack(side="left", padx=(8, 0))
        ttb.Button(bar, text="Inativar", command=lambda: self._set_sector_active(False), bootstyle="danger-outline").pack(side="left", padx=(8, 0))
        self.sector_tree = self._make_tree(
            parent,
            [
                ("nome", "Setor", 220),
                ("descricao", "Descri??o", 320),
                ("active", "Ativo", 90),
                ("data_cadastro", "Cadastro", 120),
            ],
            height=14,
        )

    def _build_goals(self, parent: ttb.Frame) -> None:
        self._section_title(
            parent,
            "Metas",
            "Cadastre metas coletivas e individuais por mês para calcular bônus gerenciais no relatório de pagamento.",
        )
        bar = ttb.Frame(parent, style="Content.TFrame")
        bar.pack(fill="x", pady=(0, 8))
        ttb.Button(bar, text="Cadastrar meta", command=self._new_goal, bootstyle="primary").pack(side="left")
        ttb.Button(bar, text="Editar meta", command=self._edit_goal, bootstyle="secondary-outline").pack(side="left", padx=(8, 0))
        ttb.Button(bar, text="Ativar", command=lambda: self._set_goal_active(True), bootstyle="success").pack(side="left", padx=(8, 0))
        ttb.Button(bar, text="Inativar", command=lambda: self._set_goal_active(False), bootstyle="danger-outline").pack(side="left", padx=(8, 0))
        self.goal_tree = self._make_tree(
            parent,
            [
                ("nome", "Meta", 180),
                ("tipo", "Tipo", 90),
                ("periodo", "Mês", 80),
                ("bonus", "Bônus", 100),
                ("meta", "Meta", 100),
                ("realizado", "Realizado", 100),
                ("atingida", "Atingida", 80),
                ("colaborador", "Colaborador", 150),
                ("active", "Ativa", 70),
            ],
            height=14,
        )

    def _build_time_clock(self, parent: ttb.Frame) -> None:
        self._section_title(
            parent,
            "Jornadas / Ponto",
            "Configure jornadas e acompanhe os registros de ponto. A batida de ponto fica na interface do colaborador.",
        )
        bar = ttb.Frame(parent, style="Content.TFrame")
        bar.pack(fill="x", pady=(0, 8))
        ttb.Button(bar, text="Nova jornada", command=self._new_journey, bootstyle="primary").pack(side="left")
        ttb.Button(bar, text="Editar jornada", command=self._edit_journey, bootstyle="secondary-outline").pack(side="left", padx=(8, 0))
        ttb.Button(bar, text="Ativar", command=lambda: self._set_journey_active(True), bootstyle="success").pack(side="left", padx=(8, 0))
        ttb.Button(bar, text="Inativar", command=lambda: self._set_journey_active(False), bootstyle="danger-outline").pack(side="left", padx=(8, 0))

        self.journey_tree = self._make_tree(
            parent,
            [
                ("nome", "Nome", 220),
                ("tipo", "Tipo", 120),
                ("horario", "Horário/Escala", 220),
                ("tolerancia", "Tolerância", 100),
                ("dias", "Dias/Descrição", 240),
                ("active", "Ativa", 80),
            ],
            height=8,
        )

        ttb.Label(parent, text="Registros de ponto", style="Section.TLabel").pack(anchor="w", pady=(16, 4))
        filters = ttb.Frame(parent, style="Content.TFrame")
        filters.pack(fill="x", pady=(0, 8))
        ttb.Label(filters, text="Data").pack(side="left")
        ttb.Entry(filters, textvariable=self._point_date_var, width=12).pack(side="left", padx=(6, 12))
        ttb.Label(filters, text="Colaborador").pack(side="left")
        ttb.Entry(filters, textvariable=self._point_collaborator_var, width=24).pack(side="left", padx=(6, 12))
        ttb.Button(filters, text="Atualizar", command=self._refresh_points, bootstyle="secondary-outline").pack(side="left")

        self.time_tree = self._make_tree(
            parent,
            [("hora", "Hora", 80), ("nome", "Colaborador", 220), ("tipo", "Tipo", 100), ("obs", "Observações", 260)],
            height=8,
        )

    def _build_tasks(self, parent: ttb.Frame) -> None:
        self._section_title(parent, "Tarefas / POPs", "Cadastre tarefas obrigatórias e confira a execução diária.")
        bar = ttb.Frame(parent, style="Content.TFrame")
        bar.pack(fill="x", pady=(0, 8))
        ttb.Button(bar, text="Nova tarefa", command=self._new_task, bootstyle="primary").pack(side="left")
        ttb.Button(bar, text="Editar", command=self._edit_task, bootstyle="secondary-outline").pack(side="left", padx=(8, 0))
        ttb.Button(bar, text="Ativar", command=lambda: self._set_task_active(True), bootstyle="success").pack(
            side="left", padx=(8, 0)
        )
        ttb.Button(bar, text="Inativar", command=lambda: self._set_task_active(False), bootstyle="danger-outline").pack(
            side="left", padx=(8, 0)
        )
        self.task_tree = self._make_tree(
            parent,
            [
                ("nome", "Tarefa", 220),
                ("inicio", "Início", 80),
                ("limite", "Limite", 80),
                ("dias", "Dias", 150),
                ("setor", "Setor", 120),
                ("active", "Ativa", 80),
            ],
            height=7,
        )
        self.task_check_panel = TaskCheckPanel(parent, self.collaborator_service, self.task_service, self._after_change)
        self.task_check_panel.pack(fill="both", expand=True, pady=(18, 0))

    def _build_occurrences(self, parent: ttb.Frame) -> None:
        self._section_title(
            parent,
            "Ocorr\u00eancias",
            "Acompanhe atrasos, falhas e tarefas n\u00e3o cumpridas com filtros, status e tratativa.",
        )
        filters = ttb.Labelframe(parent, text="Filtros", padding=10)
        filters.pack(fill="x", pady=(0, 10))
        ttb.Label(filters, text="Data inicial").grid(row=0, column=0, sticky="w")
        ttb.Entry(filters, textvariable=self._occ_start_var, width=12).grid(row=1, column=0, sticky="ew", padx=(0, 8))
        ttb.Label(filters, text="Data final").grid(row=0, column=1, sticky="w")
        ttb.Entry(filters, textvariable=self._occ_end_var, width=12).grid(row=1, column=1, sticky="ew", padx=(0, 8))
        ttb.Label(filters, text="Colaborador").grid(row=0, column=2, sticky="w")
        ttb.Entry(filters, textvariable=self._occ_collaborator_var, width=22).grid(
            row=1, column=2, sticky="ew", padx=(0, 8)
        )
        ttb.Label(filters, text="Tipo").grid(row=0, column=3, sticky="w")
        self.occurrence_type_combo = ttb.Combobox(
            filters,
            textvariable=self._occ_type_var,
            values=["Todos"],
            state="readonly",
            width=24,
        )
        self.occurrence_type_combo.grid(row=1, column=3, sticky="ew", padx=(0, 8))
        ttb.Button(filters, text="Filtrar", command=self._refresh_occurrences, bootstyle="primary").grid(
            row=1, column=4, sticky="ew", padx=(0, 6)
        )
        ttb.Button(filters, text="Limpar", command=self._clear_occurrence_filters, bootstyle="secondary-outline").grid(
            row=1, column=5, sticky="ew"
        )
        for idx in range(6):
            filters.columnconfigure(idx, weight=1 if idx in {2, 3} else 0)

        actions = ttb.Frame(parent, style="Content.TFrame")
        actions.pack(fill="x", pady=(0, 8))
        ttb.Button(actions, text="Editar tratativa", command=self._edit_occurrence, bootstyle="primary").pack(side="left")
        ttb.Button(actions, text="Abonar falta", command=self._waive_occurrence, bootstyle="info-outline").pack(side="left", padx=(8, 0))
        ttb.Button(actions, text="Exportar PDF", command=self._export_occurrences_pdf, bootstyle="secondary-outline").pack(
            side="right"
        )

        self.occurrence_tree = self._make_tree(
            parent,
            [
                ("data", "Data", 90),
                ("tipo", "Tipo", 170),
                ("colaborador", "Colaborador", 160),
                ("tarefa", "Tarefa", 160),
                ("status", "Status", 95),
                ("responsavel", "Respons\u00e1vel", 150),
                ("acao", "A\u00e7\u00e3o tomada", 220),
                ("descricao", "Descri\u00e7\u00e3o", 300),
            ],
        )
        self.occurrence_tree.tag_configure("excused", background="#D8F5D0")
        self.occurrence_tree.tag_configure("absence", background="#FFE0E0")
        self.occurrence_tree.tag_configure("task_issue", background="#FFF4CC")
        self.occurrence_tree.tag_configure("default", background="")

    def _build_bot(self, parent: ttb.Frame) -> None:
        parent = self._make_scrollable_page(parent)
        panel = BotPanel(parent, self.bot_service)
        panel.pack(fill="both", expand=True)

    def _build_maintenance(self, parent: ttb.Frame) -> None:
        parent = self._make_scrollable_page(parent)
        panel = MaintenancePanel(parent, self.maintenance_service)
        panel.pack(fill="both", expand=True)

    def _make_scrollable_page(self, parent: ttb.Frame) -> ttb.Frame:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        host = ttb.Frame(parent, style="Content.TFrame")
        host.pack(fill="both", expand=True)
        host.columnconfigure(0, weight=1)
        host.rowconfigure(0, weight=1)

        canvas = tk.Canvas(host, highlightthickness=0, background=BACKGROUND)
        scrollbar = ttb.Scrollbar(host, orient="vertical", command=canvas.yview)
        inner = ttb.Frame(canvas, style="Content.TFrame")
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(8, 0))

        inner.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))

        def on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                return

        def bind_mousewheel(_event=None):
            canvas.bind_all("<MouseWheel>", on_mousewheel)

        def unbind_mousewheel(_event=None):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", bind_mousewheel)
        canvas.bind("<Leave>", unbind_mousewheel)
        inner.bind("<Enter>", bind_mousewheel)
        inner.bind("<Leave>", unbind_mousewheel)
        canvas.bind("<Destroy>", unbind_mousewheel, add="+")
        return inner

    def _make_tree(self, parent: ttb.Frame, columns: list[tuple[str, str, int]], height: int = 14) -> ttk.Treeview:
        frame = ttb.Frame(parent, style="Content.TFrame")
        frame.pack(fill="both", expand=True)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        tree = ttk.Treeview(frame, columns=[col for col, _label, _width in columns], show="headings", height=height)
        y_scroll = ttb.Scrollbar(frame, orient="vertical", command=tree.yview)
        x_scroll = ttb.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        for col, label, width in columns:
            tree.heading(col, text=label, anchor="center")
            tree.column(col, width=width, minwidth=70, anchor="center")

        tree.bind("<Enter>", lambda _event, current=tree: self._bind_tree_mousewheel(current))
        tree.bind("<Leave>", lambda _event, current=tree: self._unbind_tree_mousewheel(current))
        return tree

    def _bind_tree_mousewheel(self, tree: ttk.Treeview) -> None:
        tree.bind_all("<MouseWheel>", lambda event: tree.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        tree.bind_all("<Shift-MouseWheel>", lambda event: tree.xview_scroll(int(-1 * (event.delta / 120)), "units"))

    def _unbind_tree_mousewheel(self, tree: ttk.Treeview) -> None:
        tree.unbind_all("<MouseWheel>")
        tree.unbind_all("<Shift-MouseWheel>")

    def _selected_id(self, tree: ttk.Treeview) -> str | None:
        selected = tree.selection()
        return str(selected[0]) if selected else None

    def _after_change(self) -> None:
        self._status_var.set("Dados atualizados.")
        self._refresh_all()

    def _refresh_all(self) -> None:
        self._refresh_dashboard()
        self._refresh_collaborators()
        self._refresh_sectors()
        self._refresh_goals()
        self._refresh_points()
        self._refresh_journeys()
        self._refresh_tasks()
        self._refresh_occurrences()
        if hasattr(self, "time_panel"):
            self.time_panel.refresh()
        if hasattr(self, "task_check_panel"):
            self.task_check_panel.refresh()

    def _today_text(self) -> str:
        from app.utils.dates import format_date

        return format_date()

    def _current_month_text(self) -> str:
        today = date.today()
        return f"{today.month:02d}/{today.year}"

    def _generate_monthly_report(self) -> None:
        try:
            path = self.monthly_report_service.generate_pdf(self._report_month_var.get())
        except Exception as exc:
            messagebox.showerror("Relat\u00f3rio mensal", f"N\u00e3o foi poss\u00edvel gerar o relat\u00f3rio.\n\n{exc}")
            return
        prompt_open_generated_file(self, path, title="Relat\u00f3rio mensal", message_prefix="PDF salvo em:")

    def _generate_payment_report(self) -> None:
        try:
            path = self.monthly_report_service.generate_payment_pdf(self._report_month_var.get())
        except Exception as exc:
            messagebox.showerror(
                "Relat\u00f3rio de pagamento",
                f"N\u00e3o foi poss\u00edvel gerar o relat\u00f3rio de pagamento.\n\n{exc}",
            )
            return
        prompt_open_generated_file(
            self,
            path,
            title="Relat\u00f3rio de pagamento",
            message_prefix="PDF salvo em:",
        )

    def _show_frequency_report(self) -> None:
        FrequencyDialog(self, self.monthly_report_service, self._report_month_var.get())

    def _dashboard_period(self) -> tuple[str, str] | None:
        try:
            start, end = self.dashboard_service.normalize_period(
                self._dashboard_start_var.get(),
                self._dashboard_end_var.get(),
            )
        except Exception as exc:
            messagebox.showwarning("Dashboard", f"Informe datas válidas no formato DD/MM/AAAA.\n\n{exc}")
            return None
        self._dashboard_start_var.set(start)
        self._dashboard_end_var.set(end)
        return start, end

    def _refresh_dashboard(self) -> None:
        if not hasattr(self, "dashboard_occ_tree"):
            return
        period = self._dashboard_period()
        if period is None:
            return
        start, end = period
        summary = self.dashboard_service.summary_by_period(start, end)
        for key, var in self._dash_vars.items():
            var.set(str(summary.get(key, 0)))

        self._refresh_occurrence_chart(self.dashboard_service.occurrences_by_type(start, end))
        self._fill_tree(
            self.dashboard_critical_tree,
            [
                (row.get("nome", ""), row.get("horario", ""), row.get("status", ""), row.get("nome_setor", ""))
                for row in self.dashboard_service.critical_tasks(end)
            ],
        )
        self._fill_tree(
            self.dashboard_failed_tasks_tree,
            [(row.get("nome_tarefa", ""), row.get("falhas", 0)) for row in self.dashboard_service.failed_tasks_ranking(start, end)],
        )
        self._fill_tree(
            self.dashboard_late_collaborators_tree,
            [
                (row.get("nome_colaborador", ""), row.get("atrasos", 0))
                for row in self.dashboard_service.late_collaborators_ranking(start, end)
            ],
        )
        self._fill_tree(
            self.dashboard_occ_tree,
            [
                (row.get("data", ""), row.get("tipo", ""), row.get("nome_colaborador", ""), row.get("nome_tarefa", ""))
                for row in self.dashboard_service.recent_occurrences(start, end, 8)
            ],
            prefix="dash-occ",
        )

    def _refresh_occurrence_chart(self, rows: list[dict]) -> None:
        for child in self.dashboard_occurrence_chart.winfo_children():
            child.destroy()
        if not rows:
            ttb.Label(
                self.dashboard_occurrence_chart,
                text="Nenhuma ocorrência no período.",
                foreground=MUTED,
            ).pack(anchor="w")
            return
        max_value = max(int(row.get("quantidade", 0) or 0) for row in rows) or 1
        for row in rows[:6]:
            label = str(row.get("tipo", ""))
            value = int(row.get("quantidade", 0) or 0)
            line = ttb.Frame(self.dashboard_occurrence_chart)
            line.pack(fill="x", pady=3)
            ttb.Label(line, text=label, width=28, anchor="w").pack(side="left")
            bar = ttb.Frame(line, style="Card.TFrame", height=14)
            bar.pack(side="left", fill="x", expand=True, padx=(6, 8))
            fill = ttb.Frame(bar, bootstyle="primary")
            fill.place(relx=0, rely=0, relwidth=max(value / max_value, 0.04), relheight=1)
            ttb.Label(line, text=str(value), width=4, anchor="e").pack(side="right")

    def _fill_tree(self, tree: ttk.Treeview, rows: list[tuple], prefix: str = "dash") -> None:
        tree.delete(*tree.get_children())
        for idx, values in enumerate(rows):
            tree.insert("", "end", iid=f"{prefix}-{idx}", values=values)

    def _verify_dashboard_pending(self) -> None:
        try:
            created = self.task_service.verify_pending_tasks()
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message)
            return
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))
            return
        messagebox.showinfo("Pendências", f"Ocorrências criadas: {len(created)}.")
        self._after_change()

    def _refresh_sectors(self) -> None:
        if not hasattr(self, "sector_tree"):
            return
        self.sector_tree.delete(*self.sector_tree.get_children())
        for row in self.sector_service.list_all():
            self.sector_tree.insert(
                "",
                "end",
                iid=str(row.get("setor_id")),
                values=(
                    row.get("nome", ""),
                    row.get("descricao", ""),
                    yes_no(row.get("active", True)),
                    row.get("data_cadastro", ""),
                ),
            )

    def _refresh_collaborators(self) -> None:
        if not hasattr(self, "collaborator_tree"):
            return
        self.collaborator_tree.delete(*self.collaborator_tree.get_children())
        for row in self.collaborator_service.list_all():
            self.collaborator_tree.insert(
                "",
                "end",
                iid=str(row.get("colaborador_id")),
                values=(
                    row.get("nome", ""),
                    row.get("cargo", ""),
                    row.get("telefone", ""),
                    row.get("nome_setor", ""),
                    self._journey_label_by_id(str(row.get("jornada_id", ""))),
                    self._money(row.get("salario_base", 0)),
                    row.get("status", ""),
                    row.get("data_cadastro", ""),
                ),
            )

    def _refresh_goals(self) -> None:
        if not hasattr(self, "goal_tree"):
            return
        self.goal_tree.delete(*self.goal_tree.get_children())
        for row in self.goal_service.list_all():
            self.goal_tree.insert(
                "",
                "end",
                iid=str(row.get("meta_id")),
                values=(
                    row.get("nome_meta", ""),
                    row.get("tipo_meta", ""),
                    row.get("periodo_mes", ""),
                    self._money(row.get("valor_bonus", 0)),
                    self._money(row.get("valor_meta", 0)),
                    self._money(row.get("valor_realizado", 0)),
                    yes_no(row.get("atingida", False)),
                    row.get("nome_colaborador", ""),
                    yes_no(row.get("active", True)),
                ),
            )

    def _refresh_journeys(self) -> None:
        if not hasattr(self, "journey_tree"):
            return
        self.journey_tree.delete(*self.journey_tree.get_children())
        for row in self.journey_service.list_all():
            if row.get("tipo_escala") == SCALE_TYPE_SCALE:
                horario = f"Início {row.get('horario_inicio_escala') or row.get('entrada', '')}"
                descricao = f"{row.get('descricao_escala', '')} ({row.get('horas_trabalho', 0)}h trabalho / {row.get('horas_descanso', 0)}h descanso)"
            else:
                horario = f"{row.get('entrada', '')} até {row.get('saida', '')}"
                descricao = row.get("dias_semana", "")
            self.journey_tree.insert(
                "",
                "end",
                iid=str(row.get("jornada_id")),
                values=(
                    row.get("nome", ""),
                    row.get("tipo_escala", ""),
                    horario,
                    f"{row.get('tolerancia_minutos', 0)} min",
                    descricao,
                    yes_no(row.get("active", True)),
                ),
            )

    def _refresh_points(self) -> None:
        if not hasattr(self, "time_tree"):
            return
        self.time_tree.delete(*self.time_tree.get_children())
        day = self._point_date_var.get() or self._today_text()
        collaborator_filter = self._point_collaborator_var.get().strip().lower()
        for row in self.time_clock_service.list_today(day):
            if collaborator_filter and collaborator_filter not in str(row.get("nome_colaborador", "")).lower():
                continue
            self.time_tree.insert(
                "",
                "end",
                iid=str(row.get("ponto_id")),
                values=(row.get("hora", ""), row.get("nome_colaborador", ""), row.get("tipo_ponto", ""), row.get("observacoes", "")),
            )

    def _refresh_tasks(self) -> None:
        if not hasattr(self, "task_tree"):
            return
        self.task_tree.delete(*self.task_tree.get_children())
        for row in self.task_service.list_tasks():
            self.task_tree.insert(
                "",
                "end",
                iid=str(row.get("tarefa_id")),
                values=(
                    row.get("nome", ""),
                    row.get("horario_inicio", ""),
                    row.get("horario_limite", ""),
                    row.get("dias_semana", ""),
                    row.get("nome_setor", ""),
                    yes_no(row.get("active", True)),
                ),
            )

    def _refresh_occurrence_filter_options(self) -> None:
        if hasattr(self, "occurrence_type_combo"):
            current = self._occ_type_var.get() or "Todos"
            values = ["Todos"] + self.occurrence_service.occurrence_types()
            self.occurrence_type_combo.configure(values=values)
            self._occ_type_var.set(current if current in values else "Todos")

    def _occurrence_rows_for_filters(self) -> list[dict] | None:
        try:
            return self.occurrence_service.filter_occurrences(
                data_inicio=self._occ_start_var.get(),
                data_fim=self._occ_end_var.get(),
                colaborador=self._occ_collaborator_var.get(),
                tipo=self._occ_type_var.get(),
                status="",
            )
        except Exception as exc:
            messagebox.showwarning("Ocorr\u00eancias", f"Revise os filtros informados.\n\n{exc}")
            return None

    def _refresh_occurrences(self) -> None:
        if not hasattr(self, "occurrence_tree"):
            return
        self._refresh_occurrence_filter_options()
        rows = self._occurrence_rows_for_filters()
        if rows is None:
            return
        self.occurrence_tree.delete(*self.occurrence_tree.get_children())
        for row in rows:
            tag = self._occurrence_tag(row)
            self.occurrence_tree.insert(
                "",
                "end",
                iid=str(row.get("ocorrencia_id")),
                values=(
                    row.get("data", ""),
                    row.get("tipo", ""),
                    row.get("nome_colaborador", ""),
                    row.get("nome_tarefa", ""),
                    yes_no(row.get("abonado", False)) if str(row.get("tipo", "")) == OCCURRENCE_POINT_MISSING else "-",
                    row.get("nome_setor", ""),
                    row.get("descricao", ""),
                ),
                tags=(tag,),
            )

    def _occurrence_tag(self, row: dict) -> str:
        occurrence_type = str(row.get("tipo", ""))
        if occurrence_type == OCCURRENCE_POINT_MISSING:
            return "excused" if bool(row.get("abonado", False)) else "absence"
        if occurrence_type in {OCCURRENCE_TASK_LATE, OCCURRENCE_TASK_MISSED}:
            return "task_issue"
        return "default"

    def _clear_occurrence_filters(self) -> None:
        self._occ_start_var.set("")
        self._occ_end_var.set("")
        self._occ_collaborator_var.set("")
        self._occ_type_var.set("Todos")
        self._refresh_occurrences()

    def _selected_occurrence(self) -> dict | None:
        occurrence_id = self._selected_id(self.occurrence_tree)
        if not occurrence_id:
            messagebox.showwarning("Ocorr\u00eancias", "Selecione uma ocorr\u00eancia.")
            return None
        occurrence = self.occurrence_service.get(occurrence_id)
        if not occurrence:
            messagebox.showwarning("Ocorr\u00eancias", "Ocorr\u00eancia n\u00e3o encontrada.")
            return None
        return occurrence

    def _edit_occurrence(self) -> None:
        occurrence = self._selected_occurrence()
        if not occurrence:
            return
        OccurrenceEditor(self, lambda payload: self._save_occurrence_treatment(occurrence["ocorrencia_id"], payload), occurrence)

    def _save_occurrence_treatment(self, occurrence_id: str, payload: dict) -> None:
        try:
            self.occurrence_service.update_treatment(occurrence_id, **payload)
            self._after_change()
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message)
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))

    def _mark_occurrence_status(self, status: str) -> None:
        occurrence = self._selected_occurrence()
        if not occurrence:
            return
        try:
            if status == OCCURRENCE_STATUS_RESOLVED:
                self.occurrence_service.mark_resolved(occurrence["ocorrencia_id"])
            else:
                self.occurrence_service.mark_pending(occurrence["ocorrencia_id"])
            self._after_change()
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message)
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))

    def _waive_occurrence(self) -> None:
        occurrence = self._selected_occurrence()
        if not occurrence:
            return
        WaiverDialog(self, lambda payload: self._save_occurrence_waiver(occurrence["ocorrencia_id"], payload), occurrence)

    def _save_occurrence_waiver(self, occurrence_id: str, payload: dict) -> None:
        try:
            self.occurrence_service.waive_occurrence(occurrence_id, **payload)
            self._after_change()
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message)
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))

    def _export_occurrences_pdf(self) -> None:
        rows = self._occurrence_rows_for_filters()
        if rows is None:
            return
        try:
            path = self.occurrence_service.export_pdf(
                rows,
                data_inicio=self._occ_start_var.get(),
                data_fim=self._occ_end_var.get(),
            )
        except Exception as exc:
            messagebox.showerror("PDF", f"N\u00e3o foi poss\u00edvel gerar o PDF.\n\n{exc}")
            return
        prompt_open_generated_file(self, path, title="PDF de ocorr\u00eancias", message_prefix="PDF salvo em:")

    def _collaborator_options(self) -> list[tuple[str, str]]:
        return [(str(row.get("colaborador_id", "")), str(row.get("nome", ""))) for row in self.collaborator_service.list_active()]

    def _sector_options(self) -> list[tuple[str, str]]:
        return self.sector_service.options()

    def _journey_options(self) -> list[tuple[str, str]]:
        return [(str(row.get("jornada_id", "")), str(row.get("nome", ""))) for row in self.journey_service.list_active()]

    def _journey_label_by_id(self, jornada_id: str) -> str:
        if not jornada_id:
            return ""
        journey = self.journey_service.get(jornada_id)
        return str((journey or {}).get("nome", ""))

    def _money(self, value) -> str:
        try:
            number = float(value or 0)
        except (TypeError, ValueError):
            number = 0.0
        return f"R$ {number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _new_goal(self) -> None:
        GoalEditor(self, lambda payload: self._save_new_goal(payload), collaborator_options=self._collaborator_options())

    def _save_new_goal(self, payload: dict) -> None:
        self.goal_service.create_goal(**payload)
        self._after_change()

    def _edit_goal(self) -> None:
        meta_id = self._selected_id(self.goal_tree)
        if not meta_id:
            messagebox.showwarning("Metas", "Selecione uma meta.")
            return
        initial = self.goal_service.get(meta_id)
        GoalEditor(self, lambda payload: self._save_existing_goal(meta_id, payload), initial, collaborator_options=self._collaborator_options())

    def _save_existing_goal(self, meta_id: str, payload: dict) -> None:
        self.goal_service.update_goal(meta_id, **payload)
        self._after_change()

    def _set_goal_active(self, active: bool) -> None:
        meta_id = self._selected_id(self.goal_tree)
        if not meta_id:
            messagebox.showwarning("Metas", "Selecione uma meta.")
            return
        try:
            self.goal_service.set_active(meta_id, active)
            self._after_change()
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message)
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))

    def _new_sector(self) -> None:
        SectorEditor(self, lambda payload: self._save_new_sector(payload))

    def _save_new_sector(self, payload: dict) -> None:
        self.sector_service.create_sector(**payload)
        self._after_change()

    def _edit_sector(self) -> None:
        setor_id = self._selected_id(self.sector_tree)
        if not setor_id:
            messagebox.showwarning("Setores", "Selecione um setor.")
            return
        initial = self.sector_service.get(setor_id)
        SectorEditor(self, lambda payload: self._save_existing_sector(setor_id, payload), initial)

    def _save_existing_sector(self, setor_id: str, payload: dict) -> None:
        self.sector_service.update_sector(setor_id, **payload)
        self._after_change()

    def _set_sector_active(self, active: bool) -> None:
        setor_id = self._selected_id(self.sector_tree)
        if not setor_id:
            messagebox.showwarning("Setores", "Selecione um setor.")
            return
        try:
            self.sector_service.set_active(setor_id, active)
            self._after_change()
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message)
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))

    def _new_collaborator(self) -> None:
        CollaboratorEditor(
            self,
            lambda payload: self._save_new_collaborator(payload),
            journey_options=self._journey_options(),
            sector_options=self._sector_options(),
        )

    def _save_new_collaborator(self, payload: dict) -> None:
        self.collaborator_service.create_collaborator(**payload)
        self._after_change()

    def _edit_collaborator(self) -> None:
        collaborator_id = self._selected_id(self.collaborator_tree)
        if not collaborator_id:
            messagebox.showwarning("Colaboradores", "Selecione um colaborador.")
            return
        initial = self.collaborator_service.get(collaborator_id)
        CollaboratorEditor(
            self,
            lambda payload: self._save_existing_collaborator(collaborator_id, payload),
            initial,
            journey_options=self._journey_options(),
            sector_options=self._sector_options(),
        )

    def _save_existing_collaborator(self, collaborator_id: str, payload: dict) -> None:
        self.collaborator_service.update_collaborator(collaborator_id, **payload)
        self._after_change()

    def _set_collaborator_active(self, active: bool) -> None:
        collaborator_id = self._selected_id(self.collaborator_tree)
        if not collaborator_id:
            messagebox.showwarning("Colaboradores", "Selecione um colaborador.")
            return
        try:
            self.collaborator_service.set_active(collaborator_id, active)
            self._after_change()
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message)
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))

    def _new_journey(self) -> None:
        JourneyEditor(self, lambda payload: self._save_new_journey(payload))

    def _save_new_journey(self, payload: dict) -> None:
        self.journey_service.create_journey(**payload)
        self._after_change()

    def _edit_journey(self) -> None:
        jornada_id = self._selected_id(self.journey_tree)
        if not jornada_id:
            messagebox.showwarning("Jornadas", "Selecione uma jornada.")
            return
        initial = self.journey_service.get(jornada_id)
        JourneyEditor(self, lambda payload: self._save_existing_journey(jornada_id, payload), initial)

    def _save_existing_journey(self, jornada_id: str, payload: dict) -> None:
        self.journey_service.update_journey(jornada_id, **payload)
        self._after_change()

    def _set_journey_active(self, active: bool) -> None:
        jornada_id = self._selected_id(self.journey_tree)
        if not jornada_id:
            messagebox.showwarning("Jornadas", "Selecione uma jornada.")
            return
        try:
            self.journey_service.set_active(jornada_id, active)
            self._after_change()
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message)
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))

    def _new_task(self) -> None:
        TaskEditor(self, lambda payload: self._save_new_task(payload), sector_options=self._sector_options())

    def _save_new_task(self, payload: dict) -> None:
        self.task_service.create_task(**payload)
        self._after_change()

    def _edit_task(self) -> None:
        task_id = self._selected_id(self.task_tree)
        if not task_id:
            messagebox.showwarning("Tarefas", "Selecione uma tarefa.")
            return
        initial = next((row for row in self.task_service.list_tasks() if str(row.get("tarefa_id")) == task_id), None)
        TaskEditor(self, lambda payload: self._save_existing_task(task_id, payload), initial, sector_options=self._sector_options())

    def _save_existing_task(self, task_id: str, payload: dict) -> None:
        self.task_service.update_task(task_id, **payload)
        self._after_change()

    def _set_task_active(self, active: bool) -> None:
        task_id = self._selected_id(self.task_tree)
        if not task_id:
            messagebox.showwarning("Tarefas", "Selecione uma tarefa.")
            return
        try:
            self.task_service.set_active(task_id, active)
            self._after_change()
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message)
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))
