"""Formatacao simples para textos de tela e Excel."""

from __future__ import annotations

import re
from typing import Any


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_key(value: Any) -> str:
    text = clean_text(value).lower()
    return re.sub(r"\s+", " ", text)


def bool_to_excel(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = clean_text(value).lower()
    if text in {"false", "0", "nao", "não", "inativo"}:
        return False
    return True


def yes_no(value: Any) -> str:
    return "Sim" if bool_to_excel(value) else "Não"

