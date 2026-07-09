"""Modal de tratativa de ocorrencias."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttb

from app.ui.window_icon import apply_window_icon


class OccurrenceEditor(tk.Toplevel):
    def __init__(self, master: tk.Misc, on_save, initial: dict):
        super().__init__(master)
        self.title("Tratativa de ocorr\u00eancia")
        self.geometry("760x560")
        self.minsize(660, 460)
        self.resizable(True, True)
        apply_window_icon(self)
        self.transient(master.winfo_toplevel())
        self.on_save = on_save
        self.initial = initial or {}
        self.responsavel_var = tk.StringVar(value=str(self.initial.get("responsavel_tratativa") or ""))
        self._build()
        self.grab_set()
        self.focus_force()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        container = ttb.Frame(self, padding=16)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(4, weight=1)
        container.rowconfigure(6, weight=1)

        title = f"{self.initial.get('data', '')} - {self.initial.get('tipo', '')}"
        ttb.Label(container, text=title, font=("Segoe UI", 13, "bold"), wraplength=700, justify="left").grid(
            row=0, column=0, sticky="ew"
        )
        details = (
            f"Colaborador: {self.initial.get('nome_colaborador', '') or '-'}  |  "
            f"Tarefa: {self.initial.get('nome_tarefa', '') or '-'}"
        )
        ttb.Label(container, text=details, foreground="#64748B", wraplength=700, justify="left").grid(
            row=1, column=0, sticky="ew", pady=(2, 10)
        )
        ttb.Label(container, text=str(self.initial.get("descricao", "")), wraplength=700, justify="left").grid(
            row=2, column=0, sticky="ew", pady=(0, 12)
        )

        form = ttb.Frame(container)
        form.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        form.columnconfigure(1, weight=1)
        ttb.Label(form, text="Status").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttb.Combobox(
            form,
            textvariable=self.status_var,
            values=[OCCURRENCE_STATUS_OPEN, OCCURRENCE_STATUS_RESOLVED],
            state="readonly",
            width=18,
        ).grid(row=0, column=1, sticky="w", pady=4)
        ttb.Label(form, text="Respons\u00e1vel pela tratativa").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttb.Entry(form, textvariable=self.responsavel_var).grid(row=1, column=1, sticky="ew", pady=4)

        ttb.Label(container, text="A\u00e7\u00e3o tomada").grid(row=4, column=0, sticky="sw")
        self.action_text = tk.Text(container, height=6, wrap="word", relief="solid", borderwidth=1)
        self.action_text.grid(row=5, column=0, sticky="nsew", pady=(4, 10))
        self.action_text.insert("1.0", str(self.initial.get("acao_tomada") or ""))

        ttb.Label(container, text="Observa\u00e7\u00f5es edit\u00e1veis").grid(row=6, column=0, sticky="sw")
        self.notes_text = tk.Text(container, height=5, wrap="word", relief="solid", borderwidth=1)
        self.notes_text.grid(row=7, column=0, sticky="nsew", pady=(4, 12))
        self.notes_text.insert("1.0", str(self.initial.get("observacoes") or ""))

        buttons = ttb.Frame(container)
        buttons.grid(row=8, column=0, sticky="e")
        ttb.Button(buttons, text="Cancelar", command=self.destroy, bootstyle="secondary-outline").pack(side="right", padx=(8, 0))
        ttb.Button(buttons, text="Salvar tratativa", command=self._save, bootstyle="primary").pack(side="right")

    def _save(self) -> None:
        status = self.status_var.get().strip()
        if status not in {OCCURRENCE_STATUS_OPEN, OCCURRENCE_STATUS_RESOLVED}:
            messagebox.showwarning("Ocorr\u00eancias", "Selecione um status v\u00e1lido.", parent=self)
            return
        payload = {
            "status": status,
            "responsavel_tratativa": self.responsavel_var.get().strip(),
            "acao_tomada": self.action_text.get("1.0", "end").strip(),
            "observacoes": self.notes_text.get("1.0", "end").strip(),
        }
        self.on_save(payload)
        self.destroy()
