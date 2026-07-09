"""Acesso ao Excel com criacao automatica, migracao simples e gravacao atomica."""

from __future__ import annotations

import os
import shutil
import uuid
import json
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.workbook.workbook import Workbook as WorkbookType
from openpyxl.worksheet.worksheet import Worksheet

from app.config.paths import get_backups_dir, get_data_dir, get_database_path, get_db_version_path
from app.config.settings import BACKUP_STEM
from app.repositories.excel_schema import SHEETS_CONFIG

BACKUP_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
CURRENT_DB_VERSION = "1.0.3"
MAX_BACKUPS_PER_DATABASE = 10
MIN_BACKUP_INTERVAL = timedelta(minutes=10)


class ExcelSaveError(Exception):
    """Erro ao persistir workbook, geralmente por arquivo aberto no Excel."""

    user_message = "Não foi possível salvar. Feche a planilha no Excel e tente novamente."


def _read_sheet_dicts(ws: Worksheet) -> list[dict[str, Any]]:
    if ws.max_row < 1:
        return []
    headers = [str(c.value).strip() for c in ws[1] if c.value is not None]
    if not headers:
        return []
    rows: list[dict[str, Any]] = []
    for values in ws.iter_rows(min_row=2, max_col=len(headers), values_only=True):
        if values is None or all(v is None for v in values):
            continue
        rows.append({headers[idx]: value for idx, value in enumerate(values)})
    return rows


def _write_sheet(ws: Worksheet, headers: list[str], rows: list[dict[str, Any]]) -> None:
    ws.delete_rows(1, ws.max_row)
    ws.append(headers)
    for row in rows:
        ws.append([row.get(header, "") for header in headers])


def _normalize_row(headers: list[str], row: dict[str, Any]) -> dict[str, Any]:
    normalized = {header: "" for header in headers}
    for key, value in row.items():
        if key in normalized:
            normalized[key] = "" if value is None else value
    return normalized


def _merge_headers(current_headers: list[str], expected_headers: list[str]) -> list[str]:
    merged = [header for header in current_headers if header]
    for header in expected_headers:
        if header not in merged:
            merged.append(header)
    return merged


def _backup_timestamp(path: str, stem: str) -> datetime | None:
    name = os.path.basename(path)
    prefix = f"{stem}_backup_"
    suffix = ".xlsx"
    if not (name.startswith(prefix) and name.endswith(suffix)):
        return None
    raw = name[len(prefix) : -len(suffix)]
    try:
        return datetime.strptime(raw, BACKUP_TIMESTAMP_FORMAT)
    except ValueError:
        return None


def _list_backups(folder: str, stem: str) -> list[tuple[datetime, str]]:
    if not os.path.isdir(folder):
        return []
    backups: list[tuple[datetime, str]] = []
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        stamp = _backup_timestamp(path, stem)
        if stamp is not None:
            backups.append((stamp, path))
    backups.sort(key=lambda item: item[0])
    return backups


def _read_db_version() -> dict[str, Any]:
    path = get_db_version_path()
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_db_version(migration_applied: bool = False) -> None:
    path = get_db_version_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    now = datetime.now()
    state = _read_db_version()
    state["version"] = CURRENT_DB_VERSION
    if migration_applied or not state.get("last_migration"):
        state["last_migration"] = now.strftime("%Y-%m-%d")
    state["last_check"] = now.strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)


def _db_version_needs_update() -> bool:
    state = _read_db_version()
    return state.get("version") != CURRENT_DB_VERSION or not state.get("last_migration")


def _is_app_data_workbook(path: str) -> bool:
    try:
        data_dir = os.path.abspath(get_data_dir())
        workbook_path = os.path.abspath(path)
        return os.path.commonpath([data_dir, workbook_path]) == data_dir
    except ValueError:
        return False


class ExcelDatabase:
    def __init__(
        self,
        db_path: str | None = None,
        sheets_config: dict[str, list[str]] | None = None,
        backup_dir: str | None = None,
        backup_stem: str = BACKUP_STEM,
    ):
        self.db_path = db_path or get_database_path()
        self.sheets_config = sheets_config or SHEETS_CONFIG
        self.backup_dir = backup_dir or get_backups_dir()
        self.backup_stem = backup_stem

    def create_database(self) -> None:
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        wb = Workbook()
        first = True
        for sheet_name, headers in self.sheets_config.items():
            ws = wb.active if first else wb.create_sheet(sheet_name)
            ws.title = sheet_name
            ws.append(headers)
            first = False
        self.save_workbook_safe(wb)

    def create_backup(self) -> str | None:
        if not os.path.isfile(self.db_path):
            return None
        os.makedirs(self.backup_dir, exist_ok=True)
        backups = _list_backups(self.backup_dir, self.backup_stem)
        now = datetime.now()
        if backups and now - backups[-1][0] < MIN_BACKUP_INTERVAL:
            self._cleanup_old_backups(backups)
            return None
        stamp = now.strftime(BACKUP_TIMESTAMP_FORMAT)
        dest = os.path.join(self.backup_dir, f"{self.backup_stem}_backup_{stamp}.xlsx")
        shutil.copy2(self.db_path, dest)
        self._cleanup_old_backups(_list_backups(self.backup_dir, self.backup_stem))
        return dest

    def create_structure_backup(self) -> str | None:
        """Copia as planilhas atuais da pasta data antes de migrar schema."""
        if not os.path.isfile(self.db_path):
            return None
        os.makedirs(self.backup_dir, exist_ok=True)
        stamp = datetime.now().strftime(BACKUP_TIMESTAMP_FORMAT)
        base_folder = os.path.join(self.backup_dir, f"backup_{stamp}")
        folder = base_folder
        counter = 1
        while os.path.exists(folder):
            counter += 1
            folder = f"{base_folder}_{counter}"
        os.makedirs(folder, exist_ok=True)
        data_folder = os.path.dirname(self.db_path) or "."
        copied = False
        for name in os.listdir(data_folder):
            source = os.path.join(data_folder, name)
            if not os.path.isfile(source) or not name.lower().endswith(".xlsx"):
                continue
            shutil.copy2(source, os.path.join(folder, name))
            copied = True
        if not copied:
            shutil.copy2(self.db_path, os.path.join(folder, os.path.basename(self.db_path)))
        return folder

    def _cleanup_old_backups(self, backups: list[tuple[datetime, str]] | None = None) -> None:
        items = backups if backups is not None else _list_backups(self.backup_dir, self.backup_stem)
        excess = len(items) - MAX_BACKUPS_PER_DATABASE
        if excess <= 0:
            return
        for _stamp, path in items[:excess]:
            try:
                os.remove(path)
            except OSError:
                pass

    def ensure_database(self) -> None:
        if not os.path.isfile(self.db_path):
            self.create_database()
            if _is_app_data_workbook(self.db_path):
                _write_db_version(migration_applied=True)
            return
        migrated = self.migrate_database()
        if _is_app_data_workbook(self.db_path) and (migrated or _db_version_needs_update()):
            _write_db_version(migration_applied=migrated)

    def migrate_database(self) -> bool:
        wb = self.load_workbook_safe()
        changed = False
        try:
            for sheet_name, headers in self.sheets_config.items():
                if sheet_name not in wb.sheetnames:
                    ws = wb.create_sheet(sheet_name)
                    ws.append(headers)
                    changed = True
                    continue
                ws = wb[sheet_name]
                current_headers = [str(c.value).strip() for c in ws[1] if c.value is not None]
                merged_headers = _merge_headers(current_headers, headers)
                if current_headers != merged_headers:
                    rows = [_normalize_row(merged_headers, row) for row in _read_sheet_dicts(ws)]
                    _write_sheet(ws, merged_headers, rows)
                    changed = True
            if changed:
                self.create_structure_backup()
                self.create_backup()
                self.save_workbook_safe(wb)
            else:
                wb.close()
            return changed
        except Exception:
            wb.close()
            raise

    def load_workbook_safe(self) -> WorkbookType:
        return load_workbook(self.db_path, read_only=False, data_only=False)

    def save_workbook_safe(self, wb: WorkbookType) -> None:
        folder = os.path.dirname(self.db_path) or "."
        os.makedirs(folder, exist_ok=True)
        tmp = os.path.join(folder, f".{os.path.basename(self.db_path)}.{uuid.uuid4().hex}.tmp.xlsx")
        try:
            wb.save(tmp)
            wb.close()
            os.replace(tmp, self.db_path)
        except (PermissionError, OSError) as exc:
            try:
                if os.path.isfile(tmp):
                    os.remove(tmp)
            finally:
                raise ExcelSaveError() from exc

    def read_sheet(self, sheet_name: str) -> list[dict[str, Any]]:
        self.ensure_database()
        wb = self.load_workbook_safe()
        try:
            if sheet_name not in wb.sheetnames:
                return []
            return _read_sheet_dicts(wb[sheet_name])
        finally:
            wb.close()

    def read_sheet_dataframe(self, sheet_name: str) -> pd.DataFrame:
        return pd.DataFrame(self.read_sheet(sheet_name))

    def write_sheet(self, sheet_name: str, headers: list[str], rows: list[dict[str, Any]]) -> None:
        self.ensure_database()
        wb = self.load_workbook_safe()
        try:
            if sheet_name not in wb.sheetnames:
                wb.create_sheet(sheet_name)
            _write_sheet(wb[sheet_name], headers, [_normalize_row(headers, row) for row in rows])
            self.save_workbook_safe(wb)
            self.create_backup()
        except Exception:
            wb.close()
            raise

    def append_row(self, sheet_name: str, headers: list[str], row: dict[str, Any]) -> dict[str, Any]:
        rows = self.read_sheet(sheet_name)
        normalized = _normalize_row(headers, row)
        rows.append(normalized)
        self.write_sheet(sheet_name, headers, rows)
        return normalized

    def sheet_names(self) -> list[str]:
        self.ensure_database()
        wb = self.load_workbook_safe()
        try:
            return list(wb.sheetnames)
        finally:
            wb.close()
