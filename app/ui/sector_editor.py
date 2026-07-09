"""Modal de cadastro/edicao de setores."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttb

from app.repositories.excel_database import ExcelSaveError
from app.ui.window_icon import apply_window_icon


class SectorEditor(tk.Toplevel):
    def __init__(self, master: tk.Misc, on_save, initial: dict | None = None):
        super().__init__(master)
        self.title("Setor")
        self.geometry("560x420")
        self.minsize(460, 320)
        self.resizable(True, True)
        apply_window_icon(self)
        self.transient(master.winfo_toplevel())
        self.grab_set()
        self._on_save = on_save
        self._initial = initial or {}
        self._vars = {
            "nome": tk.StringVar(value=str(self._initial.get("nome", ""))),
            "descricao": tk.StringVar(value=str(self._initial.get("descricao", ""))),
        }
        self._build()

    def _build(self) -> None:
        outer = ttb.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)
        ttb.Label(outer, text="Cadastro de setor", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 12))
        ttb.Label(outer, text="Nome do setor *").pack(anchor="w", pady=(8, 2))
        ttb.Entry(outer, textvariable=self._vars["nome"]).pack(fill="x")
        ttb.Label(outer, text="Descri??o").pack(anchor="w", pady=(10, 2))
        ttb.Entry(outer, textvariable=self._vars["descricao"]).pack(fill="x")
        buttons = ttb.Frame(outer)
        buttons.pack(fill="x", side="bottom", pady=(18, 0))
        ttb.Button(buttons, text="Cancelar", command=self.destroy, bootstyle="secondary-outline").pack(side="right")
        ttb.Button(buttons, text="Salvar", command=self._save, bootstyle="primary").pack(side="right", padx=(0, 8))

    def _save(self) -> None:
        payload = {key: var.get().strip() for key, var in self._vars.items()}
        try:
            self._on_save(payload)
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message, parent=self)
            return
        except Exception as exc:
            messagebox.showerror("Erro", str(exc), parent=self)
            return
        self.destroy()
