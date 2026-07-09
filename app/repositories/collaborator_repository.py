"""Repositorio de colaboradores."""

from __future__ import annotations

from app.config.settings import COLLABORATOR_STATUS_ACTIVE, SHEET_COLLABORATORS
from app.models.collaborator import Collaborator
from app.config.paths import get_colaboradores_db_path
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import COLLABORATOR_HEADERS, COLLABORATORS_SHEETS_CONFIG


class CollaboratorRepository:
    def __init__(self, database: ExcelDatabase | None = None):
        self.database = database or ExcelDatabase(
            db_path=get_colaboradores_db_path(),
            sheets_config=COLLABORATORS_SHEETS_CONFIG,
            backup_stem="colaboradores",
        )

    def list_all(self) -> list[dict]:
        return self.database.read_sheet(SHEET_COLLABORATORS)

    def list_active(self) -> list[dict]:
        return [row for row in self.list_all() if str(row.get("status", "")).lower() == COLLABORATOR_STATUS_ACTIVE]

    def get_by_id(self, colaborador_id: str) -> dict | None:
        for row in self.list_all():
            if str(row.get("colaborador_id", "")) == str(colaborador_id):
                return row
        return None

    def add(self, collaborator: Collaborator) -> dict:
        return self.database.append_row(SHEET_COLLABORATORS, COLLABORATOR_HEADERS, collaborator.to_dict())

    def update(self, colaborador_id: str, changes: dict) -> dict:
        rows = self.list_all()
        updated: dict | None = None
        for row in rows:
            if str(row.get("colaborador_id", "")) == str(colaborador_id):
                for key, value in changes.items():
                    if key in COLLABORATOR_HEADERS:
                        row[key] = value
                updated = row
                break
        if updated is None:
            raise KeyError("Colaborador não encontrado.")
        self.database.write_sheet(SHEET_COLLABORATORS, COLLABORATOR_HEADERS, rows)
        return updated
