"""Agendador testável de lembretes de ponto e tarefas."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Callable

from app.bot.message_templates import (
    pause_confirmation,
    point_entry_confirmation,
    point_reminder,
    return_reminder,
    return_tolerance_reminder,
    task_reminder,
    task_tolerance_reminder,
)
from app.bot.whatsapp_bot import normalize_whatsapp_phone
from app.config.settings import OCCURRENCE_TASK_MISSED
from app.repositories.bot_config_repository import BotConfigRepository
from app.services.collaborator_service import CollaboratorService
from app.services.journey_service import JourneyService
from app.services.task_service import TaskService
from app.services.time_clock_service import TimeClockService
from app.utils.dates import combine_date_time, format_date, format_datetime, format_time, now_local, parse_datetime
from app.utils.formatting import clean_text

Sender = Callable[[str, str], bool]

REMINDER_POINT_ENTRY_CONFIRMED = "ponto_entrada_confirmado"
REMINDER_TASK_START = "tarefa_inicio"
REMINDER_TASK_TOLERANCE = "tarefa_tolerancia"
REMINDER_POINT_ENTRY = "ponto_entrada"
REMINDER_POINT_ENTRY_TOLERANCE = "ponto_entrada_tolerancia"
REMINDER_POINT_BREAK = "ponto_pausa"
REMINDER_POINT_BREAK_CONFIRMED = "pausa_confirmada"
REMINDER_POINT_RETURN = "ponto_retorno"
REMINDER_POINT_RETURN_TOLERANCE = "retorno_tolerancia"
REMINDER_POINT_EXIT = "ponto_saida"

DEFAULT_BOT_CONFIG = {
    "lembretes_tarefas_ativos": "sim",
    "lembretes_ponto_ativos": "sim",
    "minutos_antes_inicio": "0",
    "minutos_antes_tolerancia": "0",
    "intervalo_verificacao_segundos": "60",
    "max_tentativas_envio": "3",
    "intervalo_retry_segundos": "90",
    "limite_envios_por_ciclo": "3",
}


class ReminderScheduler:
    def __init__(
        self,
        repository: BotConfigRepository,
        collaborator_service: CollaboratorService,
        task_service: TaskService,
        time_clock_service: TimeClockService,
        journey_service: JourneyService,
        sender: Sender | None = None,
    ):
        self.repository = repository
        self.collaborator_service = collaborator_service
        self.task_service = task_service
        self.time_clock_service = time_clock_service
        self.journey_service = journey_service
        self.sender = sender or (lambda _phone, _message: False)

    def config(self) -> dict[str, str]:
        config = dict(DEFAULT_BOT_CONFIG)
        config.update(self.repository.get_config())
        return config

    def ensure_default_config(self) -> dict[str, str]:
        current = self.repository.get_config()
        missing = {key: value for key, value in DEFAULT_BOT_CONFIG.items() if key not in current}
        if missing:
            current = self.repository.save_config(missing)
        config = dict(DEFAULT_BOT_CONFIG)
        config.update(current)
        return config

    def run_once(self, now: datetime | None = None) -> list[dict]:
        stamp = now or now_local()
        config = self.config()
        sent: list[dict] = []
        if _is_enabled(config.get("lembretes_tarefas_ativos")):
            sent.extend(self._task_reminders(stamp, config))
        if _is_enabled(config.get("lembretes_ponto_ativos")):
            sent.extend(self._point_reminders(stamp, config))
        return sent

    def queue_time_record_confirmation(self, record: dict, collaborator: dict, *, bot_connected: bool = True) -> dict | None:
        record_type = clean_text(record.get("tipo_ponto"))
        if record_type not in {"entrada", "pausa"}:
            return None
        day_text = clean_text(record.get("data")) or format_date()
        point_id = clean_text(record.get("ponto_id"))
        collaborator_id = clean_text(collaborator.get("colaborador_id"))
        reminder_type = REMINDER_POINT_ENTRY_CONFIRMED if record_type == "entrada" else REMINDER_POINT_BREAK_CONFIRMED
        if self._reminder_exists(day_text, reminder_type, collaborator_id, ponto_id=point_id):
            return None
        if not bot_connected:
            return self._add_skipped_reminder(
                collaborator=collaborator,
                reminder_type=reminder_type,
                day_text=day_text,
                point_record=record,
                status="bot desconectado",
                observations="Bot desconectado; confirmação de ponto não enviada.",
            )
        if record_type == "entrada":
            message = point_entry_confirmation(str(collaborator.get("nome", "")), str(record.get("hora", "")))
        else:
            interval_minutes = self._journey_interval_minutes(collaborator)
            if interval_minutes <= 0:
                return None
            pause_dt = parse_datetime(record.get("data_hora"))
            return_dt = pause_dt + timedelta(minutes=interval_minutes)
            message = pause_confirmation(str(collaborator.get("nome", "")), str(record.get("hora", "")), format_time(return_dt))
        return self._send_once(
            collaborator=collaborator,
            reminder_type=reminder_type,
            message=message,
            day=day_text,
            point_record=record,
        )

    def _task_reminders(self, stamp: datetime, config: dict[str, str]) -> list[dict]:
        day = stamp.date()
        lead = timedelta(minutes=_to_int(config.get("minutos_antes_inicio"), 0))
        sent: list[dict] = []
        for task in self.task_service.tasks_for_date(day):
            start_dt = combine_date_time(day, task.get("horario_inicio", "00:00"))
            limit_dt = combine_date_time(day, task.get("horario_limite", "00:00"))
            tolerance = _to_int(task.get("tolerancia_minutos"), 0)
            deadline_dt = limit_dt + timedelta(minutes=tolerance)
            collaborators = self._entered_responsible_collaborators_for_task(task, day, stamp)
            if start_dt - lead <= stamp <= limit_dt:
                for collaborator in collaborators:
                    if self._task_already_checked(task, collaborator, day) or self._task_missed_occurrence_exists(task, collaborator, day):
                        continue
                    sent.append(
                        self._send_once(
                            collaborator=collaborator,
                            reminder_type=REMINDER_TASK_START,
                            message=task_reminder(
                                str(collaborator.get("nome", "")),
                                self._task_message_name(task),
                                str(task.get("horario_inicio", "")),
                                str(task.get("horario_limite", "")),
                            ),
                            day=day,
                            task=task,
                        )
                    )
            if limit_dt <= stamp <= deadline_dt:
                for collaborator in collaborators:
                    if self._task_already_checked(task, collaborator, day) or self._task_missed_occurrence_exists(task, collaborator, day):
                        continue
                    sent.append(
                        self._send_once(
                            collaborator=collaborator,
                            reminder_type=REMINDER_TASK_TOLERANCE,
                            message=task_tolerance_reminder(str(collaborator.get("nome", "")), self._task_message_name(task), tolerance),
                            day=day,
                            task=task,
                        )
                    )
        return [row for row in sent if row]

    def _point_reminders(self, stamp: datetime, config: dict[str, str]) -> list[dict]:
        day = stamp.date()
        lead = timedelta(minutes=_to_int(config.get("minutos_antes_inicio"), 0))
        tolerance_lead = timedelta(minutes=_to_int(config.get("minutos_antes_tolerancia"), 0))
        sent: list[dict] = []
        for collaborator in self.collaborator_service.list_active():
            intervals = self.journey_service.get_work_intervals_for_date(collaborator, day)
            if not intervals:
                continue
            records = self.time_clock_service.list_collaborator_records_for_day(str(collaborator.get("colaborador_id", "")), day)
            for start_dt, end_dt in intervals:
                tolerance = self._journey_tolerance(collaborator)
                if start_dt - max(lead, tolerance_lead) <= stamp <= start_dt + timedelta(minutes=tolerance):
                    if not self._has_record_between(records, "entrada", start_dt, end_dt):
                        reminder_type = REMINDER_POINT_ENTRY_TOLERANCE if stamp >= start_dt else REMINDER_POINT_ENTRY
                        sent.append(
                            self._send_once(
                                collaborator=collaborator,
                                reminder_type=reminder_type,
                                message=point_reminder(str(collaborator.get("nome", "")), "entrada"),
                                day=day,
                            )
                        )
                pause_dt = self._suggested_pause_datetime(collaborator, start_dt, end_dt)
                if pause_dt and pause_dt - lead <= stamp <= pause_dt + timedelta(minutes=tolerance):
                    if self._has_record_between(records, "entrada", start_dt, end_dt) and not self._has_record_between(records, "pausa", start_dt, end_dt):
                        sent.append(
                            self._send_once(
                                collaborator=collaborator,
                                reminder_type=REMINDER_POINT_BREAK,
                                message=point_reminder(str(collaborator.get("nome", "")), "pausa"),
                                day=day,
                            )
                        )
                if end_dt - lead <= stamp <= end_dt + timedelta(minutes=tolerance):
                    if self._has_record_between(records, "entrada", start_dt, end_dt) and not self._has_record_between(records, "saída", start_dt, end_dt):
                        sent.append(
                            self._send_once(
                                collaborator=collaborator,
                                reminder_type=REMINDER_POINT_EXIT,
                                message=point_reminder(str(collaborator.get("nome", "")), "saída"),
                                day=day,
                            )
                        )
                sent.extend(self._return_reminders(collaborator, records, stamp, day, tolerance, lead))
        return [row for row in sent if row]

    def _return_reminders(self, collaborator: dict, records: list[dict], stamp: datetime, day: date, tolerance: int, lead: timedelta) -> list[dict]:
        interval_minutes = self._journey_interval_minutes(collaborator)
        if interval_minutes <= 0:
            return []
        sent: list[dict] = []
        for pause_record in records:
            if str(pause_record.get("tipo_ponto", "")) != "pausa":
                continue
            pause_dt = parse_datetime(pause_record.get("data_hora"))
            return_dt = pause_dt + timedelta(minutes=interval_minutes)
            limit_dt = return_dt + timedelta(minutes=tolerance)
            if self._has_return_after_pause(records, pause_dt):
                continue
            if return_dt - lead <= stamp < return_dt:
                sent.append(
                    self._send_once(
                        collaborator=collaborator,
                        reminder_type=REMINDER_POINT_RETURN,
                        message=return_reminder(str(collaborator.get("nome", "")), format_time(return_dt)),
                        day=day,
                        point_record=pause_record,
                    )
                )
            elif return_dt <= stamp <= limit_dt:
                sent.append(
                    self._send_once(
                        collaborator=collaborator,
                        reminder_type=REMINDER_POINT_RETURN_TOLERANCE,
                        message=return_tolerance_reminder(str(collaborator.get("nome", "")), format_time(limit_dt)),
                        day=day,
                        point_record=pause_record,
                    )
                )
        return [row for row in sent if row]

    def _send_once(
        self,
        *,
        collaborator: dict,
        reminder_type: str,
        message: str,
        day: date | str,
        task: dict | None = None,
        point_record: dict | None = None,
    ) -> dict | None:
        task = task or {}
        point_record = point_record or {}
        day_text = format_date(day)
        collaborator_id = str(collaborator.get("colaborador_id", ""))
        task_id = str(task.get("tarefa_id", ""))
        point_id = str(point_record.get("ponto_id", ""))
        if self._reminder_exists(day_text, reminder_type, collaborator_id, task_id=task_id, ponto_id=point_id):
            return None
        phone = normalize_whatsapp_phone(collaborator.get("telefone"))
        if not phone:
            return self._add_skipped_reminder(
                collaborator=collaborator,
                reminder_type=reminder_type,
                day_text=day_text,
                task=task,
                point_record=point_record,
                status="telefone inválido",
                observations="Colaborador sem telefone válido para WhatsApp.",
            )
        row = {
            "mensagem_id": uuid.uuid4().hex[:12],
            "data": day_text,
            "tipo": reminder_type,
            "colaborador_id": collaborator_id,
            "nome_colaborador": str(collaborator.get("nome", "")),
            "telefone": phone,
            "tarefa_id": task_id,
            "nome_tarefa": str(task.get("nome", "")),
            "ponto_id": point_id,
            "mensagem": message,
            "status": "pendente",
            "tentativas": 0,
            "proxima_tentativa_em": "",
            "ultimo_erro": "",
            "criado_em": format_datetime(),
            "enviado_em": "",
            "observacoes": "Lembrete aguardando envio pelo bot WhatsApp.",
        }
        return self.repository.add_message(row)

    def _add_skipped_reminder(
        self,
        *,
        collaborator: dict,
        reminder_type: str,
        day_text: str,
        status: str,
        observations: str,
        task: dict | None = None,
        point_record: dict | None = None,
    ) -> dict | None:
        task = task or {}
        point_record = point_record or {}
        collaborator_id = str(collaborator.get("colaborador_id", ""))
        task_id = str(task.get("tarefa_id", ""))
        point_id = str(point_record.get("ponto_id", ""))
        if self._reminder_exists(day_text, reminder_type, collaborator_id, task_id=task_id, ponto_id=point_id):
            return None
        return self.repository.add_sent_reminder(
            {
                "lembrete_id": uuid.uuid4().hex[:12],
                "data": day_text,
                "tipo": reminder_type,
                "colaborador_id": collaborator_id,
                "nome_colaborador": str(collaborator.get("nome", "")),
                "tarefa_id": task_id,
                "nome_tarefa": str(task.get("nome", "")),
                "ponto_id": point_id,
                "telefone": normalize_whatsapp_phone(collaborator.get("telefone")),
                "enviado_em": format_datetime(),
                "status": status,
                "observacoes": observations,
            }
        )

    def _reminder_exists(self, day_text: str, reminder_type: str, collaborator_id: str, *, task_id: str = "", ponto_id: str = "") -> bool:
        return self.repository.queued_reminder_exists(
            data=day_text,
            tipo=reminder_type,
            colaborador_id=collaborator_id,
            tarefa_id=task_id,
            ponto_id=ponto_id,
        ) or self.repository.reminder_exists(
            data=day_text,
            tipo=reminder_type,
            colaborador_id=collaborator_id,
            tarefa_id=task_id,
            ponto_id=ponto_id,
        )

    def _entered_responsible_collaborators_for_task(self, task: dict, day: date, stamp: datetime) -> list[dict]:
        present = self.time_clock_service.present_collaborators(day, format_time(stamp))
        present_ids = {str(row.get("colaborador_id", "")) for row in present}
        if not present_ids:
            return []
        expected = self.task_service.expected_collaborators_for_task(task, day)
        return [row for row in expected if str(row.get("colaborador_id", "")) in present_ids]

    def _task_already_checked(self, task: dict, collaborator: dict, day: date) -> bool:
        task_id = str(task.get("tarefa_id", ""))
        collaborator_id = str(collaborator.get("colaborador_id", ""))
        day_text = format_date(day)
        return any(
            str(row.get("tarefa_id", "")) == task_id and str(row.get("colaborador_id", "")) == collaborator_id
            for row in self.task_service.checks_for_date(day_text)
        )

    def _task_missed_occurrence_exists(self, task: dict, collaborator: dict, day: date) -> bool:
        repository = getattr(self.task_service, "occurrence_repository", None)
        if repository is None:
            return False
        return repository.exists(
            data=format_date(day),
            tipo=OCCURRENCE_TASK_MISSED,
            tarefa_id=str(task.get("tarefa_id", "")),
            colaborador_id=str(collaborator.get("colaborador_id", "")),
        )

    @staticmethod
    def _task_message_name(task: dict) -> str:
        return clean_text(task.get("descricao")) or clean_text(task.get("nome"))

    def _journey_for(self, collaborator: dict) -> dict | None:
        journey_id = clean_text(collaborator.get("jornada_id"))
        return self.journey_service.get(journey_id) if journey_id else None

    def _journey_tolerance(self, collaborator: dict) -> int:
        journey = self._journey_for(collaborator) or {}
        return _to_int(journey.get("tolerancia_minutos"), 0)

    def _journey_interval_minutes(self, collaborator: dict) -> int:
        journey = self._journey_for(collaborator) or {}
        return _to_int(journey.get("tempo_intervalo"), 0)

    def _suggested_pause_datetime(self, collaborator: dict, start_dt: datetime, end_dt: datetime) -> datetime | None:
        interval_minutes = self._journey_interval_minutes(collaborator)
        if interval_minutes <= 0:
            return None
        total_minutes = int((end_dt - start_dt).total_seconds() / 60)
        work_without_interval = max(total_minutes - interval_minutes, 0)
        return start_dt + timedelta(minutes=max(work_without_interval // 2, 0))

    @staticmethod
    def _has_record_between(records: list[dict], record_type: str, start_dt: datetime, end_dt: datetime) -> bool:
        for row in records:
            if str(row.get("tipo_ponto", "")) != record_type:
                continue
            stamp = parse_datetime(row.get("data_hora"))
            if start_dt <= stamp <= end_dt:
                return True
        return False

    @staticmethod
    def _has_return_after_pause(records: list[dict], pause_dt: datetime) -> bool:
        for row in records:
            if str(row.get("tipo_ponto", "")) != "retorno":
                continue
            if parse_datetime(row.get("data_hora")) > pause_dt:
                return True
        return False


def _is_enabled(value: object) -> bool:
    return clean_text(value).lower() in {"sim", "true", "1", "ativo", "yes"}


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(float(str(value or default).replace(",", ".")))
    except (TypeError, ValueError):
        return default
