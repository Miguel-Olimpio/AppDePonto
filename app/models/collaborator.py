"""Modelo de colaborador."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.config.settings import COLLABORATOR_STATUS_ACTIVE


@dataclass(slots=True)
class Collaborator:
    colaborador_id: str
    nome: str
    cargo: str = ""
    telefone: str = ""
    setor_id: str = ""
    nome_setor: str = ""
    salario_base: float = 0.0
    jornada_id: str = ""
    bonus_assiduidade: float = 0.0
    bonus_tarefas: float = 0.0
    status: str = COLLABORATOR_STATUS_ACTIVE
    data_cadastro: str = ""
    data_atualizacao: str = ""
    observacoes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, row: dict) -> "Collaborator":
        return cls(
            colaborador_id=str(row.get("colaborador_id", "")),
            nome=str(row.get("nome", "")),
            cargo=str(row.get("cargo", "")),
            telefone=str(row.get("telefone", "")),
            setor_id=str(row.get("setor_id", "")),
            nome_setor=str(row.get("nome_setor", "")),
            salario_base=float(row.get("salario_base", 0) or 0),
            jornada_id=str(row.get("jornada_id", "")),
            bonus_assiduidade=float(row.get("bonus_assiduidade", 0) or 0),
            bonus_tarefas=float(row.get("bonus_tarefas", 0) or 0),
            status=str(row.get("status", COLLABORATOR_STATUS_ACTIVE)),
            data_cadastro=str(row.get("data_cadastro", "")),
            data_atualizacao=str(row.get("data_atualizacao", "")),
            observacoes=str(row.get("observacoes", "")),
        )
