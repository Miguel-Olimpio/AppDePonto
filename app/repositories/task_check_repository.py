"""Repositorio de checagens de tarefas."""

from __future__ import annotations

from app.config.paths import get_tarefas_db_path
from app.config.settings import SHEET_TASK_CHECKS
from app.models.task_check import TaskCheck
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import TASK_CHECK_HEADERS, TASKS_SHEETS_CONFIG


class TaskCheckRepository:
    def __init__(self, database: ExcelDatabase | None = None):
        self.database = database or ExcelDatabase(
            db_path=get_tarefas_db_path(),
            sheets_config=TASKS_SHEETS_CONFIG,
            backup_stem="tarefas_pops",
        )

    def list_all(self) -> list[dict]:
        return self.database.read_sheet(SHEET_TASK_CHECKS)

    def list_by_date(self, data: str) -> list[dict]:
        return [row for row in self.list_all() if str(row.get("data", "")) == str(data)]

    def get_for_task_date(self, tarefa_id: str, data: str) -> dict | None:
        for row in self.list_by_date(data):
            if str(row.get("tarefa_id", "")) == str(tarefa_id):
                return row
        return None

    def list_for_task_date(self, tarefa_id: str, data: str) -> list[dict]:
        return [
            row
            for row in self.list_by_date(data)
            if str(row.get("tarefa_id", "")) == str(tarefa_id)
        ]

    def get_for_task_date_collaborator(self, tarefa_id: str, data: str, colaborador_id: str) -> dict | None:
        for row in self.list_for_task_date(tarefa_id, data):
            if str(row.get("colaborador_id", "")) == str(colaborador_id):
                return row
        return None

    def add(self, check: TaskCheck) -> dict:
        return self.database.append_row(SHEET_TASK_CHECKS, TASK_CHECK_HEADERS, check.to_dict())
