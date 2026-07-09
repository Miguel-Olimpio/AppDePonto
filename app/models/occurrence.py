"""Modelo de ocorrencia operacional."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.config.settings import OCCURRENCE_STATUS_OPEN


@dataclass(slots=True)
class Occurrence:
    ocorrencia_id: str
    data: str
    tipo: str
    descricao: str
    colaborador_id: str = ""
    nome_colaborador: str = ""
    tarefa_id: str = ""
    nome_tarefa: str = ""
    setor_id: str = ""
    nome_setor: str = ""
    horario_limite: str = ""
    data_hora_registro: str = ""
    status: str = OCCURRENCE_STATUS_OPEN
    acao_tomada: str = ""
    responsavel_tratativa: str = ""
    observacoes: str = ""
    data_atualizacao: str = ""
    abonado: bool = False
    motivo_abono: str = ""
    observacao_abono: str = ""
    data_abono: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, row: dict) -> "Occurrence":
        return cls(
            ocorrencia_id=str(row.get("ocorrencia_id", "")),
            data=str(row.get("data", "")),
            tipo=str(row.get("tipo", "")),
            descricao=str(row.get("descricao", "")),
            colaborador_id=str(row.get("colaborador_id", "")),
            nome_colaborador=str(row.get("nome_colaborador", "")),
            tarefa_id=str(row.get("tarefa_id", "")),
            nome_tarefa=str(row.get("nome_tarefa", "")),
            setor_id=str(row.get("setor_id", "")),
            nome_setor=str(row.get("nome_setor", "")),
            horario_limite=str(row.get("horario_limite", "")),
            data_hora_registro=str(row.get("data_hora_registro", "")),
            status=str(row.get("status", OCCURRENCE_STATUS_OPEN) or OCCURRENCE_STATUS_OPEN),
            acao_tomada=str(row.get("acao_tomada", "")),
            responsavel_tratativa=str(row.get("responsavel_tratativa", "")),
            observacoes=str(row.get("observacoes", "")),
            data_atualizacao=str(row.get("data_atualizacao", "")),
            abonado=str(row.get("abonado", "")).lower() in {"true", "1", "sim", "yes"},
            motivo_abono=str(row.get("motivo_abono", "")),
            observacao_abono=str(row.get("observacao_abono", "")),
            data_abono=str(row.get("data_abono", "")),
        )
