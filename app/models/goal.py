"""Modelo de meta mensal para bonus gerencial."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class Goal:
    meta_id: str
    nome_meta: str
    tipo_meta: str
    descricao: str = ""
    periodo_mes: str = ""
    valor_bonus: float = 0.0
    valor_meta: float = 0.0
    valor_realizado: float = 0.0
    atingida: bool = False
    colaborador_id: str = ""
    nome_colaborador: str = ""
    active: bool = True
    data_cadastro: str = ""
    data_atualizacao: str = ""
    observacoes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, row: dict) -> "Goal":
        return cls(
            meta_id=str(row.get("meta_id", "")),
            nome_meta=str(row.get("nome_meta", "")),
            tipo_meta=str(row.get("tipo_meta", "")),
            descricao=str(row.get("descricao", "")),
            periodo_mes=str(row.get("periodo_mes", "")),
            valor_bonus=float(row.get("valor_bonus", 0) or 0),
            valor_meta=float(row.get("valor_meta", 0) or 0),
            valor_realizado=float(row.get("valor_realizado", 0) or 0),
            atingida=str(row.get("atingida", "")).lower() in {"true", "1", "sim", "yes"},
            colaborador_id=str(row.get("colaborador_id", "")),
            nome_colaborador=str(row.get("nome_colaborador", "")),
            active=str(row.get("active", "true")).lower() not in {"false", "0", "nao", "não", "inativo"},
            data_cadastro=str(row.get("data_cadastro", "")),
            data_atualizacao=str(row.get("data_atualizacao", "")),
            observacoes=str(row.get("observacoes", "")),
        )
