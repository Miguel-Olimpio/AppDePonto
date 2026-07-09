"""Modelo de tarefa/POP obrigatorio."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class Task:
    tarefa_id: str
    nome: str
    descricao: str = ""
    horario_inicio: str = ""
    horario_limite: str = ""
    tolerancia_minutos: int = 0
    dias_semana: str = "todos"
    setor_id: str = ""
    nome_setor: str = ""
    active: bool = True
    data_cadastro: str = ""
    data_atualizacao: str = ""
    observacoes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, row: dict) -> "Task":
        active = row.get("active", True)
        if isinstance(active, str):
            active = active.strip().lower() not in {"false", "0", "nao", "n?o", "inativo"}
        return cls(
            tarefa_id=str(row.get("tarefa_id", "")),
            nome=str(row.get("nome", "")),
            descricao=str(row.get("descricao", "")),
            horario_inicio=str(row.get("horario_inicio", "")),
            horario_limite=str(row.get("horario_limite", "")),
            tolerancia_minutos=int(row.get("tolerancia_minutos") or 0),
            dias_semana=str(row.get("dias_semana", "todos") or "todos"),
            setor_id=str(row.get("setor_id", "")),
            nome_setor=str(row.get("nome_setor", "")),
            active=bool(active),
            data_cadastro=str(row.get("data_cadastro", "")),
            data_atualizacao=str(row.get("data_atualizacao", "")),
            observacoes=str(row.get("observacoes", "")),
        )
