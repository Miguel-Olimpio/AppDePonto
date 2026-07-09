"""Servico de controle do bot WhatsApp e dos lembretes."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Callable

from app.bot.reminder_scheduler import DEFAULT_BOT_CONFIG, ReminderScheduler
from app.bot.whatsapp_bot import WhatsAppBotBridge, normalize_whatsapp_phone
from app.repositories.bot_config_repository import BotConfigRepository
from app.services.collaborator_service import CollaboratorService
from app.services.journey_service import JourneyService
from app.services.task_service import TaskService
from app.services.time_clock_service import TimeClockService
from app.utils.dates import format_datetime, now_local, parse_datetime
from app.utils.formatting import clean_text

BotEventCallback = Callable[[dict], None]


class BotService:
    def __init__(
        self,
        repository: BotConfigRepository,
        collaborator_service: CollaboratorService,
        task_service: TaskService,
        time_clock_service: TimeClockService,
        journey_service: JourneyService,
        bridge: WhatsAppBotBridge | None = None,
    ):
        self.repository = repository
        self.bridge = bridge or WhatsAppBotBridge()
        self.scheduler = ReminderScheduler(
            repository,
            collaborator_service,
            task_service,
            time_clock_service,
            journey_service,
            sender=self.send_message,
        )
        self._scheduler_stop = threading.Event()
        self._scheduler_thread: threading.Thread | None = None
        self._callback: BotEventCallback | None = None
        self._last_qr_event: dict | None = None

    def ensure_default_config(self) -> dict[str, str]:
        return self.scheduler.ensure_default_config()

    def get_config(self) -> dict[str, str]:
        config = dict(DEFAULT_BOT_CONFIG)
        config.update(self.repository.get_config())
        return config

    def save_config(self, values: dict[str, object]) -> dict[str, str]:
        return self.repository.save_config(values)

    def status(self) -> str:
        return self.bridge.status

    def has_saved_session(self) -> bool:
        return self.bridge.has_saved_session()

    def log_path(self) -> str:
        return self.bridge.log_path

    def session_dir(self) -> str:
        return getattr(self.bridge, "session_dir", "")

    def attach_callback(self, callback: BotEventCallback | None) -> None:
        self._callback = callback

    def last_qr_event(self) -> dict | None:
        return dict(self._last_qr_event) if self._last_qr_event else None

    def start(self, callback: BotEventCallback | None = None) -> None:
        self._callback = callback
        self.ensure_default_config()
        self.bridge.start(self._handle_event)
        self._start_scheduler_loop()

    def stop(self) -> None:
        self._stop_scheduler_loop()
        self.bridge.stop()

    def clear_session(self) -> None:
        self._stop_scheduler_loop()
        self.bridge.clear_session()

    def restart_connection(self, callback: BotEventCallback | None = None) -> int:
        if callback:
            self._callback = callback
        self._stop_scheduler_loop()
        count = self.bridge.terminate_stale_processes()
        self.ensure_default_config()
        self.bridge.start(self._handle_event)
        self._start_scheduler_loop()
        return count

    def terminate_stale_processes(self) -> int:
        self._stop_scheduler_loop()
        return self.bridge.terminate_stale_processes()

    def send_message(self, phone: str, message: str, message_id: str = "") -> bool:
        return self.bridge.send_message(phone, message, message_id=message_id)

    def send_test_message(self, phone: str, message: str) -> bool:
        normalized = normalize_whatsapp_phone(phone)
        if not normalized:
            raise ValueError("Informe um telefone válido com DDD.")
        if not clean_text(message):
            raise ValueError("Informe uma mensagem de teste.")
        return self.send_message(normalized, message)

    def notify_time_record(self, record: dict, collaborator: dict) -> dict | None:
        queued = self.scheduler.queue_time_record_confirmation(
            record,
            collaborator,
            bot_connected=self.status() == "Conectado",
        )
        if queued and str(queued.get("status", "")).lower() == "pendente":
            self.process_message_queue_once()
        return queued

    def run_scheduler_once(self, now: datetime | None = None) -> list[dict]:
        return self.scheduler.run_once(now)

    def sent_reminders(self) -> list[dict]:
        return self.repository.list_sent_reminders()

    def queued_messages(self) -> list[dict]:
        return self.repository.list_message_queue()

    def process_message_queue_once(self, now: datetime | None = None) -> list[dict]:
        if self.status() != "Conectado":
            return []
        stamp = now or now_local()
        config = self.get_config()
        limit = _positive_int(config.get("limite_envios_por_ciclo"), 3)
        max_attempts = _positive_int(config.get("max_tentativas_envio"), 3)
        processed: list[dict] = []
        for row in self.repository.list_message_queue():
            if len(processed) >= limit:
                break
            status = clean_text(row.get("status")).lower()
            if status not in {"pendente", "erro"}:
                continue
            attempts = _positive_int(row.get("tentativas"), 0)
            if attempts >= max_attempts:
                continue
            if not _is_due(row.get("proxima_tentativa_em"), stamp):
                continue
            message_id = clean_text(row.get("mensagem_id"))
            if not message_id:
                continue
            attempts += 1
            self.repository.update_message(
                message_id,
                {
                    "status": "enviando",
                    "tentativas": attempts,
                    "ultimo_erro": "",
                    "proxima_tentativa_em": "",
                },
            )
            accepted = self.bridge.send_message(
                clean_text(row.get("telefone")),
                str(row.get("mensagem", "")),
                message_id=message_id,
            )
            if not accepted:
                self._mark_message_failed(message_id, "Bot desconectado ou envio recusado.", attempts, stamp)
            processed.append({**row, "tentativas": attempts})
        return processed

    def _mark_message_failed(self, message_id: str, error: str, attempts: int | None = None, now: datetime | None = None) -> None:
        row = self._find_queue_message(message_id)
        if row is None:
            return
        config = self.get_config()
        max_attempts = _positive_int(config.get("max_tentativas_envio"), 3)
        retry_seconds = max(_positive_int(config.get("intervalo_retry_segundos"), 90), 10)
        current_attempts = _positive_int(row.get("tentativas"), 0) if attempts is None else attempts
        updates = {
            "status": "erro",
            "ultimo_erro": error,
            "observacoes": "Falha no envio. O bot tentará novamente se ainda houver tentativas.",
        }
        if current_attempts < max_attempts:
            updates["proxima_tentativa_em"] = format_datetime((now or now_local()) + timedelta(seconds=retry_seconds))
        else:
            updates["proxima_tentativa_em"] = ""
            updates["observacoes"] = "Falha definitiva após atingir o limite de tentativas."
        self.repository.update_message(message_id, updates)

    def _mark_message_sent(self, message_id: str) -> None:
        row = self._find_queue_message(message_id)
        if row is None:
            return
        self.repository.update_message(
            message_id,
            {
                "status": "enviado",
                "enviado_em": format_datetime(),
                "ultimo_erro": "",
                "proxima_tentativa_em": "",
                "observacoes": "Mensagem enviada com confirmação do WhatsApp Web.",
            },
        )
        self.repository.add_sent_reminder(
            {
                "lembrete_id": message_id,
                "data": row.get("data", ""),
                "tipo": row.get("tipo", ""),
                "colaborador_id": row.get("colaborador_id", ""),
                "nome_colaborador": row.get("nome_colaborador", ""),
                "tarefa_id": row.get("tarefa_id", ""),
                "nome_tarefa": row.get("nome_tarefa", ""),
                "ponto_id": row.get("ponto_id", ""),
                "telefone": row.get("telefone", ""),
                "enviado_em": format_datetime(),
                "status": "enviado",
                "observacoes": "Mensagem enviada pelo Bot WhatsApp.",
            }
        )

    def _find_queue_message(self, message_id: str) -> dict | None:
        for row in self.repository.list_message_queue():
            if str(row.get("mensagem_id", "")) == str(message_id):
                return row
        return None

    def _stop_scheduler_loop(self) -> None:
        self._scheduler_stop.set()
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=1)
        self._scheduler_thread = None

    def _start_scheduler_loop(self) -> None:
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return
        self._scheduler_stop.clear()
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()

    def _scheduler_loop(self) -> None:
        while not self._scheduler_stop.is_set():
            try:
                self.run_scheduler_once()
                self.process_message_queue_once()
            except Exception as exc:
                self._handle_event({"event": "log", "message": f"Erro no agendador: {exc}"})
            interval = _interval_seconds(self.get_config().get("intervalo_verificacao_segundos"))
            self._scheduler_stop.wait(interval)

    def _handle_event(self, event: dict) -> None:
        if event.get("event") == "qr":
            self._last_qr_event = dict(event)
        elif event.get("event") == "ready":
            self._last_qr_event = None
        if event.get("event") == "send_result" and event.get("id"):
            message_id = str(event.get("id"))
            if event.get("ok"):
                self._mark_message_sent(message_id)
            else:
                row = self._find_queue_message(message_id) or {}
                attempts = _positive_int(row.get("tentativas"), 0)
                self._mark_message_failed(message_id, str(event.get("message", "Erro desconhecido.")), attempts)
        if event.get("event") == "ready":
            try:
                self.process_message_queue_once()
            except Exception as exc:
                event = {"event": "log", "message": f"Erro ao processar fila do bot: {exc}"}
        if self._callback:
            self._callback(event)


def _is_due(value: object, now: datetime) -> bool:
    text = clean_text(value)
    if not text:
        return True
    try:
        return parse_datetime(text) <= now
    except Exception:
        return True


def _positive_int(value: object, default: int) -> int:
    try:
        number = int(float(str(value or default).replace(",", ".")))
    except (TypeError, ValueError):
        number = default
    return max(number, 0)


def _interval_seconds(value: object) -> int:
    try:
        number = int(float(str(value or "60").replace(",", ".")))
    except ValueError:
        number = 60
    return max(number, 10)
