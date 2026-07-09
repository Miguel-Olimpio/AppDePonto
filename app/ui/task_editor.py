"""Modal de cadastro/edicao de tarefa/POP."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttb

from app.config.settings import WEEKDAY_NAMES
from app.repositories.excel_database import ExcelSaveError
from app.ui.window_icon import apply_window_icon


class TaskEditor(tk.Toplevel):
    def __init__(self, master: tk.Misc, on_save, initial: dict | None = None, sector_options: list[tuple[str, str]] | None = None):
        super().__init__(master)
        self.title("Tarefa / POP")
        self.geometry("720x700")
        self.minsize(560, 500)
        self.resizable(True, True)
        apply_window_icon(self)
        self.transient(master.winfo_toplevel())
        self.grab_set()
        self._on_save = on_save
        self._initial = initial or {}
        self._sector_options = sector_options or []
        self._sector_label_by_id = {setor_id: label for setor_id, label in self._sector_options}
        self._sector_id_by_label = {label: setor_id for setor_id, label in self._sector_options}
        initial_sector_label = self._sector_label_by_id.get(
            str(self._initial.get("setor_id", "")),
            str(self._initial.get("nome_setor", "")),
        )
        self._vars = {
            "nome": tk.StringVar(value=str(self._initial.get("nome", ""))),
            "descricao": tk.StringVar(value=str(self._initial.get("descricao", ""))),
            "horario_inicio": tk.StringVar(value=str(self._initial.get("horario_inicio", ""))),
            "horario_limite": tk.StringVar(value=str(self._initial.get("horario_limite", ""))),
            "tolerancia_minutos": tk.StringVar(value=str(self._initial.get("tolerancia_minutos", "0") or "0")),
            "setor_label": tk.StringVar(value=initial_sector_label),
            "observacoes": tk.StringVar(value=str(self._initial.get("observacoes", ""))),
        }
        self._day_vars: dict[str, tk.BooleanVar] = {}
        self._build()

    def _build(self) -> None:
        outer = ttb.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0, background="white")
        scrollbar = ttb.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = ttb.Frame(canvas, padding=16)
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        inner.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))
        self._bind_canvas_mousewheel(canvas, inner)

        ttb.Label(inner, text="Tarefa obrigatoria / POP", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 12))
        self._entry(inner, "Nome da tarefa", "nome")
        self._entry(inner, "Descricao / POP", "descricao")
        row = ttb.Frame(inner)
        row.pack(fill="x", pady=(8, 0))
        self._entry(row, "Horario inicio (HH:MM)", "horario_inicio", side="left")
        self._entry(row, "Horario limite (HH:MM)", "horario_limite", side="left")
        self._entry(inner, "Tolerancia em minutos", "tolerancia_minutos")
        ttb.Label(inner, text="Setor de execucao *").pack(anchor="w", pady=(8, 2))
        ttb.Combobox(
            inner,
            textvariable=self._vars["setor_label"],
            values=[label for _setor_id, label in self._sector_options],
            state="readonly",
        ).pack(fill="x")
        self._entry(inner, "Observacoes", "observacoes")

        ttb.Label(inner, text="Dias da semana").pack(anchor="w", pady=(12, 4))
        days_frame = ttb.Frame(inner)
        days_frame.pack(fill="x")
        selected = self._selected_days()
        for idx, day in enumerate(WEEKDAY_NAMES):
            var = tk.BooleanVar(value=(not selected or day in selected))
            self._day_vars[day] = var
            ttb.Checkbutton(days_frame, text=day.title(), variable=var).grid(
                row=idx // 3, column=idx % 3, sticky="w", padx=(0, 16), pady=3
            )

        buttons = ttb.Frame(inner)
        buttons.pack(fill="x", pady=(18, 0))
        ttb.Button(buttons, text="Cancelar", command=self.destroy, bootstyle="secondary-outline").pack(side="right")
        ttb.Button(buttons, text="Salvar", command=self._save, bootstyle="primary").pack(side="right", padx=(0, 8))

    def _entry(self, parent: ttb.Frame, label: str, key: str, side: str | None = None) -> None:
        frame = ttb.Frame(parent)
        if side:
            frame.pack(side=side, fill="x", expand=True, padx=(0, 8))
        else:
            frame.pack(fill="x", pady=(8, 0))
        ttb.Label(frame, text=label).pack(anchor="w", pady=(0, 2))
        ttb.Entry(frame, textvariable=self._vars[key]).pack(fill="x")

    def _selected_days(self) -> set[str]:
        raw = str(self._initial.get("dias_semana", "") or "").lower().strip()
        if not raw or raw == "todos":
            return set()
        return {item.strip() for item in raw.replace(";", ",").split(",") if item.strip()}

    def _bind_canvas_mousewheel(self, canvas: tk.Canvas, inner: ttb.Frame) -> None:
        def on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", on_wheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))
        inner.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", on_wheel))
        inner.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

    def _save(self) -> None:
        chosen = [day for day, var in self._day_vars.items() if var.get()]
        payload = {key: var.get().strip() for key, var in self._vars.items()}
        sector_label = payload.pop("setor_label", "")
        payload["setor_id"] = self._sector_id_by_label.get(sector_label, "")
        payload["nome_setor"] = sector_label
        payload["dias_semana"] = "todos" if len(chosen) == len(WEEKDAY_NAMES) else ", ".join(chosen)
        try:
            self._on_save(payload)
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message, parent=self)
            return
        except Exception as exc:
            messagebox.showerror("Erro", str(exc), parent=self)
            return
        self.destroy()
