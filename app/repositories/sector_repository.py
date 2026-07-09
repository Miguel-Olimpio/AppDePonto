"""Repositorio de setores."""

from __future__ import annotations

from app.config.paths import get_setores_db_path
from app.config.settings import SHEET_SECTORS
from app.models.sector import Sector
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import SECTOR_HEADERS, SECTORS_SHEETS_CONFIG
from app.utils.formatting import bool_to_excel, normalize_key


class SectorRepository:
    def __init__(self, database: ExcelDatabase | None = None):
        self.database = database or ExcelDatabase(
            db_path=get_setores_db_path(),
            sheets_config=SECTORS_SHEETS_CONFIG,
            backup_stem="setores",
        )

    def list_all(self) -> list[dict]:
        return self.database.read_sheet(SHEET_SECTORS)

    def list_active(self) -> list[dict]:
        return [row for row in self.list_all() if bool_to_excel(row.get("active", True))]

    def get_by_id(self, setor_id: str) -> dict | None:
        target = str(setor_id or "")
        for row in self.list_all():
            if str(row.get("setor_id", "")) == target:
                return row
        return None

    def get_by_name(self, nome: str, only_active: bool = False) -> dict | None:
        target = normalize_key(nome)
        rows = self.list_active() if only_active else self.list_all()
        for row in rows:
            if normalize_key(row.get("nome", "")) == target:
                return row
        return None

    def add(self, sector: Sector) -> dict:
        return self.database.append_row(SHEET_SECTORS, SECTOR_HEADERS, sector.to_dict())

    def update(self, setor_id: str, changes: dict) -> dict:
        rows = self.list_all()
        updated = None
        for row in rows:
            if str(row.get("setor_id", "")) == str(setor_id):
                for key, value in changes.items():
                    if key in SECTOR_HEADERS:
                        row[key] = value
                updated = row
                break
        if updated is None:
            raise KeyError("Setor n?o encontrado.")
        self.database.write_sheet(SHEET_SECTORS, SECTOR_HEADERS, rows)
        return updated
