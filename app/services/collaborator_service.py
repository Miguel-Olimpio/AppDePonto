"""Servicos de cadastro de colaboradores."""

from __future__ import annotations

import uuid

from app.config.settings import COLLABORATOR_STATUS_ACTIVE, COLLABORATOR_STATUS_INACTIVE
from app.models.collaborator import Collaborator
from app.repositories.collaborator_repository import CollaboratorRepository
from app.services.sector_service import SectorService
from app.utils.dates import format_date, format_datetime
from app.utils.formatting import clean_text
from app.utils.validators import require_text, validate_non_negative_float


class CollaboratorService:
    def __init__(self, repository: CollaboratorRepository | None = None, sector_service: SectorService | None = None):
        self.repository = repository or CollaboratorRepository()
        self.sector_service = sector_service or SectorService()

    def create_collaborator(
        self,
        nome: str,
        cargo: str = "",
        telefone: str = "",
        setor_id: str = "",
        nome_setor: str = "",
        setor: str = "",
        observacoes: str = "",
        salario_base=0,
        jornada_id: str = "",
        bonus_assiduidade=0,
        bonus_tarefas=0,
    ) -> dict:
        sector = self.sector_service.resolve_sector(setor_id=setor_id, nome_setor=nome_setor, setor=setor)
        collaborator = Collaborator(
            colaborador_id=uuid.uuid4().hex[:12],
            nome=require_text(nome, "Nome"),
            cargo=clean_text(cargo),
            telefone=clean_text(telefone),
            setor_id=sector["setor_id"],
            nome_setor=sector["nome_setor"],
            salario_base=validate_non_negative_float(salario_base, "Salario base"),
            jornada_id=clean_text(jornada_id),
            bonus_assiduidade=validate_non_negative_float(bonus_assiduidade, "Bonus assiduidade"),
            bonus_tarefas=validate_non_negative_float(bonus_tarefas, "Bonus tarefas"),
            status=COLLABORATOR_STATUS_ACTIVE,
            data_cadastro=format_date(),
            data_atualizacao=format_datetime(),
            observacoes=clean_text(observacoes),
        )
        return self.repository.add(collaborator)

    def update_collaborator(self, colaborador_id: str, **changes) -> dict:
        if "setor_label" in changes:
            changes["nome_setor"] = changes.pop("setor_label")
        if "setor" in changes and not clean_text(changes.get("nome_setor")):
            changes["nome_setor"] = changes.pop("setor")
        if "nome" in changes:
            changes["nome"] = require_text(changes["nome"], "Nome")
        if "setor_id" in changes or "nome_setor" in changes:
            sector = self.sector_service.resolve_sector(
                setor_id=str(changes.get("setor_id", "")),
                nome_setor=str(changes.get("nome_setor", "")),
            )
            changes["setor_id"] = sector["setor_id"]
            changes["nome_setor"] = sector["nome_setor"]
        for key in ("cargo", "telefone", "observacoes", "jornada_id"):
            if key in changes:
                changes[key] = clean_text(changes[key])
        for key, label in (
            ("salario_base", "Salario base"),
            ("bonus_assiduidade", "Bonus assiduidade"),
            ("bonus_tarefas", "Bonus tarefas"),
        ):
            if key in changes:
                changes[key] = validate_non_negative_float(changes[key], label)
        changes["data_atualizacao"] = format_datetime()
        return self.repository.update(colaborador_id, changes)

    def set_active(self, colaborador_id: str, active: bool) -> dict:
        status = COLLABORATOR_STATUS_ACTIVE if active else COLLABORATOR_STATUS_INACTIVE
        return self.repository.update(colaborador_id, {"status": status, "data_atualizacao": format_datetime()})

    def get(self, colaborador_id: str) -> dict | None:
        return self.repository.get_by_id(colaborador_id)

    def list_all(self) -> list[dict]:
        return self.repository.list_all()

    def list_active(self) -> list[dict]:
        return self.repository.list_active()

    def sector_names(self, include_inactive: bool = False) -> list[str]:
        rows = self.sector_service.list_all() if include_inactive else self.sector_service.list_active()
        return [str(row.get("nome", "")) for row in rows if clean_text(row.get("nome"))]
