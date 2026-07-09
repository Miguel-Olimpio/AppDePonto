"""Modelo de checagem de tarefa."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class TaskCheck:
    check_id: str
    tarefa_id: str
    nome_tarefa: str
    colaborador_id: str
    nome_colaborador: str
    data: str
    hora_check: str
    status: str
    observacoes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, row: dict) -> "TaskCheck":
        return cls(
            check_id=str(row.get("check_id", "")),
            tarefa_id=str(row.get("tarefa_id", "")),
            nome_tarefa=str(row.get("nome_tarefa", "")),
            colaborador_id=str(row.get("colaborador_id", "")),
            nome_colaborador=str(row.get("nome_colaborador", "")),
            data=str(row.get("data", "")),
            hora_check=str(row.get("hora_check", "")),
            status=str(row.get("status", "")),
            observacoes=str(row.get("observacoes", "")),
        )

