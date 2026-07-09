"""Servicos de cadastro e consulta de setores."""

from __future__ import annotations

import uuid

from app.models.sector import Sector
from app.repositories.sector_repository import SectorRepository
from app.utils.dates import format_date, format_datetime
from app.utils.formatting import bool_to_excel, clean_text
from app.utils.validators import require_text

DEFAULT_SECTORS = ("Atendimento", "Limpeza", "Cozinha", "Caixa", "Administrativo", "Estoque", "Todos")


class SectorService:
    def __init__(self, repository: SectorRepository | None = None):
        self.repository = repository or SectorRepository()

    def ensure_default_sectors(self) -> None:
        for name in DEFAULT_SECTORS:
            if self.repository.get_by_name(name):
                continue
            self.create_sector(name)

    def create_sector(self, nome: str, descricao: str = "") -> dict:
        name = require_text(nome, "Nome do setor")
        existing = self.repository.get_by_name(name)
        if existing and bool_to_excel(existing.get("active", True)):
            raise ValueError("J? existe um setor ativo com esse nome.")
        sector = Sector(
            setor_id=uuid.uuid4().hex[:12],
            nome=name,
            descricao=clean_text(descricao),
            active=True,
            data_cadastro=format_date(),
            data_atualizacao=format_datetime(),
        )
        return self.repository.add(sector)

    def update_sector(self, setor_id: str, nome: str, descricao: str = "") -> dict:
        name = require_text(nome, "Nome do setor")
        existing = self.repository.get_by_name(name)
        if existing and str(existing.get("setor_id", "")) != str(setor_id) and bool_to_excel(existing.get("active", True)):
            raise ValueError("J? existe outro setor ativo com esse nome.")
        return self.repository.update(
            setor_id,
            {"nome": name, "descricao": clean_text(descricao), "data_atualizacao": format_datetime()},
        )

    def set_active(self, setor_id: str, active: bool) -> dict:
        return self.repository.update(setor_id, {"active": bool(active), "data_atualizacao": format_datetime()})

    def get(self, setor_id: str) -> dict | None:
        return self.repository.get_by_id(setor_id)

    def list_all(self) -> list[dict]:
        return self.repository.list_all()

    def list_active(self) -> list[dict]:
        self.ensure_default_sectors()
        return self.repository.list_active()

    def options(self) -> list[tuple[str, str]]:
        return [(str(row.get("setor_id", "")), str(row.get("nome", ""))) for row in self.list_active()]

    def resolve_sector(self, setor_id: str = "", nome_setor: str = "", setor: str = "") -> dict:
        self.ensure_default_sectors()
        if clean_text(setor_id):
            found = self.repository.get_by_id(clean_text(setor_id))
            if found and bool_to_excel(found.get("active", True)):
                return {"setor_id": str(found.get("setor_id", "")), "nome_setor": str(found.get("nome", ""))}
        name = clean_text(nome_setor) or clean_text(setor)
        if name:
            found = self.repository.get_by_name(name, only_active=True)
            if found:
                return {"setor_id": str(found.get("setor_id", "")), "nome_setor": str(found.get("nome", ""))}
        raise ValueError("Selecione um setor cadastrado.")
