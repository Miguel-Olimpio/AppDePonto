"""Validadores pequenos para formularios e services."""

from __future__ import annotations

from app.utils.dates import parse_time
from app.utils.formatting import clean_text


class ValidationError(ValueError):
    """Erro de validacao com mensagem pronta para usuario."""


def require_text(value: str, field_name: str) -> str:
    text = clean_text(value)
    if not text:
        raise ValidationError(f"{field_name} é obrigatório.")
    return text


def validate_time_text(value: str, field_name: str) -> str:
    text = require_text(value, field_name)
    try:
        parse_time(text)
    except ValueError as exc:
        raise ValidationError(f"{field_name} deve estar no formato HH:MM.") from exc
    return text


def validate_non_negative_int(value, field_name: str) -> int:
    text = clean_text(value)
    if text == "":
        return 0
    try:
        number = int(text)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} deve ser um número inteiro.") from exc
    if number < 0:
        raise ValidationError(f"{field_name} deve ser zero ou positivo.")
    return number


def validate_non_negative_float(value, field_name: str) -> float:
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = clean_text(value).replace("R$", "").replace(" ", "")
        if text == "":
            return 0.0
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        try:
            number = float(text)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{field_name} deve ser um n?mero.") from exc
    if number < 0:
        raise ValidationError(f"{field_name} deve ser zero ou positivo.")
    return number
