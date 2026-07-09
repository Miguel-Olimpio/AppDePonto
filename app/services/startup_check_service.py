"""Verificacoes automaticas de pendencias do dia anterior."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.config.settings import OCCURRENCE_POINT_MISSING, OCCURRENCE_TASK_MISSED
from app.services.collaborator_service import CollaboratorService
from app.services.journey_service import JourneyService
from app.services.occurrence_service import OccurrenceService
from app.services.task_service import TaskService
from app.services.time_clock_service import TimeClockService
from app.utils.dates import format_date, now_local, parse_datetime


class StartupCheckService:
    def __init__(
        self,
        collaborator_service: CollaboratorService,
        journey_service: JourneyService,
        time_clock_service: TimeClockService,
        task_service: TaskService,
        occurrence_service: OccurrenceService,
    ):
        self.collaborator_service = collaborator_service
        self.journey_service = journey_service
        self.time_clock_service = time_clock_service
        self.task_service = task_service
        self.occurrence_service = occurrence_service

    def verify_previous_day(self, now: datetime | None = None) -> list[dict]:
        stamp = now or now_local()
        day = stamp.date() - timedelta(days=1)
        created = []
        created.extend(self._verify_missing_points(day, stamp))
        created.extend(self._verify_missed_tasks(day, stamp))
        return created

    def _verify_missing_points(self, day, stamp: datetime) -> list[dict]:
        created = []
        day_text = format_date(day)
        for collaborator in self.collaborator_service.list_active():
            collaborator_id = str(collaborator.get("colaborador_id", ""))
            if not self.journey_service.should_work_on_date(collaborator, day):
                continue
            if self._has_entry_in_work_intervals(collaborator, day):
                continue
            if self.occurrence_service.repository.exists(
                data=day_text,
                tipo=OCCURRENCE_POINT_MISSING,
                colaborador_id=collaborator_id,
            ):
                continue
            created.append(
                self.occurrence_service.create_occurrence(
                    tipo=OCCURRENCE_POINT_MISSING,
                    descricao="Colaborador deveria trabalhar e nao registrou entrada.",
                    day=day_text,
                    when=stamp,
                    colaborador_id=collaborator_id,
                    nome_colaborador=str(collaborator.get("nome", "")),
                )
            )
        return created

    def _verify_missed_tasks(self, day, stamp: datetime) -> list[dict]:
        created = []
        day_text = format_date(day)
        for task in self.task_service.tasks_for_date(day):
            task_id = str(task.get("tarefa_id", ""))
            checks = self.task_service.check_repository.list_for_task_date(task_id, day_text)
            if checks:
                continue
            responsible = self.task_service.responsible_collaborators_for_task(
                task,
                day,
                cutoff_time=str(task.get("horario_limite", "")),
            )
            for collaborator in responsible:
                collaborator_id = str(collaborator.get("colaborador_id", ""))
                if self.occurrence_service.repository.exists(
                    data=day_text,
                    tipo=OCCURRENCE_TASK_MISSED,
                    tarefa_id=task_id,
                    colaborador_id=collaborator_id,
                ):
                    continue
                created.append(
                    self.occurrence_service.create_occurrence(
                        tipo=OCCURRENCE_TASK_MISSED,
                        descricao=f"{task.get('nome', '')} nao foi checada no dia anterior.",
                        day=day_text,
                        when=stamp,
                        colaborador_id=collaborator_id,
                        nome_colaborador=str(collaborator.get("nome", "")),
                        tarefa_id=task_id,
                        nome_tarefa=str(task.get("nome", "")),
                        setor_id=str(task.get("setor_id", "")),
                        nome_setor=str(task.get("nome_setor", "")),
                        horario_limite=str(task.get("horario_limite", "")),
                    )
                )
        return created

    def _has_entry_in_work_intervals(self, collaborator: dict, day) -> bool:
        collaborator_id = str(collaborator.get("colaborador_id", ""))
        intervals = self.journey_service.get_work_intervals_for_date(collaborator, day)
        for start, end in intervals:
            cursor = start.date()
            while cursor <= end.date():
                for row in self.time_clock_service.list_collaborator_records_for_day(collaborator_id, cursor):
                    if str(row.get("tipo_ponto", "")) != "entrada":
                        continue
                    try:
                        record_dt = parse_datetime(row.get("data_hora"))
                    except Exception:
                        continue
                    if start <= record_dt < end:
                        return True
                cursor = cursor + timedelta(days=1)
        return False
