"""Indicadores gerenciais para o Dashboard."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Any

from app.config.settings import (
    OCCURRENCE_BREAK_OUT_OF_TIME,
    OCCURRENCE_EXIT_OUT_OF_TIME,
    OCCURRENCE_POINT_LATE,
    OCCURRENCE_RETURN_OUT_OF_TIME,
    OCCURRENCE_TASK_LATE,
    OCCURRENCE_TASK_MISSED,
    TASK_STATUS_DONE,
    TASK_STATUS_LATE,
    TASK_STATUS_MISSED,
    TASK_STATUS_PARTIAL,
)
from app.services.occurrence_service import OccurrenceService
from app.services.task_service import TaskService
from app.services.time_clock_service import TimeClockService
from app.utils.dates import format_date, parse_date
from app.utils.formatting import clean_text

POINT_DELAY_TYPES = {
    OCCURRENCE_POINT_LATE,
    OCCURRENCE_BREAK_OUT_OF_TIME,
    OCCURRENCE_RETURN_OUT_OF_TIME,
    OCCURRENCE_EXIT_OUT_OF_TIME,
}
TASK_FAILURE_TYPES = {OCCURRENCE_TASK_LATE, OCCURRENCE_TASK_MISSED}


class DashboardService:
    def __init__(
        self,
        time_clock_service: TimeClockService,
        task_service: TaskService,
        occurrence_service: OccurrenceService,
    ):
        self.time_clock_service = time_clock_service
        self.task_service = task_service
        self.occurrence_service = occurrence_service

    def normalize_period(self, start: date | str | None = None, end: date | str | None = None) -> tuple[str, str]:
        start_date = parse_date(start) if start is not None else date.today()
        end_date = parse_date(end) if end is not None else start_date
        if start_date > end_date:
            raise ValueError("Data inicial deve ser menor ou igual à data final.")
        return format_date(start_date), format_date(end_date)

    def summary_by_period(self, start: date | str | None = None, end: date | str | None = None) -> dict[str, Any]:
        start_text, end_text = self.normalize_period(start, end)
        reference_day = end_text
        occurrences = self.occurrences_in_period(start_text, end_text)
        tasks_today = self.task_service.tasks_for_date(reference_day)
        task_statuses = [
            self.task_service.status_for_task(str(task.get("tarefa_id", "")), reference_day)
            for task in tasks_today
        ]
        checks = self._checks_in_period(start_text, end_text)
        points = self._points_in_period(start_text, end_text)
        point_delay_count = sum(1 for row in occurrences if clean_text(row.get("tipo")) in POINT_DELAY_TYPES)
        task_failure_count = sum(1 for row in occurrences if clean_text(row.get("tipo")) in TASK_FAILURE_TYPES)

        return {
            "data_inicio": start_text,
            "data_fim": end_text,
            "presentes": len(self.time_clock_service.present_collaborators(reference_day)),
            "tarefas_dia": len(tasks_today),
            "tarefas_cumpridas": sum(1 for status in task_statuses if status == TASK_STATUS_DONE),
            "tarefas_parciais": sum(1 for status in task_statuses if status == TASK_STATUS_PARTIAL),
            "tarefas_atrasadas": sum(1 for status in task_statuses if status == TASK_STATUS_LATE),
            "tarefas_nao_cumpridas": sum(1 for status in task_statuses if status == TASK_STATUS_MISSED) + task_failure_count,
            "ocorrencias_periodo": len(occurrences),
            "atrasos_periodo": point_delay_count,
            "checks_periodo": len(checks),
            "pontos_periodo": len(points),
        }

    def occurrences_in_period(self, start: date | str | None = None, end: date | str | None = None) -> list[dict]:
        start_text, end_text = self.normalize_period(start, end)
        start_date = parse_date(start_text)
        end_date = parse_date(end_text)
        rows = []
        for row in self.occurrence_service.list_all():
            try:
                row_date = parse_date(row.get("data"))
            except ValueError:
                continue
            if start_date <= row_date <= end_date:
                rows.append(row)
        return rows

    def occurrences_by_type(self, start: date | str | None = None, end: date | str | None = None) -> list[dict]:
        counter: Counter[str] = Counter()
        for row in self.occurrences_in_period(start, end):
            key = clean_text(row.get("tipo")) or "Sem tipo"
            counter[key] += 1
        return [{"tipo": key, "quantidade": value} for key, value in counter.most_common()]

    def failed_tasks_ranking(self, start: date | str | None = None, end: date | str | None = None, limit: int = 5) -> list[dict]:
        counter: Counter[str] = Counter()
        for row in self.occurrences_in_period(start, end):
            if clean_text(row.get("tipo")) not in TASK_FAILURE_TYPES:
                continue
            key = clean_text(row.get("nome_tarefa")) or "Sem tarefa"
            counter[key] += 1
        return [{"nome_tarefa": key, "falhas": value} for key, value in counter.most_common(limit)]

    def late_collaborators_ranking(self, start: date | str | None = None, end: date | str | None = None, limit: int = 5) -> list[dict]:
        counter: Counter[str] = Counter()
        for row in self.occurrences_in_period(start, end):
            if clean_text(row.get("tipo")) not in POINT_DELAY_TYPES:
                continue
            key = clean_text(row.get("nome_colaborador")) or "Sem colaborador"
            counter[key] += 1
        return [{"nome_colaborador": key, "atrasos": value} for key, value in counter.most_common(limit)]

    def critical_tasks(self, day: date | str | None = None, limit: int = 8) -> list[dict]:
        reference_day = format_date(day)
        rows = []
        for task in self.task_service.tasks_for_date(reference_day):
            state = self.task_service.task_display_state(task, reference_day)
            status = clean_text(state.get("status"))
            if status in {TASK_STATUS_DONE}:
                continue
            if state.get("tag") not in {"running", "late"} and status not in {TASK_STATUS_PARTIAL, TASK_STATUS_MISSED, TASK_STATUS_LATE}:
                continue
            rows.append(
                {
                    "nome": task.get("nome", ""),
                    "horario": f"{task.get('horario_inicio', '')} até {task.get('horario_limite', '')}",
                    "status": status,
                    "setor": task.get("nome_setor", ""),
                    "tag": state.get("tag", ""),
                }
            )
        return rows[:limit]

    def recent_occurrences(self, start: date | str | None = None, end: date | str | None = None, limit: int = 8) -> list[dict]:
        return list(reversed(self.occurrences_in_period(start, end)))[:limit]

    def _checks_in_period(self, start: str, end: str) -> list[dict]:
        start_date = parse_date(start)
        end_date = parse_date(end)
        rows = []
        for row in self.task_service.check_repository.list_all():
            try:
                row_date = parse_date(row.get("data"))
            except ValueError:
                continue
            if start_date <= row_date <= end_date:
                rows.append(row)
        return rows

    def _points_in_period(self, start: str, end: str) -> list[dict]:
        start_date = parse_date(start)
        end_date = parse_date(end)
        rows = []
        for row in self.time_clock_service.time_repository.list_all():
            try:
                row_date = parse_date(row.get("data"))
            except ValueError:
                continue
            if start_date <= row_date <= end_date:
                rows.append(row)
        return rows
