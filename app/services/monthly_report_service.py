"""Calculo mensal gerencial de ponto, faltas, bonus e pagamento estimado."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Any

from app.config.settings import OCCURRENCE_POINT_MISSING, OCCURRENCE_TASK_LATE, OCCURRENCE_TASK_MISSED
from app.services.collaborator_service import CollaboratorService
from app.services.journey_service import JourneyService
from app.services.occurrence_service import OccurrenceService
from app.services.goal_service import GoalService
from app.services.task_service import TaskService
from app.services.time_clock_service import TimeClockService
from app.utils.dates import format_date, parse_date, parse_datetime


class MonthlyReportService:
    def __init__(
        self,
        collaborator_service: CollaboratorService,
        journey_service: JourneyService,
        time_clock_service: TimeClockService,
        task_service: TaskService,
        occurrence_service: OccurrenceService,
        goal_service: GoalService | None = None,
    ):
        self.collaborator_service = collaborator_service
        self.journey_service = journey_service
        self.time_clock_service = time_clock_service
        self.task_service = task_service
        self.occurrence_service = occurrence_service
        self.goal_service = goal_service

    def month_period(self, month_text: str) -> tuple[date, date]:
        month, year = _parse_month_year(month_text)
        return date(year, month, 1), date(year, month, monthrange(year, month)[1])

    def calculate_month(self, month_text: str) -> dict:
        start, end = self.month_period(month_text)
        occurrences = self._occurrences_between(start, end)
        journeys = {str(row.get("jornada_id", "")): row for row in self.journey_service.list_all()}
        collaborators = self.collaborator_service.list_active()
        rows = [self.calculate_employee_payment(row, journeys, occurrences, start, end, month_text) for row in collaborators]
        return {
            "mes": month_text,
            "data_inicio": format_date(start),
            "data_fim": format_date(end),
            "colaboradores": rows,
            "ocorrencias": occurrences,
            "abonos": [row for row in occurrences if bool(row.get("abonado", False))],
            "totais": {
                "salario_base": sum(item["salario_base"] for item in rows),
                "desconto_faltas": sum(item["desconto_faltas"] for item in rows),
                "bonus_assiduidade": sum(item["bonus_assiduidade_aplicado"] for item in rows),
                "bonus_tarefas": sum(item["bonus_tarefas_aplicado"] for item in rows),
                "bonus_meta": sum(item["bonus_meta_aplicado"] for item in rows),
                "salario_estimado": sum(item["salario_final"] for item in rows),
            },
        }

    def calculate_employee_payment(
        self,
        collaborator: dict,
        journeys: dict[str, dict] | None,
        occurrences: list[dict],
        start: date,
        end: date,
        month_text: str | None = None,
    ) -> dict:
        colaborador_id = str(collaborator.get("colaborador_id", ""))
        journey = (journeys or {}).get(str(collaborator.get("jornada_id", "")), None)
        expected_days = self.journey_service.expected_workdays(journey, start, end)
        worked_days = [day for day in expected_days if self._has_entry_for_workday(collaborator, day)]
        worked_set = set(worked_days)
        absent_days = [day for day in expected_days if day not in worked_set]
        collaborator_occurrences = [row for row in occurrences if str(row.get("colaborador_id", "")) == colaborador_id]

        excused_absences = self.get_excused_absences(absent_days, collaborator_occurrences)
        unexcused_absences = self.get_unexcused_absences(absent_days, collaborator_occurrences)
        task_violations = self.get_task_violations(collaborator_occurrences)

        late_count = sum(1 for row in collaborator_occurrences if "atrasado" in str(row.get("tipo", "")).lower())
        return_late_count = sum(1 for row in collaborator_occurrences if "retorno" in str(row.get("tipo", "")).lower())
        task_late_count = sum(1 for row in task_violations if row.get("tipo") == OCCURRENCE_TASK_LATE)
        task_missed_count = sum(1 for row in task_violations if row.get("tipo") == OCCURRENCE_TASK_MISSED)

        salary = _to_float(collaborator.get("salario_base"))
        attendance_bonus_registered = _to_float(collaborator.get("bonus_assiduidade"))
        task_bonus_registered = _to_float(collaborator.get("bonus_tarefas"))
        expected_count = len(expected_days)
        salary_day = salary / expected_count if expected_count else 0.0
        absence_discount = len(unexcused_absences) * salary_day
        salary_after_discounts = max(salary - absence_discount, 0.0)
        attendance_bonus_applied = attendance_bonus_registered if not unexcused_absences else 0.0
        if unexcused_absences:
            task_bonus_applied = 0.0
        elif task_violations:
            task_bonus_applied = 0.0
        else:
            task_bonus_applied = task_bonus_registered
        goal_summary = self._goal_summary_for_collaborator(collaborator, month_text or f"{start.month:02d}/{start.year}")
        goal_bonus_applied = float(goal_summary.get("bonus_meta_aplicado", 0) or 0)
        final_salary = salary_after_discounts + attendance_bonus_applied + task_bonus_applied + goal_bonus_applied

        attendance_message = "Bonus de assiduidade aplicado."
        if unexcused_absences:
            days_text = ", ".join(item["data"] for item in unexcused_absences)
            attendance_message = f"Perdeu bonus de assiduidade por falta em {days_text}."

        task_message = "Bonus por tarefas aplicado."
        if unexcused_absences:
            task_message = "Bonus por tarefas perdido porque houve falta nao abonada no periodo."
        elif task_violations:
            days_text = ", ".join(item["data"] for item in task_violations)
            task_message = f"Bonus por tarefas perdido por tarefa atrasada ou nao cumprida em {days_text}."

        calculation_text = (
            "salario_final = salario_base - desconto_faltas + "
            "bonus_assiduidade_aplicado + bonus_tarefas_aplicado + bonus_meta_aplicado"
        )
        no_expected_days_warning = "Sem dias esperados de trabalho no periodo." if expected_count == 0 else ""

        return {
            "colaborador_id": colaborador_id,
            "nome": str(collaborator.get("nome", "")),
            "cargo": str(collaborator.get("cargo", "")),
            "setor": str(collaborator.get("nome_setor", "")),
            "jornada": str((journey or {}).get("nome", "")),
            "salario_base": salary,
            "dias_esperados": expected_count,
            "dias_trabalhados": len(worked_days),
            "faltas": len(absent_days),
            "faltas_abonadas": len(excused_absences),
            "faltas_nao_abonadas": len(unexcused_absences),
            "atrasos": late_count,
            "retornos_pausa_atrasados": return_late_count,
            "pausas_fora_horario": return_late_count,
            "tarefas_atrasadas": task_late_count,
            "tarefas_nao_cumpridas": task_missed_count,
            "salario_dia": salary_day,
            "desconto_faltas": absence_discount,
            "salario_apos_descontos": salary_after_discounts,
            "bonus_assiduidade_cadastrado": attendance_bonus_registered,
            "bonus_assiduidade_aplicado": attendance_bonus_applied,
            "bonus_assiduidade_concedido": attendance_bonus_applied,
            "bonus_tarefas_cadastrado": task_bonus_registered,
            "bonus_tarefas_aplicado": task_bonus_applied,
            "bonus_tarefas_concedido": task_bonus_applied,
            "bonus_meta_aplicado": goal_bonus_applied,
            "metas_coletivas_atingidas": goal_summary.get("metas_coletivas_atingidas", []),
            "metas_individuais_atingidas": goal_summary.get("metas_individuais_atingidas", []),
            "metas_nao_atingidas": goal_summary.get("metas_nao_atingidas", []),
            "metas_detalhes": goal_summary.get("metas_detalhes", []),
            "mensagem_metas": goal_summary.get("mensagem_metas", "Nenhum bonus por meta aplicado no periodo."),
            "salario_estimado_final": final_salary,
            "salario_final": final_salary,
            "datas_trabalhadas": [format_date(day) for day in worked_days],
            "dias_falta": [item["data"] for item in excused_absences + unexcused_absences],
            "dias_falta_abonada": [item["data"] for item in excused_absences],
            "faltas_nao_abonadas_detalhes": unexcused_absences,
            "faltas_abonadas_detalhes": excused_absences,
            "tarefas_falhas_detalhes": task_violations,
            "ocorrencias_periodo_detalhes": collaborator_occurrences,
            "mensagem_assiduidade": attendance_message,
            "mensagem_tarefas": task_message,
            "calculo_texto": calculation_text,
            "sem_dias_esperados_aviso": no_expected_days_warning,
        }

    def get_unexcused_absences(self, absent_days: list[date], occurrences: list[dict]) -> list[dict]:
        rows: list[dict] = []
        for day in absent_days:
            occurrence = self._absence_occurrence_for_day(occurrences, day)
            if occurrence and bool(occurrence.get("abonado", False)):
                continue
            rows.append(self._absence_detail(day, occurrence, excused=False))
        return rows

    def get_excused_absences(self, absent_days: list[date], occurrences: list[dict]) -> list[dict]:
        rows: list[dict] = []
        for day in absent_days:
            occurrence = self._absence_occurrence_for_day(occurrences, day)
            if occurrence and bool(occurrence.get("abonado", False)):
                rows.append(self._absence_detail(day, occurrence, excused=True))
        return rows

    def get_task_violations(self, occurrences: list[dict]) -> list[dict]:
        rows: list[dict] = []
        for row in occurrences:
            if row.get("tipo") not in {OCCURRENCE_TASK_LATE, OCCURRENCE_TASK_MISSED}:
                continue
            rows.append(
                {
                    "data": str(row.get("data", "")),
                    "tarefa": str(row.get("nome_tarefa", "")) or "-",
                    "tipo": str(row.get("tipo", "")),
                    "impacto": "Perde bonus por tarefas.",
                    "descricao": str(row.get("descricao", "")),
                }
            )
        return rows

    def _goal_summary_for_collaborator(self, collaborator: dict, month_text: str) -> dict:
        if self.goal_service is None:
            return {
                "bonus_meta_aplicado": 0.0,
                "metas_coletivas_atingidas": [],
                "metas_individuais_atingidas": [],
                "metas_nao_atingidas": [],
                "metas_detalhes": [],
                "mensagem_metas": "Nenhum bonus por meta aplicado no periodo.",
            }
        return self.goal_service.calculate_bonus_for_collaborator(collaborator, month_text)

    def generate_pdf(self, month_text: str) -> str:
        from app.pdf.monthly_report_pdf import generate_monthly_report_pdf

        return generate_monthly_report_pdf(self.calculate_month(month_text))

    def generate_payment_pdf(self, month_text: str) -> str:
        from app.pdf.payment_report_pdf import generate_payment_report_pdf

        return generate_payment_report_pdf(self.calculate_month(month_text))

    def _absence_detail(self, day: date, occurrence: dict | None, *, excused: bool) -> dict:
        return {
            "data": format_date(day),
            "motivo": str((occurrence or {}).get("motivo_abono" if excused else "descricao", "")),
            "observacao": str((occurrence or {}).get("observacao_abono", "")),
            "impacto": "Nao desconta salario." if excused else "Desconta salario e perde bonus de assiduidade.",
            "ocorrencia_id": str((occurrence or {}).get("ocorrencia_id", "")),
        }

    def _absence_occurrence_for_day(self, occurrences: list[dict], day: date) -> dict | None:
        day_text = format_date(day)
        for row in occurrences:
            if str(row.get("data", "")) != day_text:
                continue
            if str(row.get("tipo", "")) != OCCURRENCE_POINT_MISSING:
                continue
            return row
        return None

    def _has_entry_for_workday(self, collaborator: dict, day: date) -> bool:
        colaborador_id = str(collaborator.get("colaborador_id", ""))
        intervals = self.journey_service.get_work_intervals_for_date(collaborator, day)
        if not intervals:
            return False
        for start, end in intervals:
            cursor = start.date()
            while cursor <= end.date():
                for row in self.time_clock_service.list_collaborator_records_for_day(colaborador_id, cursor):
                    if str(row.get("tipo_ponto", "")) != "entrada":
                        continue
                    try:
                        record_dt = parse_datetime(row.get("data_hora"))
                    except Exception:
                        continue
                    if start <= record_dt < end:
                        return True
                cursor += timedelta(days=1)
        return False

    def _occurrences_between(self, start: date, end: date) -> list[dict]:
        rows: list[dict] = []
        for row in self.occurrence_service.list_all():
            try:
                day = parse_date(row.get("data"))
            except Exception:
                continue
            if start <= day <= end:
                rows.append(row)
        return rows


def _parse_month_year(text: str) -> tuple[int, int]:
    raw = str(text or "").strip()
    parts = raw.split("/")
    if len(parts) != 2:
        raise ValueError("Informe o mes no formato MM/AAAA.")
    try:
        month = int(parts[0])
        year = int(parts[1])
    except ValueError as exc:
        raise ValueError("Informe o mes no formato MM/AAAA.") from exc
    if month < 1 or month > 12 or year < 1900:
        raise ValueError("Informe um mes/ano valido.")
    return month, year


def _to_float(value: Any) -> float:
    text = str(value or "0").strip().replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0
