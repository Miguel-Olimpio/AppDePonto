"""Repositorio de registros de ponto."""

from __future__ import annotations

from app.config.paths import get_ponto_db_path
from app.config.settings import SHEET_TIME_RECORDS
from app.models.time_record import TimeRecord
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import POINT_SHEETS_CONFIG, TIME_RECORD_HEADERS


class TimeRecordRepository:
    def __init__(self, database: ExcelDatabase | None = None):
        self.database = database or ExcelDatabase(
            db_path=get_ponto_db_path(),
            sheets_config=POINT_SHEETS_CONFIG,
            backup_stem="ponto",
        )

    def list_all(self) -> list[dict]:
        return self.database.read_sheet(SHEET_TIME_RECORDS)

    def list_by_date(self, data: str) -> list[dict]:
        return [row for row in self.list_all() if str(row.get("data", "")) == str(data)]

    def list_by_collaborator(self, colaborador_id: str) -> list[dict]:
        return [row for row in self.list_all() if str(row.get("colaborador_id", "")) == str(colaborador_id)]

    def add(self, record: TimeRecord) -> dict:
        return self.database.append_row(SHEET_TIME_RECORDS, TIME_RECORD_HEADERS, record.to_dict())
