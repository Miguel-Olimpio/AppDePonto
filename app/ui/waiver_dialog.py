"""Modal para abonar ocorrencias/faltas."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttb

from app.ui.window_icon import apply_window_icon

WAIVER_REASONS = ["Atestado", "Troca entre funcionarios", "Folga combinada", "Erro de registro", "Outro"]


class WaiverDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, on_save, occurrence: dict):
        super().__init__(master)
        self.title("Abonar ocorrência/falta")
        self.geometry("560x420")
        self.minsize(480, 340)
        self.resizable(True, True)
        apply_window_icon(self)
        self.transient(master.winfo_toplevel())
        self.grab_set()
        self._on_save = on_save
        self.occurrence = occurrence
        self.reason_var = tk.StringVar(value=str(occurrence.get("motivo_abono") or WAIVER_REASONS[0]))
        self._build()

    def _build(self) -> None:
        container = ttb.Frame(self, padding=18)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(5, weight=1)
        ttb.Label(container, text="Abonar ocorrência/falta", font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w")
        details = f"{self.occurrence.get('data', '')} - {self.occurrence.get('tipo', '')} - {self.occurrence.get('nome_colaborador', '')}"
        ttb.Label(container, text=details, foreground="#64748B", wraplength=500, justify="left").grid(row=1, column=0, sticky="ew", pady=(2, 12))
        ttb.Label(container, text="Motivo do abono").grid(row=2, column=0, sticky="w")
        ttb.Combobox(container, textvariable=self.reason_var, values=WAIVER_REASONS, state="readonly").grid(row=3, column=0, sticky="ew", pady=(4, 12))
        ttb.Label(container, text="Observação do abono").grid(row=4, column=0, sticky="w")
        self.notes = tk.Text(container, height=6, wrap="word", relief="solid", borderwidth=1)
        self.notes.grid(row=5, column=0, sticky="nsew", pady=(4, 12))
        self.notes.insert("1.0", str(self.occurrence.get("observacao_abono") or ""))
        buttons = ttb.Frame(container)
        buttons.grid(row=6, column=0, sticky="e")
        ttb.Button(buttons, text="Cancelar", command=self.destroy, bootstyle="secondary-outline").pack(side="right", padx=(8, 0))
        ttb.Button(buttons, text="Abonar", command=self._save, bootstyle="primary").pack(side="right")

    def _save(self) -> None:
        payload = {"motivo_abono": self.reason_var.get().strip(), "observacao_abono": self.notes.get("1.0", "end").strip()}
        if not payload["motivo_abono"]:
            messagebox.showwarning("Abono", "Informe o motivo do abono.", parent=self)
            return
        self._on_save(payload)
        self.destroy()
