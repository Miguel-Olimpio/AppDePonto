"""Helpers para duracoes de jornada."""

from __future__ import annotations

from app.utils.formatting import clean_text


def parse_hours(value, field_name: str) -> float:
    text = clean_text(value).lower().replace("horas", "").replace("hora", "").replace("h", "").strip()
    if text == "":
        return 0.0
    if ":" in text:
        parts = text.split(":")
        if len(parts) != 2:
            raise ValueError(f"{field_name} deve ser informado em horas.")
        try:
            hours = int(parts[0])
            minutes = int(parts[1])
        except ValueError as exc:
            raise ValueError(f"{field_name} deve ser informado em horas.") from exc
        if hours < 0 or minutes < 0 or minutes >= 60:
            raise ValueError(f"{field_name} deve ser zero ou positivo.")
        return hours + minutes / 60
    try:
        number = float(text.replace(",", "."))
    except ValueError as exc:
        raise ValueError(f"{field_name} deve ser informado em horas.") from exc
    if number < 0:
        raise ValueError(f"{field_name} deve ser zero ou positivo.")
    return number


def parse_minutes(value, field_name: str) -> int:
    text = clean_text(value).lower().replace("minutos", "").replace("minuto", "").replace("min", "").strip()
    if text == "":
        return 0
    if text.endswith("h"):
        return int(round(parse_hours(text, field_name) * 60))
    if ":" in text:
        return int(round(parse_hours(text, field_name) * 60))
    try:
        number = float(text.replace(",", "."))
    except ValueError as exc:
        raise ValueError(f"{field_name} deve ser informado em minutos.") from exc
    if number < 0:
        raise ValueError(f"{field_name} deve ser zero ou positivo.")
    return int(round(number))
