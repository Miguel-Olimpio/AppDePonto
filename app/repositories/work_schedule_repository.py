"""Compatibilidade para a antiga jornada global.

A estrutura atual usa a aba Jornadas em ponto.xlsx. Este repositorio permanece
apenas para chamadas antigas do TimeClockService e nao cria planilha legada.
"""

from __future__ import annotations

from app.repositories.excel_schema import WORK_SCHEDULE_HEADERS


class WorkScheduleRepository:
    def __init__(self, database=None):
        self.database = database

    def get(self) -> dict:
        return {}

    def save(self, row: dict) -> dict:
        return {header: row.get(header, "") for header in WORK_SCHEDULE_HEADERS}
