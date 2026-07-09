"""Repositorio de jornadas/escalas."""

from __future__ import annotations

from app.config.paths import get_ponto_db_path
from app.config.settings import SHEET_JOURNEYS
from app.models.journey import Journey
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import JOURNEY_HEADERS, POINT_SHEETS_CONFIG
from app.utils.formatting import bool_to_excel


class JourneyRepository:
    def __init__(self, database: ExcelDatabase | None = None):
        self.database = database or ExcelDatabase(
            db_path=get_ponto_db_path(),
            sheets_config=POINT_SHEETS_CONFIG,
            backup_stem="ponto",
        )

    def list_all(self) -> list[dict]:
        return [self._normalize_row(row) for row in self.database.read_sheet(SHEET_JOURNEYS)]

    def list_active(self) -> list[dict]:
        return [row for row in self.list_all() if bool_to_excel(row.get("active", True))]

    def _normalize_row(self, row: dict) -> dict:
        normalized = dict(row)
        normalized["tipo_escala"] = str(normalized.get("tipo_jornada") or normalized.get("tipo_escala") or "")
        return normalized

    def get_by_id(self, jornada_id: str) -> dict | None:
        target = str(jornada_id)
        for row in self.list_all():
            if str(row.get("jornada_id", "")) == target:
                return row
        return None

    def add(self, journey: Journey) -> dict:
        return self.database.append_row(SHEET_JOURNEYS, JOURNEY_HEADERS, journey.to_dict())

    def update(self, jornada_id: str, changes: dict) -> dict:
        rows = self.list_all()
        updated: dict | None = None
        for row in rows:
            if str(row.get("jornada_id", "")) == str(jornada_id):
                for key, value in changes.items():
                    header = "tipo_jornada" if key == "tipo_escala" else key
                    if header in JOURNEY_HEADERS:
                        row[header] = value
                updated = self._normalize_row(row)
                break
        if updated is None:
            raise KeyError("Jornada não encontrada.")
        self.database.write_sheet(SHEET_JOURNEYS, JOURNEY_HEADERS, rows)
        return updated
