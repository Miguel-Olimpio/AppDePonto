"""Repositorio de ocorrencias."""

from __future__ import annotations

from app.config.paths import get_ocorrencias_db_path
from app.config.settings import SHEET_OCCURRENCES
from app.models.occurrence import Occurrence
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import OCCURRENCE_HEADERS, OCCURRENCES_SHEETS_CONFIG


class OccurrenceRepository:
    def __init__(self, database: ExcelDatabase | None = None):
        self.database = database or ExcelDatabase(
            db_path=get_ocorrencias_db_path(),
            sheets_config=OCCURRENCES_SHEETS_CONFIG,
            backup_stem="ocorrencias",
        )

    def list_all(self) -> list[dict]:
        return self.database.read_sheet(SHEET_OCCURRENCES)

    def list_recent(self, limit: int = 20) -> list[dict]:
        return list(reversed(self.list_all()))[:limit]

    def get_by_id(self, occurrence_id: str) -> dict | None:
        target = str(occurrence_id)
        for row in self.list_all():
            if str(row.get("ocorrencia_id", "")) == target:
                return row
        return None

    def add(self, occurrence: Occurrence) -> dict:
        return self.database.append_row(SHEET_OCCURRENCES, OCCURRENCE_HEADERS, occurrence.to_dict())

    def update(self, occurrence_id: str, changes: dict) -> dict:
        rows = self.list_all()
        target = str(occurrence_id)
        updated: dict | None = None
        for idx, row in enumerate(rows):
            if str(row.get("ocorrencia_id", "")) != target:
                continue
            merged = dict(row)
            for key, value in changes.items():
                if key in OCCURRENCE_HEADERS:
                    merged[key] = value
            rows[idx] = merged
            updated = merged
            break
        if updated is None:
            raise KeyError("Ocorrencia nao encontrada.")
        self.database.write_sheet(SHEET_OCCURRENCES, OCCURRENCE_HEADERS, rows)
        return updated

    def exists(
        self,
        *,
        data: str,
        tipo: str,
        tarefa_id: str = "",
        colaborador_id: str = "",
    ) -> bool:
        target_data = str(data or "")
        target_type = str(tipo or "")
        target_task = str(tarefa_id or "")
        target_collaborator = str(colaborador_id or "")
        for row in self.list_all():
            if str(row.get("data") or "") != target_data:
                continue
            if str(row.get("tipo") or "") != target_type:
                continue
            if str(row.get("tarefa_id") or "") != target_task:
                continue
            if str(row.get("colaborador_id") or "") != target_collaborator:
                continue
            return True
        return False
