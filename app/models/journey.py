"""Modelo de jornada/escala de trabalho."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.config.settings import SCALE_TYPE_WEEKLY


@dataclass(slots=True)
class Journey:
    jornada_id: str
    nome: str
    tipo_escala: str = SCALE_TYPE_WEEKLY
    entrada: str = ""
    saida: str = ""
    carga_horaria: float = 0.0
    tempo_intervalo: int = 0
    tolerancia_minutos: int = 0
    dias_semana: str = "todos"
    descricao_escala: str = ""
    horas_trabalho: int = 0
    horas_descanso: int = 0
    data_inicio_escala: str = ""
    horario_inicio_escala: str = ""
    active: bool = True
    data_cadastro: str = ""
    data_atualizacao: str = ""
    observacoes: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["tipo_jornada"] = data["tipo_escala"]
        return data

    @classmethod
    def from_dict(cls, row: dict) -> "Journey":
        return cls(
            jornada_id=str(row.get("jornada_id", "")),
            nome=str(row.get("nome", "")),
            tipo_escala=str(row.get("tipo_jornada") or row.get("tipo_escala") or SCALE_TYPE_WEEKLY),
            entrada=str(row.get("entrada", "")),
            saida=str(row.get("saida", "")),
            carga_horaria=float(row.get("carga_horaria", 0) or 0),
            tempo_intervalo=int(row.get("tempo_intervalo", 0) or 0),
            tolerancia_minutos=int(row.get("tolerancia_minutos", 0) or 0),
            dias_semana=str(row.get("dias_semana", "todos") or "todos"),
            descricao_escala=str(row.get("descricao_escala", "")),
            horas_trabalho=int(row.get("horas_trabalho", 0) or 0),
            horas_descanso=int(row.get("horas_descanso", 0) or 0),
            data_inicio_escala=str(row.get("data_inicio_escala", "")),
            horario_inicio_escala=str(row.get("horario_inicio_escala", "")),
            active=bool(row.get("active", True)),
            data_cadastro=str(row.get("data_cadastro", "")),
            data_atualizacao=str(row.get("data_atualizacao", "")),
            observacoes=str(row.get("observacoes", "")),
        )
