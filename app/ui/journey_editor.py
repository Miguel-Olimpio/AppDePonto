"""Modal de cadastro/edicao de jornadas e escalas."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttb

from app.config.settings import SCALE_TYPE_SCALE, SCALE_TYPE_WEEKLY, SCALE_TYPES, WEEKDAY_NAMES
from app.repositories.excel_database import ExcelSaveError
from app.ui.window_icon import apply_window_icon


class JourneyEditor(tk.Toplevel):
    def __init__(self, master: tk.Misc, on_save, initial: dict | None = None):
        super().__init__(master)
        self.title("Jornada / Escala")
        self.geometry("820x760")
        self.minsize(660, 540)
        self.resizable(True, True)
        apply_window_icon(self)
        self.transient(master.winfo_toplevel())
        self.grab_set()
        self._on_save = on_save
        self._initial = initial or {}
        self._vars = {
            "nome": tk.StringVar(value=str(self._initial.get("nome", ""))),
            "tipo_escala": tk.StringVar(value=self._initial_type()),
            "entrada": tk.StringVar(value=str(self._initial.get("entrada", ""))),
            "saida": tk.StringVar(value=str(self._initial.get("saida", ""))),
            "carga_horaria": tk.StringVar(value=_hours_text(self._initial.get("carga_horaria", ""))),
            "tempo_intervalo": tk.StringVar(value=_minutes_to_hhmm(self._initial.get("tempo_intervalo", "01:00"))),
            "tolerancia_minutos": tk.StringVar(value=str(self._initial.get("tolerancia_minutos", "0") or "0")),
            "descricao_escala": tk.StringVar(value=str(self._initial.get("descricao_escala", ""))),
            "horas_trabalho": tk.StringVar(value=str(self._initial.get("horas_trabalho", "") or "")),
            "horas_descanso": tk.StringVar(value=str(self._initial.get("horas_descanso", "") or "")),
            "horario_inicio_escala": tk.StringVar(value=str(self._initial.get("horario_inicio_escala", "") or self._initial.get("entrada", ""))),
            "data_inicio_escala": tk.StringVar(value=str(self._initial.get("data_inicio_escala", ""))),
        }
        self._day_vars: dict[str, tk.BooleanVar] = {}
        self._build()
        self._toggle_scale_fields()

    def _initial_type(self) -> str:
        raw = str(self._initial.get("tipo_escala", SCALE_TYPE_WEEKLY) or SCALE_TYPE_WEEKLY)
        return SCALE_TYPE_SCALE if raw.lower() in {"escala", "12x36", "24x48"} else SCALE_TYPE_WEEKLY

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

        ttb.Label(inner, text="Jornada / Escala", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 12))
        self._entry(inner, "Nome da jornada", "nome")
        ttb.Label(inner, text="Tipo de jornada").pack(anchor="w", pady=(8, 2))
        scale_combo = ttb.Combobox(inner, textvariable=self._vars["tipo_escala"], values=list(SCALE_TYPES), state="readonly")
        scale_combo.pack(fill="x")
        scale_combo.bind("<<ComboboxSelected>>", lambda _event: self._toggle_scale_fields())

        self.weekly_frame = ttb.Labelframe(inner, text="Semanal fixa", padding=10)
        self.weekly_frame.pack(fill="x", pady=(12, 0))
        row = ttb.Frame(self.weekly_frame)
        row.pack(fill="x", pady=(0, 8))
        self._entry(row, "Entrada (HH:MM)", "entrada", side="left")
        self._entry(row, "Saída (HH:MM)", "saida", side="left")
        self._entry(row, "Carga horária", "carga_horaria", side="left")
        self._entry(row, "Tempo de pausa (HH:MM)", "tempo_intervalo", side="left")
        ttb.Label(
            self.weekly_frame,
            text="O horário de retorno da pausa será calculado automaticamente a partir do horário em que o colaborador bater o ponto de pausa.",
            wraplength=700,
            justify="left",
            foreground="#64748B",
        ).pack(anchor="w", pady=(4, 0))
        ttb.Label(self.weekly_frame, text="Dias trabalhados").pack(anchor="w", pady=(8, 4))
        days_frame = ttb.Frame(self.weekly_frame)
        days_frame.pack(fill="x")
        selected = self._selected_days()
        for idx, day in enumerate(WEEKDAY_NAMES):
            var = tk.BooleanVar(value=(not selected or day in selected))
            self._day_vars[day] = var
            ttb.Checkbutton(days_frame, text=day.title(), variable=var).grid(
                row=idx // 3, column=idx % 3, sticky="w", padx=(0, 16), pady=3
            )

        self.scale_frame = ttb.Labelframe(inner, text="Escala", padding=10)
        self.scale_frame.pack(fill="x", pady=(12, 0))
        ttb.Label(
            self.scale_frame,
            text="Em escalas, informe quantas horas o colaborador trabalha e quantas horas descansa. Exemplo: 24x48 significa 24 horas de trabalho e 48 horas de descanso.",
            wraplength=700,
            justify="left",
            foreground="#64748B",
        ).pack(anchor="w", pady=(0, 8))
        self._entry(self.scale_frame, "Descricao da escala (ex.: 12x36, 24x48, 6x1)", "descricao_escala")
        scale_row = ttb.Frame(self.scale_frame)
        scale_row.pack(fill="x", pady=(8, 0))
        self._entry(scale_row, "Horas de trabalho", "horas_trabalho", side="left")
        self._entry(scale_row, "Horas de descanso", "horas_descanso", side="left")
        self._entry(scale_row, "Horário de início", "horario_inicio_escala", side="left")
        self._entry(self.scale_frame, "Data inicial da escala (DD/MM/AAAA)", "data_inicio_escala")
        pause_row = ttb.Frame(self.scale_frame)
        pause_row.pack(fill="x", pady=(8, 0))
        self._entry(pause_row, "Carga horária", "carga_horaria", side="left")
        self._entry(pause_row, "Tempo de pausa (HH:MM)", "tempo_intervalo", side="left")
        ttb.Label(
            self.scale_frame,
            text="O horário de retorno da pausa será calculado automaticamente a partir do horário em que o colaborador bater o ponto de pausa.",
            wraplength=700,
            justify="left",
            foreground="#64748B",
        ).pack(anchor="w", pady=(4, 0))

        self.tolerance_frame = self._entry(inner, "Tolerancia de atraso em minutos", "tolerancia_minutos")

        buttons = ttb.Frame(inner)
        buttons.pack(fill="x", pady=(18, 0))
        ttb.Button(buttons, text="Cancelar", command=self.destroy, bootstyle="secondary-outline").pack(side="right")
        ttb.Button(buttons, text="Salvar", command=self._save, bootstyle="primary").pack(side="right", padx=(0, 8))

    def _entry(self, parent: ttb.Frame, label: str, key: str, side: str | None = None) -> ttb.Frame:
        frame = ttb.Frame(parent)
        if side:
            frame.pack(side=side, fill="x", expand=True, padx=(0, 8))
        else:
            frame.pack(fill="x", pady=(8, 0))
        ttb.Label(frame, text=label).pack(anchor="w", pady=(0, 2))
        ttb.Entry(frame, textvariable=self._vars[key]).pack(fill="x")
        return frame

    def _selected_days(self) -> set[str]:
        raw = str(self._initial.get("dias_semana", "") or "").lower().strip()
        if not raw or raw == "todos":
            return set()
        return {item.strip() for item in raw.replace(";", ",").split(",") if item.strip()}

    def _toggle_scale_fields(self) -> None:
        is_scale = self._vars["tipo_escala"].get() == SCALE_TYPE_SCALE
        self.weekly_frame.pack_forget()
        self.scale_frame.pack_forget()
        if is_scale:
            self.scale_frame.pack(fill="x", pady=(12, 0), before=self.tolerance_frame)
        else:
            self.weekly_frame.pack(fill="x", pady=(12, 0), before=self.tolerance_frame)

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
        if payload.get("tipo_escala") == SCALE_TYPE_SCALE:
            payload["dias_semana"] = ""
        else:
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


def _minutes_to_hhmm(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "01:00"
    if ":" in text:
        return text
    try:
        minutes = int(float(text.replace(",", ".")))
    except ValueError:
        return text
    if minutes <= 0:
        return "01:00"
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _hours_text(value: object) -> str:
    text = str(value or "").strip()
    if text in {"", "0", "0.0"}:
        return ""
    return text.replace(".", ",")
