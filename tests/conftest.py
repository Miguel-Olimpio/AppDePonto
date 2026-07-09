from __future__ import annotations

import pytest

from app.repositories.collaborator_repository import CollaboratorRepository
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import (
    COLLABORATORS_SHEETS_CONFIG,
    OCCURRENCES_SHEETS_CONFIG,
    POINT_SHEETS_CONFIG,
    SECTORS_SHEETS_CONFIG,
    BOT_SHEETS_CONFIG,
    GOALS_SHEETS_CONFIG,
    TASKS_SHEETS_CONFIG,
)
from app.repositories.occurrence_repository import OccurrenceRepository
from app.repositories.sector_repository import SectorRepository
from app.repositories.bot_config_repository import BotConfigRepository
from app.repositories.goal_repository import GoalRepository
from app.repositories.task_check_repository import TaskCheckRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.time_record_repository import TimeRecordRepository
from app.repositories.work_schedule_repository import WorkScheduleRepository
from app.repositories.journey_repository import JourneyRepository
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
from app.bot.bot_service import BotService


class DummyBotBridge:
    def __init__(self):
        self.status = "Conectado"
        self.sent = []
        self.session_dir = "data/wwebjs_auth"
        self.terminated_stale = 0

    def start(self, callback=None):
        self.status = "Conectado"
        if callback:
            callback({"event": "ready", "message": "dummy"})

    def stop(self):
        self.status = "Desconectado"

    def clear_session(self):
        self.status = "Desconectado"

    def send_message(self, phone, message, message_id=""):
        self.sent.append((phone, message, message_id))
        return True

    def has_saved_session(self):
        return False

    def terminate_stale_processes(self):
        self.terminated_stale += 1
        return 1

    @property
    def log_path(self):
        return "bot_test.log"


@pytest.fixture()
def stack(tmp_path):
    backup_dir = str(tmp_path / "backups")
    data_dir = tmp_path / "data"
    colaboradores_db = ExcelDatabase(
        db_path=str(data_dir / "colaboradores.xlsx"),
        sheets_config=COLLABORATORS_SHEETS_CONFIG,
        backup_dir=backup_dir,
        backup_stem="colaboradores",
    )
    ponto_db = ExcelDatabase(
        db_path=str(data_dir / "ponto.xlsx"),
        sheets_config=POINT_SHEETS_CONFIG,
        backup_dir=backup_dir,
        backup_stem="ponto",
    )
    tarefas_db = ExcelDatabase(
        db_path=str(data_dir / "tarefas_pops.xlsx"),
        sheets_config=TASKS_SHEETS_CONFIG,
        backup_dir=backup_dir,
        backup_stem="tarefas_pops",
    )
    ocorrencias_db = ExcelDatabase(
        db_path=str(data_dir / "ocorrencias.xlsx"),
        sheets_config=OCCURRENCES_SHEETS_CONFIG,
        backup_dir=backup_dir,
        backup_stem="ocorrencias",
    )
    setores_db = ExcelDatabase(
        db_path=str(data_dir / "setores.xlsx"),
        sheets_config=SECTORS_SHEETS_CONFIG,
        backup_dir=backup_dir,
        backup_stem="setores",
    )
    bot_db = ExcelDatabase(
        db_path=str(data_dir / "bot_config.xlsx"),
        sheets_config=BOT_SHEETS_CONFIG,
        backup_dir=backup_dir,
        backup_stem="bot_config",
    )
    metas_db = ExcelDatabase(
        db_path=str(data_dir / "metas.xlsx"),
        sheets_config=GOALS_SHEETS_CONFIG,
        backup_dir=backup_dir,
        backup_stem="metas",
    )
    for db in (colaboradores_db, ponto_db, tarefas_db, ocorrencias_db, setores_db, bot_db, metas_db):
        db.ensure_database()

    collaborator_repo = CollaboratorRepository(colaboradores_db)
    time_repo = TimeRecordRepository(ponto_db)
    task_repo = TaskRepository(tarefas_db)
    check_repo = TaskCheckRepository(tarefas_db)
    occurrence_repo = OccurrenceRepository(ocorrencias_db)
    sector_repo = SectorRepository(setores_db)
    schedule_repo = WorkScheduleRepository(ponto_db)
    journey_repo = JourneyRepository(ponto_db)
    bot_repo = BotConfigRepository(bot_db)
    goal_repo = GoalRepository(metas_db)
    sector_service = SectorService(sector_repo)
    sector_service.ensure_default_sectors()
    collaborator_service = CollaboratorService(collaborator_repo, sector_service)
    goal_service = GoalService(goal_repo, collaborator_repo)
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
    dummy_bridge = DummyBotBridge()
    bot_service = BotService(
        bot_repo,
        collaborator_service,
        task_service,
        time_clock_service,
        journey_service,
        bridge=dummy_bridge,
    )
    time_clock_service.add_record_listener(bot_service.notify_time_record)
    bot_service.ensure_default_config()

    return {
        "dbs": {
            "colaboradores": colaboradores_db,
            "ponto": ponto_db,
            "tarefas": tarefas_db,
            "ocorrencias": ocorrencias_db,
            "setores": setores_db,
            "bot": bot_db,
            "metas": metas_db,
        },
        "sectors": sector_service,
        "collaborators": collaborator_service,
        "time": time_clock_service,
        "tasks": task_service,
        "occurrences": occurrence_service,
        "dashboard": dashboard_service,
        "journeys": journey_service,
        "monthly_report": monthly_report_service,
        "goals": goal_service,
        "startup_check": startup_check_service,
        "bot": bot_service,
        "bot_bridge": dummy_bridge,
    }
