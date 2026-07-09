"""Aplicacao do icone padrao nas janelas."""

from __future__ import annotations

import ctypes
import os
import tkinter as tk

from app.config.paths import get_icon_path

APP_USER_MODEL_ID = "MiguelOlimpio.ControlePontoTarefas.App"
_APP_ID_SET = False


def set_windows_app_id() -> None:
    """Ajuda o Windows a usar o icone correto na barra de tarefas."""
    global _APP_ID_SET
    if _APP_ID_SET or os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        _APP_ID_SET = True
    except Exception:
        pass


def _apply_iconbitmap(window: tk.Misc, icon_path: str) -> bool:
    applied = False
    for kwargs in ({"default": icon_path}, {}):
        try:
            if kwargs:
                window.iconbitmap(**kwargs)
            else:
                window.iconbitmap(icon_path)
            applied = True
        except Exception:
            pass
    try:
        window.tk.call("wm", "iconbitmap", window._w, icon_path)
        applied = True
    except Exception:
        pass
    return applied


def apply_window_icon(window: tk.Misc) -> None:
    """Aplica icon/icon.ico na janela, sem interromper a abertura se falhar."""
    set_windows_app_id()
    icon_path = get_icon_path()
    if not os.path.isfile(icon_path):
        return
    _apply_iconbitmap(window, icon_path)
    try:
        window.after(50, lambda: _apply_iconbitmap(window, icon_path))
    except Exception:
        pass
