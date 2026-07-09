"""Servicos de tarefas/POPs e checagens."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from app.config.settings import (
    OCCURRENCE_TASK_LATE,
    OCCURRENCE_TASK_MISSED,
    TASK_STATUS_DONE,
    TASK_STATUS_IN_PROGRESS,
    TASK_STATUS_LATE,
    TASK_STATUS_MISSED,
    TASK_STATUS_PARTIAL,
    TASK_STATUS_PENDING,
    TASK_STATUS_TOLERANCE,
    WEEKDAY_NAMES,
)
from app.models.task import Task
from app.models.task_check import TaskCheck
from app.repositories.collaborator_repository import CollaboratorRepository
from app.repositories.occurrence_repository import OccurrenceRepository
from app.repositories.task_check_repository import TaskCheckRepository
from app.repositories.task_repository import TaskRepository
from app.services.journey_service import JourneyService
from app.services.occurrence_service import OccurrenceService
from app.services.sector_service import SectorService
from app.services.time_clock_service import TimeClockService
from app.utils.dates import combine_date_time, format_date, format_datetime, format_time, now_local, parse_date, parse_time, weekday_name
from app.utils.formatting import bool_to_excel, clean_text, normalize_key
from app.utils.validators import require_text, validate_non_negative_int, validate_time_text

GENERAL_SECTOR_KEYS = {"todos", "geral", "all"}
GENERAL_SECTOR_LABEL = "Todos"


class TaskService:
    def __init__(
        self,
        task_repository: TaskRepository | None = None,
        check_repository: TaskCheckRepository | None = None,
        collaborator_repository: CollaboratorRepository | None = None,
        occurrence_repository: OccurrenceRepository | None = None,
        time_clock_service: TimeClockService | None = None,
        occurrence_service: OccurrenceService | None = None,
        journey_service: JourneyService | None = None,
        sector_service: SectorService | None = None,
        **_ignored,
    ):
        self.task_repository = task_repository or TaskRepository()
        self.check_repository = check_repository or TaskCheckRepository()
        self.collaborator_repository = collaborator_repository or CollaboratorRepository()
        self.occurrence_repository = occurrence_repository or OccurrenceRepository()
        self.time_clock_service = time_clock_service or TimeClockService(
            collaborator_repository=self.collaborator_repository
        )
        self.occurrence_service = occurrence_service or OccurrenceService(self.occurrence_repository)
        self.journey_service = journey_service or JourneyService()
        self.sector_service = sector_service or SectorService()

    def create_task(
        self,
        nome: str,
        descricao: str = "",
        horario_inicio: str = "",
        horario_limite: str = "",
        tolerancia_minutos=0,
        dias_semana: str = "todos",
        setor_id: str = "",
        nome_setor: str = "",
        observacoes: str = "",
        **_ignored,
    ) -> dict:
        start = validate_time_text(horario_inicio, "Horario de inicio")
        limit = validate_time_text(horario_limite, "Horario limite")
        tolerance = validate_non_negative_int(tolerancia_minutos, "Tolerancia da tarefa")
        if parse_time(start) >= parse_time(limit):
            raise ValueError("Horario de inicio deve ser menor que o horario limite.")
        sector = self.sector_service.resolve_sector(setor_id=setor_id, nome_setor=nome_setor)
        task = Task(
            tarefa_id=uuid.uuid4().hex[:12],
            nome=require_text(nome, "Nome da tarefa"),
            descricao=clean_text(descricao),
            horario_inicio=start,
            horario_limite=limit,
            tolerancia_minutos=tolerance,
            dias_semana=clean_text(dias_semana) or "todos",
            setor_id=sector["setor_id"],
            nome_setor=sector["nome_setor"],
            active=True,
            data_cadastro=format_date(),
            data_atualizacao=format_datetime(),
            observacoes=clean_text(observacoes),
        )
        return self.task_repository.add(task)

    def update_task(self, tarefa_id: str, **changes) -> dict:
        if "setor_label" in changes:
            changes["nome_setor"] = changes.pop("setor_label")
        if "setor_id" in changes or "nome_setor" in changes:
            sector = self.sector_service.resolve_sector(
                setor_id=str(changes.get("setor_id", "")),
                nome_setor=str(changes.get("nome_setor", "")),
            )
            changes["setor_id"] = sector["setor_id"]
            changes["nome_setor"] = sector["nome_setor"]
        if "nome" in changes:
            changes["nome"] = require_text(changes["nome"], "Nome da tarefa")
        for key in ("horario_inicio", "horario_limite"):
            if key in changes:
                changes[key] = validate_time_text(changes[key], key.replace("_", " ").title())
        if "tolerancia_minutos" in changes:
            changes["tolerancia_minutos"] = validate_non_negative_int(
                changes["tolerancia_minutos"],
                "Tolerancia da tarefa",
            )

        current = self.task_repository.get_by_id(tarefa_id) or {}
        start = changes.get("horario_inicio", current.get("horario_inicio", ""))
        limit = changes.get("horario_limite", current.get("horario_limite", ""))
        if start and limit and parse_time(start) >= parse_time(limit):
            raise ValueError("Horario de inicio deve ser menor que o horario limite.")
        changes["data_atualizacao"] = format_datetime()
        return self.task_repository.update(tarefa_id, changes)

    def set_active(self, tarefa_id: str, active: bool) -> dict:
        return self.task_repository.update(tarefa_id, {"active": bool(active), "data_atualizacao": format_datetime()})

    def list_tasks(self, only_active: bool = False) -> list[dict]:
        return self.task_repository.list_active() if only_active else self.task_repository.list_all()

    def tasks_for_date(self, day: date | str | None = None) -> list[dict]:
        parsed_day = parse_date(day) if day is not None else date.today()
        return [task for task in self.task_repository.list_active() if self._task_runs_on_day(task, parsed_day)]

    def tasks_for_collaborator(self, collaborator: dict | None, day: date | str | None = None) -> list[dict]:
        if not collaborator:
            return []
        return [task for task in self.tasks_for_date(day) if self._collaborator_matches_task_sector(task, collaborator)]

    def collaborators_for_task_check(
        self,
        tarefa_id: str,
        day: date | str | None = None,
        now: datetime | None = None,
    ) -> list[dict]:
        task = self.task_repository.get_by_id(tarefa_id)
        if not task:
            return []
        stamp = now or now_local()
        parsed_day = parse_date(day) if day is not None else stamp.date()
        cutoff = format_time(stamp) if parsed_day == stamp.date() else str(task.get("horario_limite", ""))
        return self.responsible_collaborators_for_task(task, parsed_day, cutoff_time=cutoff)

    def responsible_collaborators_for_task(
        self,
        task: dict,
        day: date | str,
        cutoff_time: str | None = None,
    ) -> list[dict]:
        parsed_day = parse_date(day)
        present = self.time_clock_service.present_collaborators(parsed_day, cutoff_time or str(task.get("horario_limite", "")))
        expected = self.expected_collaborators_for_task(task, parsed_day)
        return self._filter_collaborators_by_task_sector(task, self._unique_collaborators(expected + present))

    def expected_collaborators_for_task(self, task: dict, day: date | str) -> list[dict]:
        parsed_day = parse_date(day)
        task_start = combine_date_time(parsed_day, task.get("horario_inicio", "00:00"))
        task_end = combine_date_time(parsed_day, task.get("horario_limite", "00:00"))
        expected: list[dict] = []
        for collaborator in self.collaborator_repository.list_active():
            if not self._collaborator_matches_task_sector(task, collaborator):
                continue
            intervals = self.journey_service.get_work_intervals_for_date(collaborator, parsed_day)
            if any(start < task_end and end > task_start for start, end in intervals):
                expected.append(collaborator)
        return sorted(expected, key=lambda row: str(row.get("nome", "")).lower())

    @staticmethod
    def _unique_collaborators(rows: list[dict]) -> list[dict]:
        seen: set[str] = set()
        unique: list[dict] = []
        for row in rows:
            collaborator_id = str(row.get("colaborador_id", ""))
            if collaborator_id in seen:
                continue
            seen.add(collaborator_id)
            unique.append(row)
        return unique

    def mark_done(
        self,
        tarefa_id: str,
        colaborador_id: str,
        when: datetime | None = None,
        observacoes: str = "",
    ) -> dict:
        stamp = when or now_local()
        date_str = format_date(stamp)
        existing = self.check_repository.get_for_task_date_collaborator(tarefa_id, date_str, colaborador_id)
        if existing:
            return existing

        task = self.task_repository.get_by_id(tarefa_id)
        if not task:
            raise KeyError("Tarefa nao encontrada.")
        collaborator = self.collaborator_repository.get_by_id(colaborador_id)
        if not collaborator:
            raise KeyError("Colaborador nao encontrado.")
        if not self._collaborator_matches_task_sector(task, collaborator):
            raise ValueError("Colaborador nao pertence ao setor responsavel da tarefa.")

        deadline_dt = self._task_deadline(task, date_str)
        status = TASK_STATUS_DONE if stamp <= deadline_dt else TASK_STATUS_LATE
        check = TaskCheck(
            check_id=uuid.uuid4().hex[:12],
            tarefa_id=str(tarefa_id),
            nome_tarefa=str(task.get("nome", "")),
            colaborador_id=str(colaborador_id),
            nome_colaborador=str(collaborator.get("nome", "")),
            data=date_str,
            hora_check=format_time(stamp),
            status=status,
            observacoes=clean_text(observacoes),
        )
        saved = self.check_repository.add(check)

        if status == TASK_STATUS_LATE:
            self._create_late_occurrence(task, collaborator, stamp)
        return saved

    def mark_done_for_collaborators(
        self,
        tarefa_id: str,
        colaborador_ids: list[str],
        when: datetime | None = None,
        observacoes: str = "",
    ) -> list[dict]:
        return [
            self.mark_done(tarefa_id, colaborador_id, when=when, observacoes=observacoes)
            for colaborador_id in colaborador_ids
        ]

    def verify_pending_tasks(self, day: date | str | None = None, now: datetime | None = None) -> list[dict]:
        stamp = now or now_local()
        parsed_day = parse_date(day) if day is not None else stamp.date()
        date_str = format_date(parsed_day)
        created: list[dict] = []

        for task in self.tasks_for_date(parsed_day):
            tarefa_id = str(task.get("tarefa_id", ""))
            limit = str(task.get("horario_limite", "00:00"))
            if self._task_deadline(task, parsed_day) >= stamp:
                continue

            targets = self.responsible_collaborators_for_task(task, parsed_day, cutoff_time=limit)
            for collaborator in targets:
                colaborador_id = str(collaborator.get("colaborador_id", ""))
                if self.check_repository.get_for_task_date_collaborator(tarefa_id, date_str, colaborador_id):
                    continue
                if self.occurrence_repository.exists(
                    data=date_str,
                    tipo=OCCURRENCE_TASK_MISSED,
                    tarefa_id=tarefa_id,
                    colaborador_id=colaborador_id,
                ):
                    continue
                created.append(
                    self.occurrence_service.create_occurrence(
                        tipo=OCCURRENCE_TASK_MISSED,
                        descricao=f"{task.get('nome', '')} nao foi cumprida dentro do horario.",
                        day=date_str,
                        when=stamp,
                        colaborador_id=colaborador_id,
                        nome_colaborador=str(collaborator.get("nome", "")),
                        tarefa_id=tarefa_id,
                        nome_tarefa=str(task.get("nome", "")),
                        setor_id=str(task.get("setor_id", "")),
                        nome_setor=self._task_sector_name(task),
                        horario_limite=limit,
                    )
                )
        return created

    def checks_for_date(self, day: date | str | None = None) -> list[dict]:
        return self.check_repository.list_by_date(format_date(day))

    def status_for_task(
        self,
        tarefa_id: str,
        day: date | str | None = None,
        now: datetime | None = None,
    ) -> str:
        task = self.task_repository.get_by_id(tarefa_id)
        if not task:
            return TASK_STATUS_PENDING

        stamp = now or now_local()
        parsed_day = parse_date(day) if day is not None else stamp.date()
        date_str = format_date(parsed_day)
        checks = self.check_repository.list_for_task_date(tarefa_id, date_str)
        responsible = self.responsible_collaborators_for_task(task, parsed_day, cutoff_time=str(task.get("horario_limite", "")))
        required_ids = {str(row.get("colaborador_id", "")) for row in responsible}
        checked_ids = {str(row.get("colaborador_id", "")) for row in checks}

        if required_ids:
            if required_ids.issubset(checked_ids):
                return TASK_STATUS_LATE if any(row.get("status") == TASK_STATUS_LATE for row in checks) else TASK_STATUS_DONE
            if checked_ids:
                return TASK_STATUS_PARTIAL
        elif checks:
            return str(checks[0].get("status", TASK_STATUS_DONE))

        if self._task_deadline(task, parsed_day) < stamp:
            return TASK_STATUS_MISSED
        return TASK_STATUS_PENDING

    def task_display_state(
        self,
        task: dict,
        day: date | str | None = None,
        now: datetime | None = None,
    ) -> dict:
        stamp = now or now_local()
        parsed_day = parse_date(day) if day is not None else stamp.date()
        status = self.status_for_task(str(task.get("tarefa_id", "")), parsed_day, stamp)
        start_dt = combine_date_time(parsed_day, task.get("horario_inicio", "00:00"))
        limit_dt = combine_date_time(parsed_day, task.get("horario_limite", "00:00"))
        deadline_dt = self._task_deadline(task, parsed_day)

        if status == TASK_STATUS_DONE:
            return {"status": status, "tag": "done"}
        if status in {TASK_STATUS_LATE, TASK_STATUS_MISSED}:
            return {"status": status, "tag": "late"}
        if status == TASK_STATUS_PARTIAL:
            return {"status": status, "tag": "running"}
        if start_dt <= stamp <= limit_dt:
            return {"status": TASK_STATUS_IN_PROGRESS, "tag": "running"}
        if limit_dt < stamp <= deadline_dt:
            return {"status": TASK_STATUS_TOLERANCE, "tag": "running"}
        if stamp > deadline_dt:
            return {"status": TASK_STATUS_MISSED, "tag": "late"}
        return {"status": TASK_STATUS_PENDING, "tag": "pending"}

    def dashboard_summary(self, day: date | str | None = None) -> dict:
        date_str = format_date(day)
        tasks_today = self.tasks_for_date(date_str)
        task_statuses = [self.status_for_task(str(task.get("tarefa_id", "")), date_str) for task in tasks_today]
        occurrences = self.occurrence_repository.list_all()
        return {
            "presentes": len(self.time_clock_service.present_collaborators(date_str)),
            "tarefas_dia": len(tasks_today),
            "tarefas_cumpridas": sum(1 for status in task_statuses if status == TASK_STATUS_DONE),
            "tarefas_atrasadas": sum(1 for status in task_statuses if status == TASK_STATUS_LATE),
            "tarefas_nao_cumpridas": sum(
                1
                for row in occurrences
                if row.get("data") == date_str and row.get("tipo") == OCCURRENCE_TASK_MISSED
            ),
        }

    def _filter_collaborators_by_task_sector(self, task: dict, collaborators: list[dict]) -> list[dict]:
        return [row for row in collaborators if self._collaborator_matches_task_sector(task, row)]

    def _collaborator_matches_task_sector(self, task: dict, collaborator: dict) -> bool:
        if self._task_is_general_sector(task):
            return True
        task_sector_id = clean_text(task.get("setor_id"))
        collaborator_sector_id = clean_text(collaborator.get("setor_id"))
        if task_sector_id and collaborator_sector_id and task_sector_id == collaborator_sector_id:
            return True

        task_names = self._sector_match_keys(task_sector_id, self._task_sector_name(task))
        collaborator_names = self._sector_match_keys(collaborator_sector_id, collaborator.get("nome_setor", ""))
        return bool(task_names and collaborator_names and task_names.intersection(collaborator_names))

    def _task_is_general_sector(self, task: dict) -> bool:
        task_sector_id = clean_text(task.get("setor_id"))
        return bool(self._sector_match_keys(task_sector_id, self._task_sector_name(task)).intersection(GENERAL_SECTOR_KEYS))

    @staticmethod
    def _task_sector_name(task: dict) -> str:
        return clean_text(task.get("nome_setor"))

    def _sector_match_keys(self, setor_id: str = "", nome_setor: object = "") -> set[str]:
        name_key = normalize_key(nome_setor)
        if name_key:
            return {name_key}
        if clean_text(setor_id):
            sector = self.sector_service.get(clean_text(setor_id))
            sector_key = normalize_key((sector or {}).get("nome", ""))
            if sector_key:
                return {sector_key}
        return set()

    @staticmethod
    def _task_runs_on_day(task: dict, day: date) -> bool:
        raw = normalize_key(task.get("dias_semana", "todos"))
        if not bool_to_excel(task.get("active", True)):
            return False
        if not raw or raw == "todos":
            return True
        parts = {normalize_key(part) for part in raw.replace(";", ",").split(",") if clean_text(part)}
        current = weekday_name(day)
        aliases = {current, current[:3], str(day.weekday() + 1), WEEKDAY_NAMES[day.weekday()]}
        return bool(parts & aliases)

    def _task_deadline(self, task: dict, day: date | str) -> datetime:
        limit_dt = combine_date_time(day, task.get("horario_limite", "00:00"))
        tolerance = validate_non_negative_int(task.get("tolerancia_minutos", 0), "Tolerancia da tarefa")
        return limit_dt + timedelta(minutes=tolerance)

    def _create_late_occurrence(self, task: dict, collaborator: dict, stamp: datetime) -> None:
        self.occurrence_service.create_occurrence(
            tipo=OCCURRENCE_TASK_LATE,
            descricao=f"{task.get('nome', '')} foi cumprida apos o horario limite.",
            day=format_date(stamp),
            when=stamp,
            colaborador_id=str(collaborator.get("colaborador_id", "")),
            nome_colaborador=str(collaborator.get("nome", "")),
            tarefa_id=str(task.get("tarefa_id", "")),
            nome_tarefa=str(task.get("nome", "")),
            setor_id=str(task.get("setor_id", "")),
            nome_setor=self._task_sector_name(task),
            horario_limite=str(task.get("horario_limite", "")),
        )
