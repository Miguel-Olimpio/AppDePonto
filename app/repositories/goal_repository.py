"""Repositorio de metas mensais."""

from __future__ import annotations

from app.config.paths import get_metas_db_path
from app.config.settings import SHEET_GOALS
from app.models.goal import Goal
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import GOAL_HEADERS, GOALS_SHEETS_CONFIG
from app.utils.formatting import bool_to_excel


class GoalRepository:
    def __init__(self, database: ExcelDatabase | None = None):
        self.database = database or ExcelDatabase(
            db_path=get_metas_db_path(),
            sheets_config=GOALS_SHEETS_CONFIG,
            backup_stem="metas",
        )

    def list_all(self) -> list[dict]:
        return self.database.read_sheet(SHEET_GOALS)

    def list_active(self) -> list[dict]:
        return [row for row in self.list_all() if bool_to_excel(row.get("active", True))]

    def get_by_id(self, meta_id: str) -> dict | None:
        target = str(meta_id or "")
        for row in self.list_all():
            if str(row.get("meta_id", "")) == target:
                return row
        return None

    def add(self, goal: Goal) -> dict:
        return self.database.append_row(SHEET_GOALS, GOAL_HEADERS, goal.to_dict())

    def update(self, meta_id: str, changes: dict) -> dict:
        rows = self.list_all()
        updated = None
        for row in rows:
            if str(row.get("meta_id", "")) != str(meta_id):
                continue
            for key, value in changes.items():
                if key in GOAL_HEADERS:
                    row[key] = value
            updated = row
            break
        if updated is None:
            raise KeyError("Meta nao encontrada.")
        self.database.write_sheet(SHEET_GOALS, GOAL_HEADERS, rows)
        return updated
