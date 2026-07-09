"""Caminhos estaveis para desenvolvimento e PyInstaller."""

from __future__ import annotations

import os
import sys

from app.config.settings import (
    COLLABORATORS_DATABASE_FILENAME,
    DATABASE_FILENAME,
    OCCURRENCES_DATABASE_FILENAME,
    POINT_DATABASE_FILENAME,
    SECTORS_DATABASE_FILENAME,
    TASKS_DATABASE_FILENAME,
    BOT_CONFIG_DATABASE_FILENAME,
    GOALS_DATABASE_FILENAME,
)

_ROOT_OVERRIDE: str | None = None


def set_root_override(path: str | None) -> None:
    """Permite testes com diretorio temporario sem alterar ambiente real."""
    global _ROOT_OVERRIDE
    _ROOT_OVERRIDE = os.path.abspath(path) if path else None


def is_packaged() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_project_root() -> str:
    if _ROOT_OVERRIDE:
        return _ROOT_OVERRIDE
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", ".."))


def get_app_data_dir() -> str:
    if _ROOT_OVERRIDE:
        path = _ROOT_OVERRIDE
    elif is_packaged():
        path = os.path.dirname(os.path.abspath(sys.executable))
    else:
        path = get_project_root()
    os.makedirs(path, exist_ok=True)
    return path


def get_app_base_path() -> str:
    """Pasta base usada por dados, PDFs, backups e icone."""
    return get_app_data_dir()


def get_base_dir() -> str:
    return get_app_base_path()


def _ensure_child(name: str) -> str:
    path = os.path.join(get_base_dir(), name)
    os.makedirs(path, exist_ok=True)
    return path


def get_data_dir() -> str:
    return _ensure_child("data")


def get_pdfs_dir() -> str:
    return _ensure_child("pdfs")


def get_backups_dir() -> str:
    return _ensure_child("backups")


def get_icon_dir() -> str:
    return _ensure_child("icon")


def get_database_path() -> str:
    return os.path.join(get_data_dir(), DATABASE_FILENAME)


def get_colaboradores_db_path() -> str:
    return os.path.join(get_data_dir(), COLLABORATORS_DATABASE_FILENAME)


def get_ponto_db_path() -> str:
    return os.path.join(get_data_dir(), POINT_DATABASE_FILENAME)


def get_tarefas_db_path() -> str:
    return os.path.join(get_data_dir(), TASKS_DATABASE_FILENAME)


def get_ocorrencias_db_path() -> str:
    return os.path.join(get_data_dir(), OCCURRENCES_DATABASE_FILENAME)


def get_setores_db_path() -> str:
    return os.path.join(get_data_dir(), SECTORS_DATABASE_FILENAME)


def get_bot_config_db_path() -> str:
    return os.path.join(get_data_dir(), BOT_CONFIG_DATABASE_FILENAME)


def get_metas_db_path() -> str:
    return os.path.join(get_data_dir(), GOALS_DATABASE_FILENAME)


def get_whatsapp_session_dir() -> str:
    path = os.path.join(get_data_dir(), "wwebjs_auth")
    os.makedirs(path, exist_ok=True)
    return path


def get_db_version_path() -> str:
    return os.path.join(get_data_dir(), "db_version.json")


def ensure_app_directories() -> None:
    """Cria as pastas esperadas tanto em desenvolvimento quanto no executavel."""
    get_data_dir()
    get_pdfs_dir()
    get_backups_dir()
    get_icon_dir()
    get_whatsapp_session_dir()


def get_bot_log_path() -> str:
    return os.path.join(get_data_dir(), "bot_whatsapp.log")


def get_bot_node_dir() -> str:
    roots: list[str] = []
    if is_packaged():
        roots.append(os.path.dirname(os.path.abspath(sys.executable)))
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            roots.append(str(bundle_dir))
    roots.append(get_project_root())
    for root in roots:
        candidate = os.path.join(root, "bot_node")
        if os.path.isdir(candidate):
            return candidate
    return os.path.join(roots[0], "bot_node")


def get_icon_path() -> str:
    roots: list[str] = []
    if is_packaged():
        roots.append(os.path.dirname(os.path.abspath(sys.executable)))
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            roots.append(str(bundle_dir))
    roots.append(get_project_root())

    candidates = [os.path.join(root, "icon", "icon.ico") for root in roots]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return candidates[0]
