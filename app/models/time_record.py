"""Modelo de registro de ponto."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class TimeRecord:
    ponto_id: str
    colaborador_id: str
    nome_colaborador: str
    tipo_ponto: str
    data: str
    hora: str
    data_hora: str
    observacoes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, row: dict) -> "TimeRecord":
        return cls(
            ponto_id=str(row.get("ponto_id", "")),
            colaborador_id=str(row.get("colaborador_id", "")),
            nome_colaborador=str(row.get("nome_colaborador", "")),
            tipo_ponto=str(row.get("tipo_ponto", "")),
            data=str(row.get("data", "")),
            hora=str(row.get("hora", "")),
            data_hora=str(row.get("data_hora", "")),
            observacoes=str(row.get("observacoes", "")),
        )

