"""Bridge entre o app Python e whatsapp-web.js em processo Node."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from typing import Callable

from app.config.paths import get_bot_log_path, get_bot_node_dir, get_whatsapp_session_dir
from app.utils.dates import format_datetime
from app.utils.formatting import clean_text

BotEventCallback = Callable[[dict], None]


def _is_browser_lock_error(value: object) -> bool:
    text = str(value or "").lower()
    return "browser is already running" in text or ("userdata" in text and "running browser" in text)


def _subprocess_creationflags() -> int:
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        return subprocess.CREATE_NO_WINDOW
    return 0


def _node_executable(node_dir: str = "") -> str | None:
    if node_dir:
        local = os.path.join(node_dir, "runtime", "node", "node.exe")
        if os.path.isfile(local):
            return local
    return shutil.which("node") or shutil.which("node.exe")


def _packaged_chromium_path(node_dir: str) -> str:
    candidates = [
        os.path.join(node_dir, "chromium", "chrome-win64", "chrome.exe"),
        os.path.join(node_dir, "chromium", "chrome-win", "chrome.exe"),
        os.path.join(node_dir, "chromium", "chrome.exe"),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return ""


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def normalize_whatsapp_phone(value: object, default_country_code: str = "55") -> str:
    digits = "".join(ch for ch in clean_text(value) if ch.isdigit())
    if not digits:
        return ""
    if digits.startswith(default_country_code):
        local = digits[len(default_country_code):]
        return digits if len(local) in {10, 11} else ""
    return f"{default_country_code}{digits}" if len(digits) in {10, 11} else ""


class WhatsAppBotBridge:
    def __init__(self, node_dir: str | None = None, session_dir: str | None = None):
        self.node_dir = node_dir or get_bot_node_dir()
        self.session_dir = session_dir or get_whatsapp_session_dir()
        self.log_path = get_bot_log_path()
        self.process: subprocess.Popen | None = None
        self.status = "Desconectado"
        self.ready = False
        self._callback: BotEventCallback | None = None
        self._reader_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._run_id = 0

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def has_saved_session(self) -> bool:
        if not os.path.isdir(self.session_dir):
            return False
        for root, dirs, files in os.walk(self.session_dir):
            if files or dirs:
                return True
        return False

    def start(self, callback: BotEventCallback | None = None) -> None:
        self._callback = callback
        if self.is_running:
            self._emit({"event": "log", "message": "Bot já está em execução."})
            return
        script = os.path.join(self.node_dir, "main.js")
        if not os.path.isfile(script):
            message = f"Arquivo do bot Node não encontrado: {script}"
            self._emit_startup_error(message)
            raise FileNotFoundError(message)
        node_exe = _node_executable(self.node_dir)
        if not node_exe:
            message = (
                "Node.js não encontrado. Instale o Node.js LTS e mantenha o comando "
                "'node' disponível no PATH para usar o Bot WhatsApp."
            )
            self._emit_startup_error(message)
            raise RuntimeError(message)
        package_json = os.path.join(self.node_dir, "package.json")
        node_modules = os.path.join(self.node_dir, "node_modules")
        if not os.path.isfile(package_json) or not os.path.isdir(node_modules):
            message = (
                "Dependências Node do Bot WhatsApp não encontradas. Execute 'npm install' "
                "na pasta bot_node ou empacote a pasta node_modules junto com o aplicativo."
            )
            self._emit_startup_error(message)
            raise RuntimeError(message)
        if not _packaged_chromium_path(self.node_dir):
            message = (
                "Chromium empacotado do Bot WhatsApp não encontrado. "
                "Reinstale o aplicativo ou verifique a pasta bot_node/chromium."
            )
            self._emit_startup_error(message)
            raise RuntimeError(message)
        os.makedirs(self.session_dir, exist_ok=True)
        self.ready = False
        self._run_id += 1
        run_id = self._run_id
        self.process = subprocess.Popen(
            [node_exe, script, "--auth-dir", self.session_dir],
            cwd=self.node_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            bufsize=1,
            creationflags=_subprocess_creationflags(),
        )
        self.status = "Reconectando sessão" if self.has_saved_session() else "Aguardando QR Code"
        self._emit({"event": "status", "status": self.status})
        self._reader_thread = threading.Thread(target=self._read_stdout, args=(self.process, run_id), daemon=True)
        self._reader_thread.start()

    def _emit_startup_error(self, message: str) -> None:
        self.ready = False
        self.status = "Erro"
        self._emit({"event": "status", "status": self.status})
        self._emit({"event": "error", "message": message})

    def stop(self) -> None:
        process = self.process
        if not process:
            self.ready = False
            self.status = "Desconectado"
            self._emit({"event": "status", "status": self.status})
            return
        self._run_id += 1
        try:
            self._write({"action": "stop"})
            process.wait(timeout=8)
        except Exception:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        self.process = None
        self.ready = False
        self.status = "Desconectado"
        self._emit({"event": "status", "status": self.status})

    def terminate_stale_processes(self) -> int:
        if self.is_running:
            self.stop()
        count = self._terminate_windows_session_processes()
        if count:
            self._emit({"event": "log", "message": f"Processos antigos do WhatsApp encerrados: {count}."})
        else:
            self._emit({"event": "log", "message": "Nenhum processo antigo do WhatsApp foi encontrado."})
        return count

    def clear_session(self) -> None:
        self.stop()
        self.terminate_stale_processes()
        if os.path.isdir(self.session_dir):
            shutil.rmtree(self.session_dir, ignore_errors=True)
        os.makedirs(self.session_dir, exist_ok=True)
        self._emit({"event": "log", "message": "Sessão local do WhatsApp removida."})

    def send_message(self, phone: str, message: str, message_id: str = "") -> bool:
        phone = normalize_whatsapp_phone(phone)
        if not phone or not clean_text(message):
            self._emit({"event": "send_result", "ok": False, "message": "Telefone ou mensagem inválidos."})
            return False
        if not self.is_running:
            self._emit({"event": "send_result", "id": message_id, "ok": False, "message": "Bot desligado. Clique em Iniciar bot."})
            return False
        if not self.ready:
            message = "WhatsApp ainda não está conectado. Aguarde o status Conectado."
            if self.status == "Autenticado":
                message = "WhatsApp autenticado, mas ainda carregando. Aguarde o status Conectado."
            self._emit({"event": "send_result", "id": message_id, "ok": False, "message": message})
            return False
        self._write({"action": "send", "id": message_id, "phone": phone, "message": message})
        return True

    def _terminate_windows_session_processes(self) -> int:
        if os.name != "nt":
            return 0
        targets = [
            os.path.abspath(self.session_dir).lower(),
            os.path.abspath(self.node_dir).lower(),
        ]
        targets_literal = ",".join(_ps_quote(target) for target in targets if target)
        script = f"""
$targets = @({targets_literal})
$names = @('node.exe','chrome.exe','chromium.exe','msedge.exe')
$count = 0
Get-CimInstance Win32_Process | Where-Object {{
    $name = ([string]$_.Name).ToLowerInvariant()
    if ($names -notcontains $name) {{ return $false }}
    $cmd = [string]$_.CommandLine
    if (-not $cmd) {{ return $false }}
    $lower = $cmd.ToLowerInvariant()
    foreach ($target in $targets) {{
        if ($target -and $lower.Contains($target)) {{ return $true }}
    }}
    return $false
}} | ForEach-Object {{
    try {{
        Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
        $count += 1
    }} catch {{}}
}}
Write-Output $count
"""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=15,
                creationflags=_subprocess_creationflags(),
            )
        except Exception as exc:
            self._emit({"event": "log", "message": f"Não foi possível verificar processos antigos do WhatsApp: {exc}"})
            return 0
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "").strip()
            if message:
                self._emit({"event": "log", "message": f"Falha ao encerrar processos antigos: {message}"})
            return 0
        for token in reversed((result.stdout or "").split()):
            try:
                return int(token)
            except ValueError:
                continue
        return 0

    def _read_stdout(self, process: subprocess.Popen, run_id: int) -> None:
        if not process or not process.stdout:
            return
        for line in process.stdout:
            if run_id != self._run_id:
                continue
            text = line.strip()
            if not text:
                continue
            try:
                event = json.loads(text)
            except json.JSONDecodeError:
                event = {"event": "log", "message": text}
            if event.get("event") in {"error", "log"} and _is_browser_lock_error(event.get("message")):
                event["message"] = (
                    "Existe uma sessão do WhatsApp ainda aberta usando esta pasta. "
                    "Feche outras janelas/processos do bot ou use Limpar sessão para gerar um novo QR Code."
                )
            if event.get("event") == "ready":
                self.ready = True
                self.status = "Conectado"
                self._emit({"event": "status", "status": self.status})
            elif event.get("event") == "qr":
                self.ready = False
                self.status = "Aguardando QR Code"
                self._emit({"event": "status", "status": self.status})
            elif event.get("event") == "authenticated":
                self.ready = False
                self.status = "Autenticado"
                self._emit({"event": "status", "status": self.status})
            elif event.get("event") == "error":
                self.ready = False
                self.status = "Erro"
                self._emit({"event": "status", "status": self.status})
            elif event.get("event") == "status" and event.get("status"):
                self.status = str(event.get("status"))
                self.ready = self.status == "Conectado"
            self._emit(event)
        if run_id == self._run_id:
            self.ready = False
            if self.status != "Erro":
                self.status = "Desconectado"
                self._emit({"event": "status", "status": self.status})

    def _write(self, payload: dict) -> None:
        with self._lock:
            if not self.process or not self.process.stdin:
                return
            self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self.process.stdin.flush()

    def _emit(self, event: dict) -> None:
        self._write_log(event)
        if self._callback:
            self._callback(event)

    def _write_log(self, event: dict) -> None:
        message = event.get("message") or json.dumps(event, ensure_ascii=False)
        try:
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as file:
                file.write(f"[{format_datetime()}] {message}\n")
        except OSError:
            pass
