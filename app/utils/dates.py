"""Funcoes de data/hora usadas no dominio e na UI."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from app.config.settings import DATE_FORMAT, DATETIME_FORMAT, TIME_FORMAT, WEEKDAY_NAMES


def now_local() -> datetime:
    return datetime.now()


def format_date(value: date | datetime | str | None = None) -> str:
    if value is None:
        value = date.today()
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime(DATE_FORMAT)
    return str(value)


def format_time(value: time | datetime | str | None = None) -> str:
    if value is None:
        value = datetime.now()
    if isinstance(value, datetime):
        value = value.time()
    if isinstance(value, time):
        return value.strftime(TIME_FORMAT)
    return str(value)


def format_datetime(value: datetime | str | None = None) -> str:
    if value is None:
        value = datetime.now()
    if isinstance(value, datetime):
        return value.strftime(DATETIME_FORMAT)
    return str(value)


def parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return date.today()
    return datetime.strptime(text, DATE_FORMAT).date()


def parse_time(value: Any) -> time:
    if isinstance(value, datetime):
        return value.time().replace(second=0, microsecond=0)
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    text = str(value or "").strip()
    if not text:
        return time(0, 0)
    return datetime.strptime(text, TIME_FORMAT).time()


def parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return datetime.now()
    return datetime.strptime(text, DATETIME_FORMAT)


def combine_date_time(day: date | str, hour: time | str) -> datetime:
    return datetime.combine(parse_date(day), parse_time(hour))


def weekday_name(day: date | datetime | str | None = None) -> str:
    parsed = parse_date(day) if day is not None else date.today()
    return WEEKDAY_NAMES[parsed.weekday()]

