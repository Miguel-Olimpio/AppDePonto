"""Painel administrativo do Bot WhatsApp."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

import ttkbootstrap as ttb

from app.bot.bot_service import BotService
from app.utils.open_file_location import open_path

PRIMARY = "#005CA9"
BACKGROUND = "#F4F8FC"
MUTED = "#64748B"


class BotPanel(ttb.Frame):
    def __init__(self, master: tk.Misc, bot_service: BotService):
        super().__init__(master, style="Content.TFrame")
        self.bot_service = bot_service
        self._destroyed = False
        self._bot_callback = self._on_bot_event
        self.bind("<Destroy>", self._on_destroy, add="+")
        self.status_var = tk.StringVar(value=self.bot_service.status())
        self.session_var = tk.StringVar(value=self._session_text())
        self.queue_var = tk.StringVar(value="Fila: 0 pendentes")
        config = self.bot_service.ensure_default_config()
        self.tasks_enabled_var = tk.BooleanVar(value=_enabled(config.get("lembretes_tarefas_ativos")))
        self.point_enabled_var = tk.BooleanVar(value=_enabled(config.get("lembretes_ponto_ativos")))
        self.start_minutes_var = tk.StringVar(value=str(config.get("minutos_antes_inicio", "0")))
        self.tolerance_minutes_var = tk.StringVar(value=str(config.get("minutos_antes_tolerancia", "0")))
        self.interval_var = tk.StringVar(value=str(config.get("intervalo_verificacao_segundos", "60")))
        self.test_phone_var = tk.StringVar()
        self.test_message_var = tk.StringVar(value="Olá. Esta é uma mensagem de teste do AppDePonto.")
        self._qr_image: tk.PhotoImage | None = None
        self._build()
        self.bot_service.attach_callback(self._bot_callback)
        self._load_current_state()
        self._refresh_queue_status()

    def _build(self) -> None:
        header = ttb.Frame(self, style="Content.TFrame")
        header.pack(fill="x", pady=(0, 10))
        ttb.Label(header, text="Bot WhatsApp", font=("Segoe UI", 16, "bold"), foreground="#003F7D", background=BACKGROUND).pack(anchor="w")
        ttb.Label(
            header,
            text="Conecte o WhatsApp pela própria interface do app. A sessão fica salva em data/wwebjs_auth para reutilizar nas próximas aberturas deste computador. Em outro computador, escaneie o QR Code uma vez.",
            foreground=MUTED,
            background=BACKGROUND,
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

        status = ttb.Labelframe(self, text="Conexão", padding=10)
        status.pack(fill="x", pady=(0, 10))
        ttb.Label(status, text="Status:").grid(row=0, column=0, sticky="w")
        ttb.Label(status, textvariable=self.status_var, font=("Segoe UI", 10, "bold"), foreground=PRIMARY).grid(row=0, column=1, sticky="w", padx=(6, 20))
        ttb.Label(status, textvariable=self.session_var, foreground=MUTED).grid(row=0, column=2, sticky="w", padx=(0, 18))
        ttb.Label(status, textvariable=self.queue_var, foreground=MUTED).grid(row=0, column=3, sticky="w", padx=(0, 18))
        ttb.Button(status, text="Iniciar bot", command=self._start_bot, bootstyle="primary").grid(row=0, column=4, padx=(0, 6))
        ttb.Button(status, text="Parar bot", command=self._stop_bot, bootstyle="secondary-outline").grid(row=0, column=5, padx=(0, 6))
        ttb.Button(status, text="Reiniciar conexão", command=self._restart_connection, bootstyle="warning-outline").grid(row=0, column=6, padx=(0, 6))
        ttb.Button(status, text="Limpar sessão", command=self._clear_session, bootstyle="danger-outline").grid(row=0, column=7)
        ttb.Label(
            status,
            text=f"Pasta da sessão: {self.bot_service.session_dir()}",
            foreground=MUTED,
            wraplength=900,
            justify="left",
        ).grid(row=1, column=0, columnspan=8, sticky="w", pady=(8, 0))
        status.columnconfigure(8, weight=1)

        middle = ttb.Frame(self, style="Content.TFrame")
        middle.pack(fill="both", expand=True, pady=(0, 10))
        middle.columnconfigure(0, weight=1)
        middle.columnconfigure(1, weight=1)
        middle.rowconfigure(0, weight=1)

        qr_box = ttb.Labelframe(middle, text="QR Code", padding=10)
        qr_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.qr_label = ttb.Label(qr_box, text="Clique em Iniciar bot. Se já houver sessão salva, o WhatsApp deve reconectar sem QR Code.", anchor="center", justify="center", wraplength=360)
        self.qr_label.pack(fill="both", expand=True)
        self.qr_ascii = tk.Text(qr_box, height=12, wrap="none")
        self.qr_ascii.pack(fill="both", expand=True, pady=(8, 0))
        self.qr_ascii.configure(state="disabled")

        log_box = ttb.Labelframe(middle, text="Logs", padding=8)
        log_box.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        log_actions = ttb.Frame(log_box)
        log_actions.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        ttb.Button(log_actions, text="Copiar logs", command=self._copy_logs, bootstyle="secondary-outline").pack(side="left")
        ttb.Button(log_actions, text="Abrir arquivo de log", command=self._open_log_file, bootstyle="secondary-outline").pack(side="left", padx=(6, 0))
        ttb.Button(log_actions, text="Processar fila agora", command=self._process_queue_now, bootstyle="info-outline").pack(side="left", padx=(6, 0))
        self.log_text = tk.Text(log_box, height=14, wrap="word")
        log_scroll = ttk.Scrollbar(log_box, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.grid(row=1, column=0, sticky="nsew")
        log_scroll.grid(row=1, column=1, sticky="ns")
        log_box.columnconfigure(0, weight=1)
        log_box.rowconfigure(1, weight=1)

        config_box = ttb.Labelframe(self, text="Configurações dos lembretes", padding=10)
        config_box.pack(fill="x", pady=(0, 10))
        ttb.Checkbutton(config_box, text="Ativar lembretes de tarefas", variable=self.tasks_enabled_var).grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttb.Checkbutton(config_box, text="Ativar lembretes de ponto", variable=self.point_enabled_var).grid(row=0, column=1, sticky="w", padx=(0, 12))
        ttb.Label(config_box, text="Min antes início").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttb.Entry(config_box, textvariable=self.start_minutes_var, width=8).grid(row=2, column=0, sticky="w")
        ttb.Label(config_box, text="Min antes tolerância").grid(row=1, column=1, sticky="w", pady=(8, 0))
        ttb.Entry(config_box, textvariable=self.tolerance_minutes_var, width=8).grid(row=2, column=1, sticky="w")
        ttb.Label(config_box, text="Intervalo verificação (s)").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttb.Entry(config_box, textvariable=self.interval_var, width=10).grid(row=2, column=2, sticky="w")
        ttb.Button(config_box, text="Salvar configurações", command=self._save_config, bootstyle="success").grid(row=2, column=3, sticky="e", padx=(12, 0))
        config_box.columnconfigure(4, weight=1)

        test_box = ttb.Labelframe(self, text="Mensagem de teste", padding=10)
        test_box.pack(fill="x")
        ttb.Label(test_box, text="Telefone").grid(row=0, column=0, sticky="w")
        ttb.Entry(test_box, textvariable=self.test_phone_var, width=20).grid(row=1, column=0, sticky="ew", padx=(0, 8))
        ttb.Label(test_box, text="Mensagem").grid(row=0, column=1, sticky="w")
        ttb.Entry(test_box, textvariable=self.test_message_var).grid(row=1, column=1, sticky="ew", padx=(0, 8))
        ttb.Button(test_box, text="Enviar mensagem de teste", command=self._send_test, bootstyle="info").grid(row=1, column=2, sticky="ew")
        test_box.columnconfigure(1, weight=1)

    def _is_alive(self) -> bool:
        if getattr(self, "_destroyed", False):
            return False
        try:
            return bool(self.winfo_exists())
        except tk.TclError:
            return False

    def _on_destroy(self, event) -> None:
        if event.widget is not self:
            return
        self._destroyed = True
        try:
            if getattr(self.bot_service, "_callback", None) == self._bot_callback:
                self.bot_service.attach_callback(None)
        except Exception:
            pass

    def _load_current_state(self) -> None:
        if not self._is_alive():
            return
        self.status_var.set(self.bot_service.status())
        self.session_var.set(self._session_text())
        qr_event = self.bot_service.last_qr_event()
        if qr_event:
            self._render_qr(str(qr_event.get("dataUrl", "")))
            self._set_ascii(str(qr_event.get("ascii", "")))

    def _start_bot(self) -> None:
        try:
            callback = getattr(self, "_bot_callback", self._on_bot_event)
            self.bot_service.start(callback)
            self.session_var.set(self._session_text())
            self._log("Bot iniciado. Se já houver sessão salva, ele tentará reconectar sem QR Code.")
        except Exception as exc:
            self.status_var.set("Erro")
            self._log(f"Erro ao iniciar bot: {exc}")
            messagebox.showerror("Bot WhatsApp", f"Não foi possível iniciar o bot.\n\n{exc}")

    def _stop_bot(self) -> None:
        self.bot_service.stop()
        self.status_var.set(self.bot_service.status())
        self._log("Bot parado.")

    def _restart_connection(self) -> None:
        try:
            callback = getattr(self, "_bot_callback", self._on_bot_event)
            count = self.bot_service.restart_connection(callback)
            self.session_var.set(self._session_text())
            self._log(f"Reinício seguro solicitado. Processos antigos encerrados: {count}. A sessão salva será reaproveitada se ainda for válida.")
        except Exception as exc:
            self.status_var.set("Erro")
            self._log(f"Erro ao reiniciar conexão: {exc}")
            messagebox.showerror("Bot WhatsApp", f"Não foi possível reiniciar a conexão.\n\n{exc}")

    def _clear_session(self) -> None:
        if not messagebox.askyesno("Bot WhatsApp", "Limpar a sessão salva e gerar novo QR Code no próximo login"):
            return
        self.bot_service.clear_session()
        self.status_var.set(self.bot_service.status())
        self.session_var.set(self._session_text())
        self._qr_image = None
        self.qr_label.configure(image="", text="Sessão limpa. Inicie o bot para gerar novo QR Code.")
        self._set_ascii("")

    def _save_config(self) -> None:
        try:
            self.bot_service.save_config(
                {
                    "lembretes_tarefas_ativos": "sim" if self.tasks_enabled_var.get() else "nao",
                    "lembretes_ponto_ativos": "sim" if self.point_enabled_var.get() else "nao",
                    "minutos_antes_inicio": _non_negative_text(self.start_minutes_var.get(), "Minutos antes do início"),
                    "minutos_antes_tolerancia": _non_negative_text(self.tolerance_minutes_var.get(), "Minutos antes da tolerância"),
                    "intervalo_verificacao_segundos": _non_negative_text(self.interval_var.get(), "Intervalo de verificação"),
                }
            )
        except Exception as exc:
            messagebox.showerror("Bot WhatsApp", str(exc))
            return
        self._log("Configurações salvas.")

    def _process_queue_now(self) -> None:
        try:
            processed = self.bot_service.process_message_queue_once()
        except Exception as exc:
            messagebox.showerror("Bot WhatsApp", str(exc))
            return
        self._refresh_queue_status()
        self._log(f"Fila processada. Mensagens encaminhadas ao bot: {len(processed)}.")

    def _send_test(self) -> None:
        try:
            ok = self.bot_service.send_test_message(self.test_phone_var.get(), self.test_message_var.get())
        except Exception as exc:
            messagebox.showerror("Bot WhatsApp", str(exc))
            return
        self._log("Mensagem enviada para o WhatsApp. Aguarde confirmação nos logs." if ok else "Mensagem não enviada. Veja o motivo nos logs.")

    def _on_bot_event(self, event: dict) -> None:
        if not self._is_alive():
            return

        def deliver() -> None:
            if self._is_alive():
                self._handle_bot_event(event)

        try:
            self.after(0, deliver)
        except tk.TclError:
            pass

    def _handle_bot_event(self, event: dict) -> None:
        if not self._is_alive():
            return
        status = event.get("status")
        if status:
            self.status_var.set(str(status))
        if event.get("event") == "qr":
            self._render_qr(str(event.get("dataUrl", "")))
            self._set_ascii(str(event.get("ascii", "")))
        if event.get("event") == "ready":
            self._qr_image = None
            self.qr_label.configure(image="", text="WhatsApp conectado. A sessão ficará salva para as próximas aberturas.")
        if event.get("event") == "send_result":
            self._refresh_queue_status()
            ok = bool(event.get("ok"))
            prefix = "Envio confirmado" if ok else "Falha no envio"
            self._log(f"{prefix}: {event.get('message', '')}")
            return
        message = event.get("message")
        if message:
            self._log(str(message))
        elif event.get("event") and event.get("event") not in {"qr"}:
            self._log(str(event))

    def _render_qr(self, data_url: str) -> None:
        if not self._is_alive() or not hasattr(self, "qr_label"):
            return
        try:
            if not data_url.startswith("data:image"):
                self.qr_label.configure(image="", text="QR Code recebido. Use o texto abaixo se a imagem não carregar.")
                return
            _, b64 = data_url.split(",", 1)
            self._qr_image = tk.PhotoImage(data=b64)
            self.qr_label.configure(image=self._qr_image, text="")
        except tk.TclError:
            pass
        except Exception:
            self._qr_image = None
            try:
                self.qr_label.configure(image="", text="Não foi possível renderizar o QR Code como imagem.")
            except tk.TclError:
                pass

    def _set_ascii(self, value: str) -> None:
        if not self._is_alive() or not hasattr(self, "qr_ascii"):
            return
        try:
            self.qr_ascii.configure(state="normal")
            self.qr_ascii.delete("1.0", "end")
            if value:
                self.qr_ascii.insert("end", value)
            self.qr_ascii.configure(state="disabled")
        except tk.TclError:
            pass

    def _copy_logs(self) -> None:
        text = self.log_text.get("1.0", "end").strip()
        if not text:
            text = self._read_log_file()
        self.clipboard_clear()
        self.clipboard_append(text)
        self._log("Logs copiados para a área de transferência.")

    def _open_log_file(self) -> None:
        path = self.bot_service.log_path()
        if not os.path.isfile(path):
            self._log(f"Arquivo de log ainda não existe: {path}")
            return
        open_path(path)

    def _read_log_file(self) -> str:
        path = self.bot_service.log_path()
        if not os.path.isfile(path):
            return ""
        try:
            return open(path, "r", encoding="utf-8").read()
        except OSError:
            return ""

    def _log(self, message: str) -> None:
        if not self._is_alive() or not hasattr(self, "log_text"):
            return
        try:
            self.log_text.insert("end", f"{message}\n")
            self.log_text.see("end")
        except tk.TclError:
            pass

    def _refresh_queue_status(self) -> None:
        if not self._is_alive():
            return
        try:
            pending = [
                row
                for row in self.bot_service.queued_messages()
                if str(row.get("status", "")).strip().lower() in {"pendente", "erro"}
            ]
        except Exception as exc:
            self.queue_var.set("Fila indisponível")
            if hasattr(self, "log_text"):
                self._log(f"Não foi possível carregar a fila de mensagens: {exc}")
            return
        self.queue_var.set(f"Fila: {len(pending)} pendente(s)")
    def _session_text(self) -> str:
        return "Sessão salva encontrada" if self.bot_service.has_saved_session() else "Sem sessão salva"


def _enabled(value: object) -> bool:
    return str(value or "").strip().lower() in {"sim", "true", "1", "yes", "ativo"}


def _non_negative_text(value: str, label: str) -> str:
    try:
        number = int(float(str(value or "0").replace(",", ".")))
    except ValueError as exc:
        raise ValueError(f"{label} deve ser um número.") from exc
    if number < 0:
        raise ValueError(f"{label} deve ser zero ou positivo.")
    return str(number)
