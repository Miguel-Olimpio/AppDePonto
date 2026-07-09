"""Servicos de jornadas, escalas e dias esperados."""

from __future__ import annotations

import math
import uuid
from datetime import date, datetime, time, timedelta
from typing import Any

from app.config.settings import SCALE_TYPE_SCALE, SCALE_TYPE_WEEKLY, SCALE_TYPES, WEEKDAY_NAMES
from app.models.journey import Journey
from app.repositories.journey_repository import JourneyRepository
from app.utils.dates import combine_date_time, format_date, format_datetime, parse_date, parse_datetime, parse_time, weekday_name
from app.utils.durations import parse_hours, parse_minutes
from app.utils.formatting import bool_to_excel, clean_text, normalize_key
from app.utils.validators import require_text, validate_non_negative_int, validate_time_text

_LEGACY_SCALE_ALIASES = {"12x36": ("12x36", 12, 36), "24x48": ("24x48", 24, 48)}


class JourneyService:
    def __init__(self, repository: JourneyRepository | None = None):
        self.repository = repository or JourneyRepository()

    def create_journey(
        self,
        nome: str,
        tipo_escala: str = SCALE_TYPE_WEEKLY,
        entrada: str = "",
        saida: str = "",
        carga_horaria=0,
        tempo_intervalo="01:00",
        tolerancia_minutos=0,
        dias_semana: str = "todos",
        data_inicio_escala: str = "",
        descricao_escala: str = "",
        horas_trabalho=0,
        horas_descanso=0,
        horario_inicio_escala: str = "",
        observacoes: str = "",
        **_ignored,
    ) -> dict:
        payload = self._validate_payload(
            nome=nome,
            tipo_escala=tipo_escala,
            entrada=entrada,
            saida=saida,
            carga_horaria=carga_horaria,
            tempo_intervalo=tempo_intervalo,
            tolerancia_minutos=tolerancia_minutos,
            dias_semana=dias_semana,
            data_inicio_escala=data_inicio_escala,
            descricao_escala=descricao_escala,
            horas_trabalho=horas_trabalho,
            horas_descanso=horas_descanso,
            horario_inicio_escala=horario_inicio_escala,
            observacoes=observacoes,
        )
        journey = Journey(
            jornada_id=uuid.uuid4().hex[:12],
            active=True,
            data_cadastro=format_date(),
            data_atualizacao=format_datetime(),
            **payload,
        )
        return self.repository.add(journey)

    def update_journey(self, jornada_id: str, **changes) -> dict:
        current = self.repository.get_by_id(jornada_id)
        if not current:
            raise KeyError("Jornada nao encontrada.")
        merged = dict(current)
        merged.update(changes)
        payload = self._validate_payload(
            nome=merged.get("nome", ""),
            tipo_escala=merged.get("tipo_escala") or merged.get("tipo_jornada", SCALE_TYPE_WEEKLY),
            entrada=merged.get("entrada", ""),
            saida=merged.get("saida", ""),
            carga_horaria=merged.get("carga_horaria", 0),
            tempo_intervalo=merged.get("tempo_intervalo", 0),
            tolerancia_minutos=merged.get("tolerancia_minutos", 0),
            dias_semana=merged.get("dias_semana", "todos"),
            data_inicio_escala=merged.get("data_inicio_escala", ""),
            descricao_escala=merged.get("descricao_escala", ""),
            horas_trabalho=merged.get("horas_trabalho", 0),
            horas_descanso=merged.get("horas_descanso", 0),
            horario_inicio_escala=merged.get("horario_inicio_escala", ""),
            observacoes=merged.get("observacoes", ""),
        )
        payload["data_atualizacao"] = format_datetime()
        return self.repository.update(jornada_id, payload)

    def set_active(self, jornada_id: str, active: bool) -> dict:
        return self.repository.update(jornada_id, {"active": bool(active), "data_atualizacao": format_datetime()})

    def get(self, jornada_id: str) -> dict | None:
        return self.repository.get_by_id(jornada_id)

    def list_all(self) -> list[dict]:
        return self.repository.list_all()

    def list_active(self) -> list[dict]:
        return self.repository.list_active()

    def expected_workdays(self, journey: dict | None, start: date | str, end: date | str) -> list[date]:
        if not journey:
            return []
        start_day = parse_date(start)
        end_day = parse_date(end)
        if start_day > end_day:
            raise ValueError("Data inicial deve ser antes da data final.")
        if not bool_to_excel(journey.get("active", True)):
            return []
        days: list[date] = []
        cursor = start_day
        while cursor <= end_day:
            if self._work_intervals_for_journey_date(journey, cursor):
                days.append(cursor)
            cursor += timedelta(days=1)
        return days

    def calculate_scale_position(self, journey: dict | None, data_hora: datetime | str) -> dict[str, Any]:
        if not journey or self._journey_type(journey) != SCALE_TYPE_SCALE:
            return {"started": False, "is_working": False, "hours_elapsed": 0.0, "position_hours": 0.0, "cycle_hours": 0.0}
        stamp = self._coerce_datetime(data_hora)
        start_dt = self._scale_start_datetime(journey)
        work_hours, rest_hours = self._scale_hours(journey)
        cycle_hours = work_hours + rest_hours
        if start_dt is None or work_hours <= 0 or rest_hours <= 0 or cycle_hours <= 0:
            return {"started": False, "is_working": False, "hours_elapsed": 0.0, "position_hours": 0.0, "cycle_hours": 0.0}
        elapsed_hours = (stamp - start_dt).total_seconds() / 3600
        if elapsed_hours < 0:
            return {"started": False, "is_working": False, "hours_elapsed": elapsed_hours, "position_hours": 0.0, "cycle_hours": cycle_hours}
        position = elapsed_hours % cycle_hours
        return {
            "started": True,
            "is_working": position < work_hours,
            "hours_elapsed": elapsed_hours,
            "position_hours": position,
            "cycle_hours": cycle_hours,
            "work_hours": work_hours,
            "rest_hours": rest_hours,
        }

    def is_working_at(self, collaborator: dict, data_hora: datetime | str) -> bool:
        journey = self._journey_for_collaborator(collaborator)
        if not journey:
            return False
        stamp = self._coerce_datetime(data_hora)
        return any(start <= stamp < end for start, end in self._work_intervals_for_journey_date(journey, stamp.date()))

    def get_work_interval_for_date(self, collaborator: dict, day: date | str) -> tuple[datetime, datetime] | None:
        intervals = self.get_work_intervals_for_date(collaborator, day)
        return intervals[0] if intervals else None

    def get_work_intervals_for_date(self, collaborator: dict, day: date | str) -> list[tuple[datetime, datetime]]:
        journey = self._journey_for_collaborator(collaborator)
        if not journey:
            return []
        return self._work_intervals_for_journey_date(journey, parse_date(day))

    def should_work_on_date(self, collaborator: dict, day: date | str) -> bool:
        return bool(self.get_work_intervals_for_date(collaborator, day))

    def _validate_payload(self, **data) -> dict:
        scale = self._normalize_scale_type(data.get("tipo_escala") or data.get("tipo_jornada"))
        if scale not in SCALE_TYPES:
            raise ValueError("Tipo de jornada invalido.")
        tolerance = validate_non_negative_int(data.get("tolerancia_minutos", 0), "Tolerancia")
        entrada = clean_text(data.get("entrada"))
        saida = clean_text(data.get("saida"))
        descricao_escala = clean_text(data.get("descricao_escala"))
        horas_trabalho = validate_non_negative_int(data.get("horas_trabalho", 0), "Horas de trabalho")
        horas_descanso = validate_non_negative_int(data.get("horas_descanso", 0), "Horas de folga")
        horario_inicio_escala = clean_text(data.get("horario_inicio_escala"))
        data_inicio = clean_text(data.get("data_inicio_escala"))
        observacoes = clean_text(data.get("observacoes"))
        carga_horaria = parse_hours(data.get("carga_horaria", 0), "Carga horaria")
        tempo_intervalo = parse_minutes(data.get("tempo_intervalo", 0), "Tempo de pausa")
        if tempo_intervalo <= 0:
            raise ValueError("Tempo de pausa deve ser informado em HH:MM.")

        if scale == SCALE_TYPE_WEEKLY:
            entrada = validate_time_text(entrada, "Horario de entrada")
            saida = validate_time_text(saida, "Horario de saida")
            if parse_time(entrada) >= parse_time(saida):
                raise ValueError("Horario de entrada deve ser anterior a saida na escala semanal.")
            descricao_escala = ""
            horas_trabalho = 0
            horas_descanso = 0
            horario_inicio_escala = ""
            data_inicio = ""
            dias_semana = clean_text(data.get("dias_semana")) or "todos"
        else:
            legacy = _LEGACY_SCALE_ALIASES.get(clean_text(data.get("tipo_escala")).lower())
            if legacy and not descricao_escala:
                descricao_escala, horas_trabalho, horas_descanso = legacy
            descricao_escala = require_text(descricao_escala, "Descricao da escala")
            if horas_trabalho <= 0:
                raise ValueError("Horas trabalhadas deve ser maior que zero.")
            if horas_descanso <= 0:
                raise ValueError("Horas de folga deve ser maior que zero.")
            if not data_inicio:
                raise ValueError("Escala precisa de data inicial.")
            parse_date(data_inicio)
            horario_inicio_escala = validate_time_text(horario_inicio_escala or entrada, "Horario inicial da escala")
            entrada = ""
            saida = clean_text(saida)
            if saida:
                saida = validate_time_text(saida, "Horario de saida")
            dias_semana = ""
            if carga_horaria <= 0:
                carga_horaria = float(horas_trabalho)

        return {
            "nome": require_text(data.get("nome", ""), "Nome da jornada"),
            "tipo_escala": scale,
            "entrada": entrada,
            "saida": saida,
            "carga_horaria": carga_horaria,
            "tempo_intervalo": tempo_intervalo,
            "tolerancia_minutos": tolerance,
            "dias_semana": dias_semana,
            "descricao_escala": descricao_escala,
            "horas_trabalho": horas_trabalho,
            "horas_descanso": horas_descanso,
            "data_inicio_escala": data_inicio,
            "horario_inicio_escala": horario_inicio_escala,
            "observacoes": observacoes,
        }

    def _work_intervals_for_journey_date(self, journey: dict, day: date) -> list[tuple[datetime, datetime]]:
        if not bool_to_excel(journey.get("active", True)):
            return []
        if self._journey_type(journey) == SCALE_TYPE_SCALE:
            return self._scale_work_intervals_for_date(journey, day)
        if not self._weekly_runs_on_day(journey, day):
            return []
        entrada = clean_text(journey.get("entrada"))
        saida = clean_text(journey.get("saida"))
        if not entrada or not saida:
            return []
        return [(combine_date_time(day, entrada), combine_date_time(day, saida))]

    def _scale_work_intervals_for_date(self, journey: dict, day: date) -> list[tuple[datetime, datetime]]:
        start_dt = self._scale_start_datetime(journey)
        work_hours, rest_hours = self._scale_hours(journey)
        if start_dt is None or work_hours <= 0 or rest_hours <= 0:
            return []
        day_start = datetime.combine(day, time.min)
        day_end = day_start + timedelta(days=1)
        if day_end <= start_dt:
            return []
        cycle_seconds = (work_hours + rest_hours) * 3600
        offset_seconds = (day_start - start_dt).total_seconds()
        first_cycle = max(0, math.floor(offset_seconds / cycle_seconds) - 1)
        intervals: list[tuple[datetime, datetime]] = []
        index = first_cycle
        while True:
            work_start = start_dt + timedelta(seconds=index * cycle_seconds)
            work_end = work_start + timedelta(hours=work_hours)
            if work_start >= day_end and index > first_cycle:
                break
            if work_start < day_end and work_end > day_start:
                intervals.append((work_start, work_end))
            index += 1
            if index > first_cycle + 20:
                break
        return intervals

    def _scale_start_datetime(self, journey: dict) -> datetime | None:
        data_inicio = clean_text(journey.get("data_inicio_escala"))
        horario_inicio = clean_text(journey.get("horario_inicio_escala")) or clean_text(journey.get("entrada"))
        if not data_inicio or not horario_inicio:
            return None
        return datetime.combine(parse_date(data_inicio), parse_time(horario_inicio))

    def _scale_hours(self, journey: dict) -> tuple[int, int]:
        try:
            return int(journey.get("horas_trabalho", 0) or 0), int(journey.get("horas_descanso", 0) or 0)
        except (TypeError, ValueError):
            return 0, 0

    def _journey_for_collaborator(self, collaborator: dict) -> dict | None:
        jornada_id = str(collaborator.get("jornada_id", "") or "")
        return self.get(jornada_id) if jornada_id else None

    def _journey_type(self, journey: dict) -> str:
        return self._normalize_scale_type(journey.get("tipo_escala") or journey.get("tipo_jornada"))

    def _coerce_datetime(self, value: datetime | date | str) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, time.min)
        return parse_datetime(value)

    def _normalize_scale_type(self, value) -> str:
        text = clean_text(value)
        if normalize_key(text) in {"escala", "12x36", "24x48"}:
            return SCALE_TYPE_SCALE
        return SCALE_TYPE_WEEKLY if not text else text

    def _weekly_runs_on_day(self, journey: dict, day: date) -> bool:
        raw = normalize_key(journey.get("dias_semana", "todos"))
        if not raw or raw == "todos":
            return True
        parts = {normalize_key(part) for part in raw.replace(";", ",").split(",") if clean_text(part)}
        current = normalize_key(weekday_name(day))
        aliases = {current, current[:3], str(day.weekday() + 1), normalize_key(WEEKDAY_NAMES[day.weekday()])}
        return bool(parts & aliases)
