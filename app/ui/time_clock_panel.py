"""Painel de batida de ponto."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttb

from app.config.settings import TIME_RECORD_TYPES
from app.repositories.excel_database import ExcelSaveError
from app.services.collaborator_service import CollaboratorService
from app.services.time_clock_service import TimeClockService


class TimeClockPanel(ttb.Frame):
    def __init__(
        self,
        master: tk.Misc,
        collaborator_service: CollaboratorService,
        time_clock_service: TimeClockService,
        on_change=None,
    ):
        super().__init__(master)
        self.collaborator_service = collaborator_service
        self.time_clock_service = time_clock_service
        self.on_change = on_change
        self._collaborators: list[dict] = []
        self._selected = tk.StringVar()
        self._last_point_var = tk.StringVar(value="Último ponto: —")
        self._next_action_var = tk.StringVar(value="Próxima ação: —")
        self._point_buttons: dict[str, ttb.Button] = {}
        self._schedule_vars = {
            "entrada": tk.StringVar(),
            "saida": tk.StringVar(),
            "carga_horaria": tk.StringVar(),
            "tempo_intervalo": tk.StringVar(),
            "tolerancia_minutos": tk.StringVar(),
        }
        self._build()
        self.refresh()

    def _build(self) -> None:
        header = ttb.Frame(self)
        header.pack(fill="x", pady=(0, 12))
        ttb.Label(header, text="Registro de ponto", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttb.Label(header, text="Selecione um colaborador e registre o evento atual.").pack(anchor="w")

        schedule = ttb.Labelframe(self, text="Jornada esperada", padding=10)
        schedule.pack(fill="x", pady=(0, 12))
        for idx, (key, label, width) in enumerate(
            [
                ("entrada", "Entrada", 8),
                ("saida", "Saída", 8),
                ("carga_horaria", "Carga horária", 10),
                ("tempo_intervalo", "Tempo de pausa", 12),
                ("tolerancia_minutos", "Tolerãncia (min)", 8),
            ]
        ):
            ttb.Label(schedule, text=label).grid(row=0, column=idx, sticky="w", padx=(0, 6))
            ttb.Entry(schedule, textvariable=self._schedule_vars[key], width=width).grid(
                row=1, column=idx, sticky="ew", padx=(0, 10)
            )
            schedule.columnconfigure(idx, weight=1)
        ttb.Button(schedule, text="Salvar jornada", command=self._save_schedule, bootstyle="primary").grid(
            row=1, column=5, sticky="e"
        )

        self.combo = ttb.Combobox(self, textvariable=self._selected, state="readonly")
        self.combo.pack(fill="x", pady=(0, 8))
        self.combo.bind("<<ComboboxSelected>>", lambda _event: self._update_point_context())

        context = ttb.Labelframe(self, text="Situação do colaborador", padding=10)
        context.pack(fill="x", pady=(0, 12))
        ttb.Label(context, textvariable=self._last_point_var, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttb.Label(context, textvariable=self._next_action_var, foreground="#64748B").pack(anchor="w", pady=(3, 0))

        buttons = ttb.Frame(self)
        buttons.pack(fill="x")
        for tipo in TIME_RECORD_TYPES:
            button = ttb.Button(
                buttons,
                text=f"Bater {tipo}",
                command=lambda t=tipo: self._record(t),
                bootstyle="primary" if tipo == "entrada" else "secondary-outline",
            )
            button.pack(side="left", padx=(0, 8), pady=4)
            self._point_buttons[tipo] = button

    def refresh(self) -> None:
        self._collaborators = self.collaborator_service.list_active()
        values = [self._label(row) for row in self._collaborators]
        self.combo.configure(values=values)
        if values and self._selected.get() not in values:
            self._selected.set(values[0])
        elif not values:
            self._selected.set("")
        self._load_schedule()
        self._update_point_context()

    def _load_schedule(self) -> None:
        schedule = self.time_clock_service.get_work_schedule()
        for key, variable in self._schedule_vars.items():
            variable.set(str(schedule.get(key, "") or ""))

    def _label(self, row: dict) -> str:
        cargo = str(row.get("cargo", "") or "").strip()
        return f"{row.get('nome', '')} - {cargo}" if cargo else str(row.get("nome", ""))

    def _selected_collaborator(self) -> dict | None:
        label = self._selected.get()
        for row in self._collaborators:
            if self._label(row) == label:
                return row
        return None

    def _update_point_context(self) -> None:
        collaborator = self._selected_collaborator()
        if not collaborator:
            self._last_point_var.set("Último ponto: nenhum colaborador selecionado.")
            self._next_action_var.set("Cadastre ou selecione um colaborador para registrar ponto.")
            for button in self._point_buttons.values():
                button.configure(state="disabled")
            return

        context = self.time_clock_service.point_context(str(collaborator.get("colaborador_id")))
        self._last_point_var.set(context["last_text"])
        self._next_action_var.set(context["next_text"])
        allowed = set(context["allowed_types"])
        for tipo, button in self._point_buttons.items():
            button.configure(state="normal" if tipo in allowed else "disabled")

    def _save_schedule(self) -> None:
        try:
            self.time_clock_service.update_work_schedule(
                entrada=self._schedule_vars["entrada"].get(),
                saida=self._schedule_vars["saida"].get(),
                carga_horaria=self._schedule_vars["carga_horaria"].get(),
                tempo_intervalo=self._schedule_vars["tempo_intervalo"].get(),
                tolerancia_minutos=self._schedule_vars["tolerancia_minutos"].get(),
            )
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message)
            return
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))
            return
        messagebox.showinfo("Jornada", "Jornada esperada salva.")
        if self.on_change:
            self.on_change()

    def _record(self, tipo: str) -> None:
        collaborator = self._selected_collaborator()
        if not collaborator:
            messagebox.showwarning("Ponto", "Cadastre ou selecione um colaborador.")
            return
        try:
            self.time_clock_service.record_time(str(collaborator.get("colaborador_id")), tipo)
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message)
            return
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))
            return
        messagebox.showinfo("Ponto", f"Ponto registrado: {tipo}.")
        self._update_point_context()
        if self.on_change:
            self.on_change()
