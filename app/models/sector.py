"""Modelo de setor da empresa."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class Sector:
    setor_id: str
    nome: str
    descricao: str = ""
    active: bool = True
    data_cadastro: str = ""
    data_atualizacao: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, row: dict) -> "Sector":
        active = row.get("active", True)
        if isinstance(active, str):
            active = active.strip().lower() not in {"false", "0", "nao", "n?o", "inativo"}
        return cls(
            setor_id=str(row.get("setor_id", "")),
            nome=str(row.get("nome", "")),
            descricao=str(row.get("descricao", "")),
            active=bool(active),
            data_cadastro=str(row.get("data_cadastro", "")),
            data_atualizacao=str(row.get("data_atualizacao", "")),
        )
