"""Repositorio de tarefas/POPs."""

from __future__ import annotations

from app.config.paths import get_tarefas_db_path
from app.config.settings import SHEET_TASKS
from app.models.task import Task
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import TASK_HEADERS, TASKS_SHEETS_CONFIG
from app.utils.formatting import bool_to_excel


class TaskRepository:
    def __init__(self, database: ExcelDatabase | None = None):
        self.database = database or ExcelDatabase(
            db_path=get_tarefas_db_path(),
            sheets_config=TASKS_SHEETS_CONFIG,
            backup_stem="tarefas_pops",
        )

    def list_all(self) -> list[dict]:
        return self.database.read_sheet(SHEET_TASKS)

    def list_active(self) -> list[dict]:
        return [row for row in self.list_all() if bool_to_excel(row.get("active", True))]

    def get_by_id(self, tarefa_id: str) -> dict | None:
        for row in self.list_all():
            if str(row.get("tarefa_id", "")) == str(tarefa_id):
                return row
        return None

    def add(self, task: Task) -> dict:
        return self.database.append_row(SHEET_TASKS, TASK_HEADERS, task.to_dict())

    def update(self, tarefa_id: str, changes: dict) -> dict:
        rows = self.list_all()
        updated: dict | None = None
        for row in rows:
            if str(row.get("tarefa_id", "")) == str(tarefa_id):
                for key, value in changes.items():
                    if key in TASK_HEADERS:
                        row[key] = value
                updated = row
                break
        if updated is None:
            raise KeyError("Tarefa não encontrada.")
        self.database.write_sheet(SHEET_TASKS, TASK_HEADERS, rows)
        return updated
