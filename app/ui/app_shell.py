"""Casca principal que alterna entre colaborador e administrador."""

from __future__ import annotations

import tkinter as tk

import ttkbootstrap as ttb

from app.bot.bot_service import BotService

from app.services.collaborator_service import CollaboratorService
from app.services.dashboard_service import DashboardService
from app.services.occurrence_service import OccurrenceService
from app.services.sector_service import SectorService
from app.services.task_service import TaskService
from app.services.time_clock_service import TimeClockService
from app.services.journey_service import JourneyService
from app.services.monthly_report_service import MonthlyReportService
from app.services.goal_service import GoalService
from app.services.maintenance_service import MaintenanceService
from app.ui.app_mode import AppModeState
from app.ui.collaborator_view import CollaboratorView
from app.ui.login_dialog import AdminLoginDialog
from app.ui.main_window import MainWindow


class AppShell(ttb.Frame):
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
    ):
        super().__init__(master)
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
        self.mode_state = AppModeState()
        self.current_view: tk.Widget | None = None
        self.pack(fill="both", expand=True)
        self.show_collaborator()

    def _clear_current_view(self) -> None:
        if self.current_view is not None:
            self.current_view.destroy()
            self.current_view = None

    def show_collaborator(self) -> None:
        self.mode_state.exit_admin()
        self._clear_current_view()
        self.current_view = CollaboratorView(
            self,
            self.collaborator_service,
            self.time_clock_service,
            self.task_service,
            self.bot_service,
            self.request_admin_login,
            journey_service=self.journey_service,
        )
        self.current_view.pack(fill="both", expand=True)

    def request_admin_login(self) -> None:
        AdminLoginDialog(self, self.show_admin)

    def show_admin(self) -> None:
        self.mode_state.enter_admin()
        self._clear_current_view()
        self.current_view = MainWindow(
            self,
            self.collaborator_service,
            self.time_clock_service,
            self.task_service,
            self.occurrence_service,
            self.dashboard_service,
            self.journey_service,
            self.monthly_report_service,
            self.sector_service,
            self.goal_service,
            self.bot_service,
            self.maintenance_service,
            on_logout=self.show_collaborator,
        )

    def logout_admin(self) -> None:
        self.show_collaborator()
