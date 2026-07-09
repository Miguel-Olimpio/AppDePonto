"""Servicos de registro de ponto, presenca e jornada esperada."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Callable

from app.config.settings import (
    OCCURRENCE_EXIT_OUT_OF_TIME,
    OCCURRENCE_POINT_LATE,
    OCCURRENCE_RETURN_OUT_OF_TIME,
    TIME_RECORD_TYPES,
)
from app.models.time_record import TimeRecord
from app.repositories.collaborator_repository import CollaboratorRepository
from app.repositories.journey_repository import JourneyRepository
from app.repositories.time_record_repository import TimeRecordRepository
from app.repositories.work_schedule_repository import WorkScheduleRepository
from app.services.journey_service import JourneyService
from app.services.occurrence_service import OccurrenceService
from app.utils.dates import combine_date_time, format_date, format_datetime, format_time, now_local, parse_datetime, parse_time
from app.utils.durations import parse_hours, parse_minutes
from app.utils.formatting import clean_text
from app.utils.validators import validate_non_negative_int, validate_time_text


POINT_SEQUENCE = {
    "entrada": ("pausa", "saída"),
    "pausa": ("retorno",),
    "retorno": ("pausa", "saída"),
    "saída": ("entrada",),
}

NEXT_ACTION_TEXT = {
    "entrada": "Próxima ação sugerida: entrada.",
    "pausa": "Próxima ação sugerida: pausa ou saída.",
    "retorno": "Próxima ação sugerida: retorno.",
    "saída": "Próxima ação sugerida: pausa ou saída.",
    "fim": "Jornada encerrada. Uma nova entrada inicia outro turno.",
}


DEFAULT_SCHEDULE = {
    "entrada": "",
    "saida": "",
    "carga_horaria": 0,
    "tempo_intervalo": 60,
    "tolerancia_minutos": 0,
    "data_atualizacao": "",
}

PointRecordListener = Callable[[dict, dict], None]


class TimeClockService:
    def __init__(
        self,
        time_repository: TimeRecordRepository | None = None,
        collaborator_repository: CollaboratorRepository | None = None,
        schedule_repository: WorkScheduleRepository | None = None,
        occurrence_service: OccurrenceService | None = None,
        journey_repository: JourneyRepository | None = None,
    ):
        self.time_repository = time_repository or TimeRecordRepository()
        self.collaborator_repository = collaborator_repository or CollaboratorRepository()
        self.schedule_repository = schedule_repository or WorkScheduleRepository()
        self.occurrence_service = occurrence_service
        self.journey_repository = journey_repository or JourneyRepository()
        self.journey_service = JourneyService(self.journey_repository)
        self._record_listeners: list[PointRecordListener] = []

    def add_record_listener(self, listener: PointRecordListener) -> None:
        if listener not in self._record_listeners:
            self._record_listeners.append(listener)

    def get_work_schedule(self) -> dict:
        saved = self.schedule_repository.get()
        schedule = dict(DEFAULT_SCHEDULE)
        schedule.update(saved)
        schedule["tolerancia_minutos"] = validate_non_negative_int(
            schedule.get("tolerancia_minutos", 0),
            "Tolerância",
        )
        return schedule

    def update_work_schedule(
        self,
        entrada: str = "",
        saida: str = "",
        carga_horaria=0,
        tempo_intervalo="01:00",
        tolerancia_minutos=0,
    ) -> dict:
        entrada = _optional_time(entrada, "Horário esperado de entrada")
        saida = _optional_time(saida, "Horário esperado de saída")
        carga = parse_hours(carga_horaria, "Carga horária")
        intervalo = parse_minutes(tempo_intervalo, "Tempo de pausa")
        tolerance = validate_non_negative_int(tolerancia_minutos, "Tolerãncia")

        if entrada and saida and parse_time(entrada) >= parse_time(saida):
            raise ValueError("Horário de entrada deve ser antes da saída.")
        if intervalo <= 0:
            raise ValueError("Tempo de pausa deve ser informado em HH:MM.")

        return self.schedule_repository.save(
            {
                "entrada": entrada,
                "saida": saida,
                "carga_horaria": carga,
                "tempo_intervalo": intervalo,
                "tolerancia_minutos": tolerance,
                "data_atualizacao": format_datetime(),
            }
        )

    def record_time(
        self,
        colaborador_id: str,
        tipo_ponto: str,
        when: datetime | None = None,
        observacoes: str = "",
    ) -> dict:
        if tipo_ponto not in TIME_RECORD_TYPES:
            raise ValueError("Tipo de ponto inválido.")
        collaborator = self.collaborator_repository.get_by_id(colaborador_id)
        if not collaborator:
            raise KeyError("Colaborador não encontrado.")
        stamp = when or now_local()
        self.validate_time_sequence(str(colaborador_id), tipo_ponto, stamp)
        record = TimeRecord(
            ponto_id=uuid.uuid4().hex[:12],
            colaborador_id=str(colaborador_id),
            nome_colaborador=str(collaborator.get("nome", "")),
            tipo_ponto=tipo_ponto,
            data=format_date(stamp),
            hora=format_time(stamp),
            data_hora=format_datetime(stamp),
            observacoes=observacoes,
        )
        saved = self.time_repository.add(record)
        self._create_schedule_occurrence_if_needed(saved, collaborator, stamp)
        self._notify_record_listeners(saved, collaborator)
        return saved

    def list_today(self, day: date | str | None = None) -> list[dict]:
        return self.time_repository.list_by_date(format_date(day))

    def list_collaborator_records_for_day(
        self,
        colaborador_id: str,
        day: date | str | None = None,
    ) -> list[dict]:
        date_str = format_date(day)
        rows = [
            row
            for row in self.time_repository.list_by_date(date_str)
            if str(row.get("colaborador_id", "")) == str(colaborador_id)
        ]
        rows.sort(key=lambda row: parse_datetime(row.get("data_hora")))
        return rows

    def last_record_for_collaborator(
        self,
        colaborador_id: str,
        day: date | str | None = None,
    ) -> dict | None:
        rows = self.list_collaborator_records_for_day(colaborador_id, day)
        return rows[-1] if rows else None

    def allowed_next_types(
        self,
        colaborador_id: str,
        day: date | str | None = None,
    ) -> tuple[str, ...]:
        last = self.last_record_for_collaborator(colaborador_id, day)
        if not last:
            return ("entrada",)
        return POINT_SEQUENCE.get(str(last.get("tipo_ponto", "")), ())

    def point_context(
        self,
        colaborador_id: str,
        day: date | str | None = None,
    ) -> dict:
        last = self.last_record_for_collaborator(colaborador_id, day)
        allowed = self.allowed_next_types(colaborador_id, day)
        if not last:
            last_text = "Nenhum ponto registrado hoje."
            next_text = NEXT_ACTION_TEXT["entrada"]
        else:
            tipo = str(last.get("tipo_ponto", ""))
            last_text = f"Último ponto: {tipo} às {last.get('hora', '')}."
            if tipo == "saída":
                next_text = NEXT_ACTION_TEXT["fim"]
            elif allowed == ("retorno",):
                next_text = NEXT_ACTION_TEXT["retorno"]
            else:
                next_text = NEXT_ACTION_TEXT.get(tipo, "Confira a próxima ação antes de registrar.")
        return {"last_record": last, "allowed_types": allowed, "last_text": last_text, "next_text": next_text}

    def validate_time_sequence(
        self,
        colaborador_id: str,
        tipo_ponto: str,
        when: datetime | None = None,
    ) -> None:
        stamp = when or now_local()
        allowed = self.allowed_next_types(colaborador_id, stamp.date())
        if tipo_ponto in allowed:
            return

        last = self.last_record_for_collaborator(colaborador_id, stamp.date())
        last_type = str((last or {}).get("tipo_ponto", ""))
        if not last:
            if tipo_ponto == "saída":
                raise ValueError("Não é possível registrar saída antes da entrada.")
            if tipo_ponto == "retorno":
                raise ValueError("Não é possível registrar retorno sem pausa registrada.")
            if tipo_ponto == "pausa":
                raise ValueError("Não é possível registrar pausa antes da entrada.")
        if tipo_ponto == "entrada" and last_type in {"entrada", "retorno"}:
            raise ValueError("Já existe uma entrada aberta. Registre pausa ou saída antes de nova entrada.")
        if tipo_ponto == "retorno" and last_type != "pausa":
            raise ValueError("Não é possível registrar retorno sem pausa registrada.")
        if tipo_ponto == "pausa" and last_type == "pausa":
            raise ValueError("Este colaborador já está em pausa. Registre retorno antes de nova pausa.")
        if tipo_ponto == "saída" and last_type == "pausa":
            raise ValueError("Registre o retorno da pausa antes da saída.")
        allowed_text = ", ".join(allowed) if allowed else "nenhuma ação"
        raise ValueError(f"Sequência inválida. Próxima ação permitida: {allowed_text}.")

    def present_collaborators(self, day: date | str | None = None, cutoff_time: str | None = None) -> list[dict]:
        date_str = format_date(day)
        cutoff_dt = combine_date_time(date_str, cutoff_time) if cutoff_time else None
        records = []
        for record in self.time_repository.list_by_date(date_str):
            record_dt = parse_datetime(record.get("data_hora"))
            if cutoff_dt and record_dt > cutoff_dt:
                continue
            records.append((record_dt, record))
        records.sort(key=lambda item: item[0])

        last_by_collaborator: dict[str, dict] = {}
        for _record_dt, record in records:
            last_by_collaborator[str(record.get("colaborador_id", ""))] = record

        active_by_id = {str(row.get("colaborador_id", "")): row for row in self.collaborator_repository.list_active()}
        present: list[dict] = []
        for colaborador_id, record in last_by_collaborator.items():
            if str(record.get("tipo_ponto", "")) == "saída":
                continue
            collaborator = active_by_id.get(colaborador_id)
            if collaborator:
                present.append(collaborator)
        present.sort(key=lambda row: str(row.get("nome", "")).lower())
        return present

    def point_activities_for_collaborator(
        self,
        colaborador_id: str,
        day: date | str | None = None,
        now: datetime | None = None,
    ) -> list[dict]:
        collaborator = self.collaborator_repository.get_by_id(colaborador_id)
        if not collaborator:
            return []
        stamp = now or now_local()
        target_day = day or stamp.date()
        records = self.list_collaborator_records_for_day(str(colaborador_id), target_day)
        first_by_type = self._first_records_by_type(records)
        schedule = self._schedule_for_collaborator(collaborator)
        tolerance = int(schedule.get("tolerancia_minutos") or 0)
        interval_minutes = int(schedule.get("tempo_intervalo") or 0)
        start_dt, end_dt = self._expected_work_bounds(collaborator, target_day, schedule)

        activities = [
            self._entry_activity(first_by_type.get("entrada"), start_dt, tolerance, stamp),
            self._pause_activity(first_by_type.get("pausa"), first_by_type.get("entrada"), end_dt, stamp),
            self._return_activity(first_by_type.get("retorno"), first_by_type.get("pausa"), interval_minutes, tolerance, stamp),
            self._exit_activity(first_by_type.get("saída"), first_by_type.get("entrada"), end_dt, tolerance, stamp),
        ]
        return activities

    @staticmethod
    def _first_records_by_type(records: list[dict]) -> dict[str, dict]:
        first: dict[str, dict] = {}
        for row in records:
            record_type = str(row.get("tipo_ponto", ""))
            if record_type and record_type not in first:
                first[record_type] = row
        return first

    def _expected_work_bounds(self, collaborator: dict, day: date | str, schedule: dict) -> tuple[datetime | None, datetime | None]:
        intervals = self.journey_service.get_work_intervals_for_date(collaborator, day)
        if intervals:
            return intervals[0]
        start_dt = combine_date_time(day, schedule.get("entrada", "")) if clean_text(schedule.get("entrada")) else None
        end_dt = combine_date_time(day, schedule.get("saida", "")) if clean_text(schedule.get("saida")) else None
        return start_dt, end_dt

    @staticmethod
    def _confirmed_activity(tipo: str, label: str, record: dict) -> dict:
        return {
            "tipo": tipo,
            "label": label,
            "status": f"Confirmada às {record.get('hora', '')}",
            "detail": "Ponto registrado.",
            "hora": record.get("hora", ""),
            "tag": "done",
        }

    def _entry_activity(self, record: dict | None, expected_dt: datetime | None, tolerance: int, stamp: datetime) -> dict:
        if record:
            return self._confirmed_activity("entrada", "Entrada", record)
        if expected_dt is None:
            return self._pending_activity("entrada", "Entrada", "Pendente", "Sem horário esperado definido.", "pending")
        limit = expected_dt + timedelta(minutes=tolerance)
        if stamp < expected_dt:
            return self._pending_activity("entrada", "Entrada", "Pendente", f"Prevista às {format_time(expected_dt)}.", "pending")
        if stamp <= limit:
            return self._pending_activity("entrada", "Entrada", "Em horário", f"Registre até {format_time(limit)}.", "running")
        return self._pending_activity("entrada", "Entrada", "Atrasada", f"Prevista às {format_time(expected_dt)}.", "late")

    def _pause_activity(self, record: dict | None, entry_record: dict | None, end_dt: datetime | None, stamp: datetime) -> dict:
        if record:
            return self._confirmed_activity("pausa", "Pausa", record)
        if not entry_record:
            return self._pending_activity("pausa", "Pausa", "Pendente", "Aguardando entrada.", "pending")
        if end_dt and stamp > end_dt:
            return self._pending_activity("pausa", "Pausa", "Atrasada", "Pausa não registrada no turno.", "late")
        return self._pending_activity("pausa", "Pausa", "Atenção", "Registre quando iniciar o intervalo.", "running")

    def _return_activity(
        self,
        record: dict | None,
        pause_record: dict | None,
        interval_minutes: int,
        tolerance: int,
        stamp: datetime,
    ) -> dict:
        if record:
            return self._confirmed_activity("retorno", "Retorno", record)
        if not pause_record:
            return self._pending_activity("retorno", "Retorno", "Pendente", "Aguardando pausa.", "pending")
        if interval_minutes <= 0:
            return self._pending_activity("retorno", "Retorno", "Pendente", "Tempo de pausa não definido.", "pending")
        pause_dt = parse_datetime(pause_record.get("data_hora"))
        expected_dt = pause_dt + timedelta(minutes=interval_minutes)
        limit = expected_dt + timedelta(minutes=tolerance)
        if stamp < expected_dt:
            return self._pending_activity("retorno", "Retorno", "Pendente", f"Previsto às {format_time(expected_dt)}.", "pending")
        if stamp <= limit:
            return self._pending_activity("retorno", "Retorno", "Em tolerância", f"Registre até {format_time(limit)}.", "running")
        return self._pending_activity("retorno", "Retorno", "Atrasado", f"Limite era {format_time(limit)}.", "late")

    def _exit_activity(self, record: dict | None, entry_record: dict | None, expected_dt: datetime | None, tolerance: int, stamp: datetime) -> dict:
        if record:
            return self._confirmed_activity("saída", "Saída", record)
        if not entry_record:
            return self._pending_activity("saída", "Saída", "Pendente", "Aguardando entrada.", "pending")
        if expected_dt is None:
            return self._pending_activity("saída", "Saída", "Pendente", "Sem horário esperado definido.", "pending")
        limit = expected_dt + timedelta(minutes=tolerance)
        if stamp < expected_dt:
            return self._pending_activity("saída", "Saída", "Pendente", f"Prevista às {format_time(expected_dt)}.", "pending")
        if stamp <= limit:
            return self._pending_activity("saída", "Saída", "Em horário", f"Registre até {format_time(limit)}.", "running")
        return self._pending_activity("saída", "Saída", "Atrasada", f"Prevista às {format_time(expected_dt)}.", "late")

    @staticmethod
    def _pending_activity(tipo: str, label: str, status: str, detail: str, tag: str) -> dict:
        return {
            "tipo": tipo,
            "label": label,
            "status": status,
            "detail": detail,
            "hora": "",
            "tag": tag,
        }

    def _create_schedule_occurrence_if_needed(self, record: dict, collaborator: dict, stamp: datetime) -> None:
        if self.occurrence_service is None:
            return

        schedule = self._schedule_for_collaborator(collaborator)
        tipo = str(record.get("tipo_ponto", ""))
        tolerance = int(schedule.get("tolerancia_minutos") or 0)
        tolerance_delta = timedelta(minutes=tolerance)

        if tipo == "entrada":
            expected = clean_text(schedule.get("entrada"))
            if not expected:
                return
            expected_dt = combine_date_time(stamp.date(), expected)
            if stamp <= expected_dt + tolerance_delta:
                return
            occurrence_type = OCCURRENCE_POINT_LATE
            description = "Entrada registrada após a tolerãncia."

        elif tipo == "retorno":
            interval_minutes = int(schedule.get("tempo_intervalo") or 0)
            if interval_minutes <= 0:
                return
            pause_record = self._last_pause_before(str(collaborator.get("colaborador_id", "")), stamp)
            if not pause_record:
                return
            pause_dt = parse_datetime(pause_record.get("data_hora"))
            expected_dt = pause_dt + timedelta(minutes=interval_minutes)
            if stamp <= expected_dt + tolerance_delta:
                return
            occurrence_type = OCCURRENCE_RETURN_OUT_OF_TIME
            description = "Retorno registrado fora do horário esperado."

        elif tipo == "saída":
            expected = clean_text(schedule.get("saida"))
            if not expected:
                return
            expected_dt = combine_date_time(stamp.date(), expected)
            if expected_dt - tolerance_delta <= stamp <= expected_dt + tolerance_delta:
                return
            occurrence_type = OCCURRENCE_EXIT_OUT_OF_TIME
            description = "Saída registrada fora do horário esperado."

        else:
            # Pausa não tem horário fixo: o retorno é calculado a partir dela.
            return

        self.occurrence_service.create_occurrence(
            tipo=occurrence_type,
            descricao=description,
            day=stamp.date(),
            when=stamp,
            colaborador_id=str(collaborator.get("colaborador_id", "")),
            nome_colaborador=str(collaborator.get("nome", "")),
        )

    def _last_pause_before(self, colaborador_id: str, stamp: datetime) -> dict | None:
        pauses: list[tuple[datetime, dict]] = []
        for row in self.time_repository.list_by_collaborator(str(colaborador_id)):
            if str(row.get("tipo_ponto", "")) != "pausa":
                continue
            try:
                pause_dt = parse_datetime(row.get("data_hora"))
            except Exception:
                continue
            if pause_dt < stamp:
                pauses.append((pause_dt, row))
        if not pauses:
            return None
        pauses.sort(key=lambda item: item[0])
        return pauses[-1][1]

    def _schedule_for_collaborator(self, collaborator: dict) -> dict:
        jornada_id = str(collaborator.get("jornada_id", "") or "")
        if jornada_id:
            journey = self.journey_repository.get_by_id(jornada_id)
            if journey:
                return {
                    "entrada": journey.get("entrada") or journey.get("horario_inicio_escala", ""),
                    "saida": journey.get("saida", ""),
                    "carga_horaria": journey.get("carga_horaria", 0),
                    "tempo_intervalo": journey.get("tempo_intervalo", 0),
                    "tolerancia_minutos": journey.get("tolerancia_minutos", 0),
                    "data_atualizacao": journey.get("data_atualizacao", ""),
                }
        return self.get_work_schedule()

    def _notify_record_listeners(self, record: dict, collaborator: dict) -> None:
        for listener in list(self._record_listeners):
            try:
                listener(record, collaborator)
            except Exception:
                # O ponto não pode falhar por uma integração externa como WhatsApp.
                continue



def _optional_time(value: str, field_name: str) -> str:
    text = clean_text(value)
    if not text:
        return ""
    return validate_time_text(text, field_name)
