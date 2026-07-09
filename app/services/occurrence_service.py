"""Servicos de ocorrencias operacionais."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from app.config.settings import OCCURRENCE_STATUS_OPEN, OCCURRENCE_STATUS_RESOLVED, OCCURRENCE_STATUSES
from app.models.occurrence import Occurrence
from app.repositories.occurrence_repository import OccurrenceRepository
from app.utils.dates import format_date, format_datetime, now_local, parse_date, parse_datetime
from app.utils.formatting import clean_text

_STATUS_ALIASES = {
    "": OCCURRENCE_STATUS_OPEN,
    "aberta": OCCURRENCE_STATUS_OPEN,
    "aberto": OCCURRENCE_STATUS_OPEN,
    "pendente": OCCURRENCE_STATUS_OPEN,
    "resolvida": OCCURRENCE_STATUS_RESOLVED,
    "resolvido": OCCURRENCE_STATUS_RESOLVED,
}


class OccurrenceService:
    def __init__(self, repository: OccurrenceRepository | None = None):
        self.repository = repository or OccurrenceRepository()

    def create_occurrence(
        self,
        *,
        tipo: str,
        descricao: str,
        day: date | str | None = None,
        when: datetime | None = None,
        colaborador_id: str = "",
        nome_colaborador: str = "",
        tarefa_id: str = "",
        nome_tarefa: str = "",
        setor_id: str = "",
        nome_setor: str = "",
        horario_limite: str = "",
        status: str = OCCURRENCE_STATUS_OPEN,
    ) -> dict:
        stamp = when or now_local()
        occurrence = Occurrence(
            ocorrencia_id=uuid.uuid4().hex[:12],
            data=format_date(day or stamp.date()),
            tipo=tipo,
            descricao=descricao,
            colaborador_id=colaborador_id,
            nome_colaborador=nome_colaborador,
            tarefa_id=tarefa_id,
            nome_tarefa=nome_tarefa,
            setor_id=clean_text(setor_id),
            nome_setor=clean_text(nome_setor),
            horario_limite=horario_limite,
            data_hora_registro=format_datetime(stamp),
            status=_normalize_status(status),
        )
        return self._normalize_row(self.repository.add(occurrence))

    def list_all(self) -> list[dict]:
        return [self._normalize_row(row) for row in self.repository.list_all()]

    def list_recent(self, limit: int = 20) -> list[dict]:
        return list(reversed(self.list_all()))[:limit]

    def get(self, occurrence_id: str) -> dict | None:
        row = self.repository.get_by_id(occurrence_id)
        return self._normalize_row(row) if row else None

    def occurrence_types(self) -> list[str]:
        values = {clean_text(row.get("tipo")) for row in self.list_all() if clean_text(row.get("tipo"))}
        return sorted(values, key=str.lower)

    def filter_occurrences(
        self,
        *,
        data_inicio: str = "",
        data_fim: str = "",
        colaborador: str = "",
        tipo: str = "",
        status: str = "",
    ) -> list[dict]:
        start = parse_date(data_inicio) if clean_text(data_inicio) else None
        end = parse_date(data_fim) if clean_text(data_fim) else None
        if start and end and start > end:
            raise ValueError("Data inicial deve ser antes da data final.")

        collaborator_filter = clean_text(colaborador).lower()
        type_filter = clean_text(tipo)
        status_filter = _normalize_status(status) if clean_text(status) and clean_text(status).lower() != "todos" else ""
        rows: list[dict] = []
        for row in self.list_all():
            row_date = parse_date(row.get("data"))
            if start and row_date < start:
                continue
            if end and row_date > end:
                continue
            if collaborator_filter and collaborator_filter not in clean_text(row.get("nome_colaborador")).lower():
                continue
            if type_filter and type_filter.lower() != "todos" and clean_text(row.get("tipo")) != type_filter:
                continue
            if status_filter and clean_text(row.get("status")) != status_filter:
                continue
            rows.append(row)
        rows.sort(key=lambda item: _sort_key(item), reverse=True)
        return rows

    def update_treatment(
        self,
        occurrence_id: str,
        *,
        status: str = "",
        acao_tomada: str = "",
        responsavel_tratativa: str = "",
        observacoes: str = "",
    ) -> dict:
        current = self.get(occurrence_id) or {}
        normalized_status = _normalize_status(status or current.get("status"))
        if normalized_status not in OCCURRENCE_STATUSES:
            raise ValueError("Status da ocorrencia invalido.")
        updated = self.repository.update(
            occurrence_id,
            {
                "status": normalized_status,
                "acao_tomada": clean_text(acao_tomada),
                "responsavel_tratativa": clean_text(responsavel_tratativa),
                "observacoes": clean_text(observacoes),
                "data_atualizacao": format_datetime(),
            },
        )
        return self._normalize_row(updated)

    def mark_resolved(
        self,
        occurrence_id: str,
        *,
        acao_tomada: str = "Resolvida pelo gestor.",
        responsavel_tratativa: str = "",
        observacoes: str = "",
    ) -> dict:
        return self.update_treatment(
            occurrence_id,
            status=OCCURRENCE_STATUS_RESOLVED,
            acao_tomada=acao_tomada,
            responsavel_tratativa=responsavel_tratativa,
            observacoes=observacoes,
        )

    def mark_pending(self, occurrence_id: str, *, observacoes: str = "") -> dict:
        current = self.get(occurrence_id) or {}
        return self.update_treatment(
            occurrence_id,
            status=OCCURRENCE_STATUS_OPEN,
            acao_tomada=str(current.get("acao_tomada", "")),
            responsavel_tratativa=str(current.get("responsavel_tratativa", "")),
            observacoes=observacoes or str(current.get("observacoes", "")),
        )


    def waive_occurrence(
        self,
        occurrence_id: str,
        *,
        motivo_abono: str,
        observacao_abono: str = "",
    ) -> dict:
        reason = clean_text(motivo_abono)
        if not reason:
            raise ValueError("Motivo do abono e obrigatorio.")
        updated = self.repository.update(
            occurrence_id,
            {
                "abonado": True,
                "motivo_abono": reason,
                "observacao_abono": clean_text(observacao_abono),
                "data_abono": format_datetime(),
                "data_atualizacao": format_datetime(),
            },
        )
        return self._normalize_row(updated)

    def export_pdf(
        self,
        rows: list[dict],
        *,
        data_inicio: str = "",
        data_fim: str = "",
    ) -> str:
        from app.pdf.occurrence_report_pdf import generate_occurrence_report_pdf

        return generate_occurrence_report_pdf(rows, data_inicio=data_inicio, data_fim=data_fim)

    def _normalize_row(self, row: dict[str, Any]) -> dict:
        normalized = dict(row)
        normalized["status"] = _normalize_status(normalized.get("status"))
        for field in ("acao_tomada", "responsavel_tratativa", "observacoes", "data_atualizacao", "motivo_abono", "observacao_abono", "data_abono", "setor_id", "nome_setor"):
            normalized[field] = "" if normalized.get(field) is None else str(normalized.get(field, ""))
        normalized["abonado"] = str(normalized.get("abonado", "")).lower() in {"true", "1", "sim", "yes"}
        return normalized


def _normalize_status(value: Any) -> str:
    text = clean_text(value).lower()
    return _STATUS_ALIASES.get(text, clean_text(value) or OCCURRENCE_STATUS_OPEN)


def _sort_key(row: dict) -> tuple:
    try:
        registered = parse_datetime(row.get("data_hora_registro"))
    except Exception:
        registered = datetime.combine(parse_date(row.get("data")), datetime.min.time())
    return (parse_date(row.get("data")), registered)
