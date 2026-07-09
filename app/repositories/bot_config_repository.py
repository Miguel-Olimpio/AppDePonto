"""Repositorio de configuracoes e lembretes enviados do bot WhatsApp."""

from __future__ import annotations

from app.config.paths import get_bot_config_db_path
from app.config.settings import SHEET_BOT_CONFIG, SHEET_SENT_REMINDERS, SHEET_BOT_QUEUE
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import BOT_CONFIG_HEADERS, BOT_QUEUE_HEADERS, BOT_SHEETS_CONFIG, SENT_REMINDER_HEADERS


class BotConfigRepository:
    def __init__(self, database: ExcelDatabase | None = None):
        self.database = database or ExcelDatabase(
            db_path=get_bot_config_db_path(),
            sheets_config=BOT_SHEETS_CONFIG,
            backup_stem="bot_config",
        )

    def get_config(self) -> dict[str, str]:
        return {str(row.get("chave", "")): str(row.get("valor", "")) for row in self.database.read_sheet(SHEET_BOT_CONFIG)}

    def save_config(self, values: dict[str, object]) -> dict[str, str]:
        current = self.get_config()
        for key, value in values.items():
            current[str(key)] = str(value)
        rows = [{"chave": key, "valor": value} for key, value in sorted(current.items())]
        self.database.write_sheet(SHEET_BOT_CONFIG, BOT_CONFIG_HEADERS, rows)
        return current

    def list_sent_reminders(self) -> list[dict]:
        return self.database.read_sheet(SHEET_SENT_REMINDERS)

    def add_sent_reminder(self, row: dict) -> dict:
        return self.database.append_row(SHEET_SENT_REMINDERS, SENT_REMINDER_HEADERS, row)

    def reminder_exists(self, *, data: str, tipo: str, colaborador_id: str, tarefa_id: str = "", ponto_id: str = "") -> bool:
        for row in self.list_sent_reminders():
            if str(row.get("data") or "") != str(data or ""):
                continue
            if str(row.get("tipo") or "") != str(tipo or ""):
                continue
            if str(row.get("colaborador_id") or "") != str(colaborador_id or ""):
                continue
            if str(row.get("tarefa_id") or "") != str(tarefa_id or ""):
                continue
            if str(row.get("ponto_id") or "") != str(ponto_id or ""):
                continue
            return True
        return False


    def list_message_queue(self) -> list[dict]:
        return self.database.read_sheet(SHEET_BOT_QUEUE)

    def save_message_queue(self, rows: list[dict]) -> None:
        self.database.write_sheet(SHEET_BOT_QUEUE, BOT_QUEUE_HEADERS, rows)

    def add_message(self, row: dict) -> dict:
        return self.database.append_row(SHEET_BOT_QUEUE, BOT_QUEUE_HEADERS, row)

    def update_message(self, mensagem_id: str, updates: dict) -> dict | None:
        rows = self.list_message_queue()
        updated: dict | None = None
        for row in rows:
            if str(row.get("mensagem_id", "")) == str(mensagem_id):
                row.update(updates)
                updated = row
                break
        if updated is not None:
            self.save_message_queue(rows)
        return updated

    def queued_reminder_exists(self, *, data: str, tipo: str, colaborador_id: str, tarefa_id: str = "", ponto_id: str = "") -> bool:
        active_statuses = {"pendente", "enviando", "enviado", "erro"}
        for row in self.list_message_queue():
            if str(row.get("status", "")).strip().lower() not in active_statuses:
                continue
            if str(row.get("data") or "") != str(data or ""):
                continue
            if str(row.get("tipo") or "") != str(tipo or ""):
                continue
            if str(row.get("colaborador_id") or "") != str(colaborador_id or ""):
                continue
            if str(row.get("tarefa_id") or "") != str(tarefa_id or ""):
                continue
            if str(row.get("ponto_id") or "") != str(ponto_id or ""):
                continue
            return True
        return False
