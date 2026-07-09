"""Inicializacao do aplicativo desktop."""

from __future__ import annotations

import os
from dataclasses import dataclass
from tkinter import messagebox

import ttkbootstrap as ttb

from app.config.paths import (
    ensure_app_directories,
    get_colaboradores_db_path,
    get_database_path,
    get_ocorrencias_db_path,
    get_ponto_db_path,
    get_setores_db_path,
    get_bot_config_db_path,
    get_metas_db_path,
    get_tarefas_db_path,
)
from app.config.settings import APP_THEME, APP_TITLE
from app.repositories.collaborator_repository import CollaboratorRepository
from app.repositories.excel_database import ExcelDatabase
from app.repositories.occurrence_repository import OccurrenceRepository
from app.repositories.sector_repository import SectorRepository
from app.repositories.bot_config_repository import BotConfigRepository
from app.repositories.goal_repository import GoalRepository
from app.repositories.task_check_repository import TaskCheckRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.time_record_repository import TimeRecordRepository
from app.repositories.work_schedule_repository import WorkScheduleRepository
from app.repositories.journey_repository import JourneyRepository
from app.repositories.excel_schema import (
    COLLABORATORS_SHEETS_CONFIG,
    OCCURRENCES_SHEETS_CONFIG,
    POINT_SHEETS_CONFIG,
    SECTORS_SHEETS_CONFIG,
    BOT_SHEETS_CONFIG,
    GOALS_SHEETS_CONFIG,
    TASKS_SHEETS_CONFIG,
)
from app.services.collaborator_service import CollaboratorService
from app.services.dashboard_service import DashboardService
from app.services.occurrence_service import OccurrenceService
from app.services.sector_service import SectorService
from app.services.task_service import TaskService
from app.services.time_clock_service import TimeClockService
from app.services.journey_service import JourneyService
from app.services.monthly_report_service import MonthlyReportService
from app.services.startup_check_service import StartupCheckService
from app.services.goal_service import GoalService
from app.services.maintenance_service import MaintenanceService
from app.bot.bot_service import BotService
from app.ui.app_shell import AppShell
from app.ui.window_icon import apply_window_icon


@dataclass(slots=True)
class AppServices:
    collaborator_service: CollaboratorService
    time_clock_service: TimeClockService
    task_service: TaskService
    occurrence_service: OccurrenceService
    dashboard_service: DashboardService
    journey_service: JourneyService
    monthly_report_service: MonthlyReportService
    startup_check_service: StartupCheckService
    sector_service: SectorService
    goal_service: GoalService
    bot_service: BotService
    maintenance_service: MaintenanceService


@dataclass(slots=True)
class AppDatabases:
    colaboradores: ExcelDatabase
    ponto: ExcelDatabase
    tarefas: ExcelDatabase
    ocorrencias: ExcelDatabase
    setores: ExcelDatabase
    bot: ExcelDatabase
    metas: ExcelDatabase


def build_databases() -> AppDatabases:
    return AppDatabases(
        colaboradores=ExcelDatabase(
            db_path=get_colaboradores_db_path(),
            sheets_config=COLLABORATORS_SHEETS_CONFIG,
            backup_stem="colaboradores",
        ),
        ponto=ExcelDatabase(
            db_path=get_ponto_db_path(),
            sheets_config=POINT_SHEETS_CONFIG,
            backup_stem="ponto",
        ),
        tarefas=ExcelDatabase(
            db_path=get_tarefas_db_path(),
            sheets_config=TASKS_SHEETS_CONFIG,
            backup_stem="tarefas_pops",
        ),
        ocorrencias=ExcelDatabase(
            db_path=get_ocorrencias_db_path(),
            sheets_config=OCCURRENCES_SHEETS_CONFIG,
            backup_stem="ocorrencias",
        ),
        setores=ExcelDatabase(
            db_path=get_setores_db_path(),
            sheets_config=SECTORS_SHEETS_CONFIG,
            backup_stem="setores",
        ),
        bot=ExcelDatabase(
            db_path=get_bot_config_db_path(),
            sheets_config=BOT_SHEETS_CONFIG,
            backup_stem="bot_config",
        ),
        metas=ExcelDatabase(
            db_path=get_metas_db_path(),
            sheets_config=GOALS_SHEETS_CONFIG,
            backup_stem="metas",
        ),
    )


def remove_legacy_database() -> None:
    legacy_path = get_database_path()
    if os.path.isfile(legacy_path):
        os.remove(legacy_path)


def build_services(database: ExcelDatabase | None = None) -> AppServices:
    ensure_app_directories()
    if database is not None:
        database.ensure_database()
        collaborator_repo = CollaboratorRepository(database)
        time_repo = TimeRecordRepository(database)
        task_repo = TaskRepository(database)
        check_repo = TaskCheckRepository(database)
        occurrence_repo = OccurrenceRepository(database)
        sector_repo = SectorRepository(database)
        schedule_repo = WorkScheduleRepository(database)
        journey_repo = JourneyRepository(database)
        bot_repo = BotConfigRepository(database)
        goal_repo = GoalRepository(database)
    else:
        remove_legacy_database()
        databases = build_databases()
        for db in (
            databases.colaboradores,
            databases.ponto,
            databases.tarefas,
            databases.ocorrencias,
            databases.setores,
            databases.bot,
            databases.metas,
        ):
            db.ensure_database()

        collaborator_repo = CollaboratorRepository(databases.colaboradores)
        time_repo = TimeRecordRepository(databases.ponto)
        task_repo = TaskRepository(databases.tarefas)
        check_repo = TaskCheckRepository(databases.tarefas)
        occurrence_repo = OccurrenceRepository(databases.ocorrencias)
        sector_repo = SectorRepository(databases.setores)
        schedule_repo = WorkScheduleRepository(databases.ponto)
        journey_repo = JourneyRepository(databases.ponto)
        bot_repo = BotConfigRepository(databases.bot)
        goal_repo = GoalRepository(databases.metas)

    sector_service = SectorService(sector_repo)
    sector_service.ensure_default_sectors()
    goal_service = GoalService(goal_repo, collaborator_repo)
    collaborator_service = CollaboratorService(collaborator_repo, sector_service)
    occurrence_service = OccurrenceService(occurrence_repo)
    journey_service = JourneyService(journey_repo)
    time_clock_service = TimeClockService(time_repo, collaborator_repo, schedule_repo, occurrence_service, journey_repo)
    task_service = TaskService(
        task_repository=task_repo,
        check_repository=check_repo,
        collaborator_repository=collaborator_repo,
        occurrence_repository=occurrence_repo,
        time_clock_service=time_clock_service,
        occurrence_service=occurrence_service,
        journey_service=journey_service,
        sector_service=sector_service,
    )
    dashboard_service = DashboardService(time_clock_service, task_service, occurrence_service)
    monthly_report_service = MonthlyReportService(
        collaborator_service,
        journey_service,
        time_clock_service,
        task_service,
        occurrence_service,
        goal_service,
    )
    startup_check_service = StartupCheckService(
        collaborator_service,
        journey_service,
        time_clock_service,
        task_service,
        occurrence_service,
    )
    bot_service = BotService(
        bot_repo,
        collaborator_service,
        task_service,
        time_clock_service,
        journey_service,
    )
    maintenance_service = MaintenanceService()
    time_clock_service.add_record_listener(bot_service.notify_time_record)
    bot_service.ensure_default_config()
    return AppServices(
        collaborator_service,
        time_clock_service,
        task_service,
        occurrence_service,
        dashboard_service,
        journey_service,
        monthly_report_service,
        startup_check_service,
        sector_service,
        goal_service,
        bot_service,
        maintenance_service,
    )


def main() -> None:
    services = build_services()
    root = ttb.Window(themename=APP_THEME)
    root.title(APP_TITLE)
    root.geometry("1200x760")
    root.minsize(1100, 700)
    apply_window_icon(root)
    AppShell(
        root,
        services.collaborator_service,
        services.time_clock_service,
        services.task_service,
        services.occurrence_service,
        services.dashboard_service,
        services.journey_service,
        services.monthly_report_service,
        services.sector_service,
        services.goal_service,
        services.bot_service,
        services.maintenance_service,
    )

    def run_startup_checks() -> None:
        try:
            created = services.startup_check_service.verify_previous_day()
        except Exception:
            return
        if created:
            messagebox.showwarning(
                "Pendências do dia anterior",
                "Foram encontradas pendências do dia anterior.",
            )

    def on_close() -> None:
        try:
            services.bot_service.stop()
        except Exception:
            pass
        root.destroy()

    def start_whatsapp_bot() -> None:
        try:
            services.bot_service.start()
        except Exception:
            # O WhatsApp é opcional; falhas de conexão não podem impedir o uso do app.
            pass

    def run_auto_maintenance() -> None:
        try:
            services.maintenance_service.run_auto_if_due()
        except Exception:
            # A manutenção não pode impedir a abertura do app.
            pass

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.after(400, run_startup_checks)
    root.after(900, start_whatsapp_bot)
    root.after(1800, run_auto_maintenance)
    root.mainloop()
