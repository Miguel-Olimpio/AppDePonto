"""Servicos de metas e bonus mensal por meta."""

from __future__ import annotations

import uuid
from typing import Any

from app.config.settings import GOAL_TYPE_COLLECTIVE, GOAL_TYPE_INDIVIDUAL, GOAL_TYPES
from app.models.goal import Goal
from app.repositories.collaborator_repository import CollaboratorRepository
from app.repositories.goal_repository import GoalRepository
from app.utils.dates import format_date, format_datetime
from app.utils.formatting import bool_to_excel, clean_text
from app.utils.validators import require_text, validate_non_negative_float


class GoalService:
    def __init__(
        self,
        repository: GoalRepository | None = None,
        collaborator_repository: CollaboratorRepository | None = None,
    ):
        self.repository = repository or GoalRepository()
        self.collaborator_repository = collaborator_repository or CollaboratorRepository()

    def create_goal(
        self,
        nome_meta: str,
        tipo_meta: str,
        periodo_mes: str,
        valor_bonus=0,
        valor_meta=0,
        valor_realizado=0,
        atingida=False,
        colaborador_id: str = "",
        nome_colaborador: str = "",
        descricao: str = "",
        observacoes: str = "",
        **_ignored,
    ) -> dict:
        payload = self._validate_payload(
            nome_meta=nome_meta,
            tipo_meta=tipo_meta,
            periodo_mes=periodo_mes,
            valor_bonus=valor_bonus,
            valor_meta=valor_meta,
            valor_realizado=valor_realizado,
            atingida=atingida,
            colaborador_id=colaborador_id,
            nome_colaborador=nome_colaborador,
            descricao=descricao,
            observacoes=observacoes,
        )
        goal = Goal(
            meta_id=uuid.uuid4().hex[:12],
            active=True,
            data_cadastro=format_date(),
            data_atualizacao=format_datetime(),
            **payload,
        )
        return self.repository.add(goal)

    def update_goal(self, meta_id: str, **changes) -> dict:
        current = self.repository.get_by_id(meta_id)
        if not current:
            raise KeyError("Meta nao encontrada.")
        merged = dict(current)
        merged.update(changes)
        payload = self._validate_payload(
            nome_meta=merged.get("nome_meta", ""),
            tipo_meta=merged.get("tipo_meta", ""),
            periodo_mes=merged.get("periodo_mes", ""),
            valor_bonus=merged.get("valor_bonus", 0),
            valor_meta=merged.get("valor_meta", 0),
            valor_realizado=merged.get("valor_realizado", 0),
            atingida=merged.get("atingida", False),
            colaborador_id=merged.get("colaborador_id", ""),
            nome_colaborador=merged.get("nome_colaborador", ""),
            descricao=merged.get("descricao", ""),
            observacoes=merged.get("observacoes", ""),
        )
        payload["data_atualizacao"] = format_datetime()
        return self.repository.update(meta_id, payload)

    def set_active(self, meta_id: str, active: bool) -> dict:
        return self.repository.update(meta_id, {"active": bool(active), "data_atualizacao": format_datetime()})

    def get(self, meta_id: str) -> dict | None:
        return self.repository.get_by_id(meta_id)

    def list_all(self) -> list[dict]:
        return [self._normalize_row(row) for row in self.repository.list_all()]

    def list_active(self) -> list[dict]:
        return [self._normalize_row(row) for row in self.repository.list_active()]

    def list_for_month(self, periodo_mes: str, *, only_active: bool = True) -> list[dict]:
        period = validate_month_text(periodo_mes)
        rows = self.list_active() if only_active else self.list_all()
        return [row for row in rows if str(row.get("periodo_mes", "")) == period]

    def calculate_bonus_for_collaborator(self, collaborator: dict, periodo_mes: str) -> dict:
        collaborator_id = str(collaborator.get("colaborador_id", ""))
        achieved_collective: list[dict] = []
        achieved_individual: list[dict] = []
        not_achieved: list[dict] = []
        for goal in self.list_for_month(periodo_mes):
            goal_type = str(goal.get("tipo_meta", ""))
            is_achieved = bool_to_excel(goal.get("atingida", False))
            applies = goal_type == GOAL_TYPE_COLLECTIVE or (
                goal_type == GOAL_TYPE_INDIVIDUAL and str(goal.get("colaborador_id", "")) == collaborator_id
            )
            if not applies:
                continue
            if is_achieved and goal_type == GOAL_TYPE_COLLECTIVE:
                achieved_collective.append(goal)
            elif is_achieved and goal_type == GOAL_TYPE_INDIVIDUAL:
                achieved_individual.append(goal)
            else:
                not_achieved.append(goal)
        applied = sum(_to_float(row.get("valor_bonus")) for row in achieved_collective + achieved_individual)
        details = []
        for row in achieved_collective + achieved_individual:
            details.append(self._detail(row, applied=True))
        for row in not_achieved:
            details.append(self._detail(row, applied=False))
        return {
            "bonus_meta_aplicado": applied,
            "metas_coletivas_atingidas": achieved_collective,
            "metas_individuais_atingidas": achieved_individual,
            "metas_nao_atingidas": not_achieved,
            "metas_detalhes": details,
            "mensagem_metas": "Bonus por meta aplicado." if applied else "Nenhum bonus por meta aplicado no periodo.",
        }

    def _detail(self, row: dict, *, applied: bool) -> dict:
        return {
            "data": str(row.get("periodo_mes", "")),
            "tipo": f"meta {row.get('tipo_meta', '')}",
            "nome": str(row.get("nome_meta", "")),
            "descricao": str(row.get("descricao", "")),
            "valor_bonus": _to_float(row.get("valor_bonus")),
            "atingida": bool_to_excel(row.get("atingida", False)),
            "impacto": "Soma bonus por meta." if applied else "Nao soma bonus por meta.",
        }

    def _validate_payload(self, **data) -> dict:
        goal_type = clean_text(data.get("tipo_meta")).lower()
        if goal_type not in GOAL_TYPES:
            raise ValueError("Tipo de meta deve ser coletiva ou individual.")
        period = validate_month_text(str(data.get("periodo_mes", "")))
        collaborator_id = clean_text(data.get("colaborador_id"))
        collaborator_name = clean_text(data.get("nome_colaborador"))
        if goal_type == GOAL_TYPE_INDIVIDUAL:
            collaborator = self._resolve_collaborator(collaborator_id, collaborator_name)
            collaborator_id = str(collaborator.get("colaborador_id", ""))
            collaborator_name = str(collaborator.get("nome", ""))
        else:
            collaborator_id = ""
            collaborator_name = ""
        return {
            "nome_meta": require_text(data.get("nome_meta", ""), "Nome da meta"),
            "tipo_meta": goal_type,
            "descricao": clean_text(data.get("descricao")),
            "periodo_mes": period,
            "valor_bonus": validate_non_negative_float(data.get("valor_bonus", 0), "Valor do bonus"),
            "valor_meta": validate_non_negative_float(data.get("valor_meta", 0), "Valor da meta"),
            "valor_realizado": validate_non_negative_float(data.get("valor_realizado", 0), "Valor realizado"),
            "atingida": _to_bool(data.get("atingida", False)),
            "colaborador_id": collaborator_id,
            "nome_colaborador": collaborator_name,
            "observacoes": clean_text(data.get("observacoes")),
        }

    def _resolve_collaborator(self, colaborador_id: str, nome_colaborador: str) -> dict:
        if clean_text(colaborador_id):
            found = self.collaborator_repository.get_by_id(clean_text(colaborador_id))
            if found:
                return found
        target = clean_text(nome_colaborador).lower()
        if target:
            for row in self.collaborator_repository.list_active():
                if clean_text(row.get("nome")).lower() == target:
                    return row
        raise ValueError("Selecione um colaborador para meta individual.")

    @staticmethod
    def _normalize_row(row: dict) -> dict:
        normalized = dict(row)
        normalized["atingida"] = bool_to_excel(normalized.get("atingida", False))
        normalized["active"] = bool_to_excel(normalized.get("active", True))
        return normalized


def validate_month_text(value: str) -> str:
    text = clean_text(value)
    parts = text.split("/")
    if len(parts) != 2:
        raise ValueError("Informe o mes no formato MM/AAAA.")
    try:
        month = int(parts[0])
        year = int(parts[1])
    except ValueError as exc:
        raise ValueError("Informe o mes no formato MM/AAAA.") from exc
    if month < 1 or month > 12 or year < 1900:
        raise ValueError("Informe um mes/ano valido.")
    return f"{month:02d}/{year}"


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return clean_text(value).lower() in {"sim", "true", "1", "yes", "atingida"}


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = clean_text(value).replace("R$", "").replace(" ", "")
    if text == "":
        return 0.0
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0
