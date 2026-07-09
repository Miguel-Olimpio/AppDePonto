"""Modal de cadastro/edicao de metas mensais."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttb

from app.config.settings import GOAL_TYPE_COLLECTIVE, GOAL_TYPE_INDIVIDUAL
from app.repositories.excel_database import ExcelSaveError
from app.ui.window_icon import apply_window_icon


class GoalEditor(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        on_save,
        initial: dict | None = None,
        collaborator_options: list[tuple[str, str]] | None = None,
    ):
        super().__init__(master)
        self.title("Meta")
        self.geometry("760x640")
        self.minsize(620, 500)
        self.resizable(True, True)
        apply_window_icon(self)
        self.transient(master.winfo_toplevel())
        self.grab_set()
        self._on_save = on_save
        self._initial = initial or {}
        self._collaborator_options = collaborator_options or []
        self._collaborator_by_id = {collaborator_id: label for collaborator_id, label in self._collaborator_options}
        self._collaborator_id_by_label = {label: collaborator_id for collaborator_id, label in self._collaborator_options}
        initial_collaborator = self._collaborator_by_id.get(
            str(self._initial.get("colaborador_id", "")),
            str(self._initial.get("nome_colaborador", "")),
        )
        self._vars = {
            "nome_meta": tk.StringVar(value=str(self._initial.get("nome_meta", ""))),
            "tipo_meta": tk.StringVar(value=str(self._initial.get("tipo_meta", GOAL_TYPE_COLLECTIVE) or GOAL_TYPE_COLLECTIVE)),
            "periodo_mes": tk.StringVar(value=str(self._initial.get("periodo_mes", ""))),
            "valor_bonus": tk.StringVar(value=str(self._initial.get("valor_bonus", "0") or "0")),
            "valor_meta": tk.StringVar(value=str(self._initial.get("valor_meta", "0") or "0")),
            "valor_realizado": tk.StringVar(value=str(self._initial.get("valor_realizado", "0") or "0")),
            "atingida": tk.StringVar(value="sim" if str(self._initial.get("atingida", "")).lower() in {"true", "1", "sim", "yes"} else "nao"),
            "colaborador_label": tk.StringVar(value=initial_collaborator),
            "descricao": tk.StringVar(value=str(self._initial.get("descricao", ""))),
            "observacoes": tk.StringVar(value=str(self._initial.get("observacoes", ""))),
        }
        self._build()
        self._sync_collaborator_state()

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

        ttb.Label(inner, text="Cadastro de meta", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 12))
        self._entry(inner, "Nome da meta *", "nome_meta")
        row = ttb.Frame(inner)
        row.pack(fill="x", pady=(8, 0))
        self._combo(row, "Tipo de meta *", "tipo_meta", [GOAL_TYPE_COLLECTIVE, GOAL_TYPE_INDIVIDUAL], side="left")
        self._entry(row, "Mes/Ano (MM/AAAA) *", "periodo_mes", side="left")
        self._entry(inner, "Descricao", "descricao")

        numbers = ttb.Frame(inner)
        numbers.pack(fill="x", pady=(8, 0))
        self._entry(numbers, "Valor do bonus", "valor_bonus", side="left")
        self._entry(numbers, "Valor da meta", "valor_meta", side="left")
        self._entry(numbers, "Valor realizado", "valor_realizado", side="left")

        self._combo(inner, "Atingida?", "atingida", ["sim", "nao"])
        ttb.Label(inner, text="Colaborador para meta individual").pack(anchor="w", pady=(8, 2))
        self.collaborator_combo = ttb.Combobox(
            inner,
            textvariable=self._vars["colaborador_label"],
            values=[label for _collaborator_id, label in self._collaborator_options],
            state="readonly",
        )
        self.collaborator_combo.pack(fill="x")
        self._vars["tipo_meta"].trace_add("write", lambda *_args: self._sync_collaborator_state())
        self._entry(inner, "Observacoes", "observacoes")

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

    def _combo(self, parent: ttb.Frame, label: str, key: str, values: list[str], side: str | None = None) -> None:
        frame = ttb.Frame(parent)
        if side:
            frame.pack(side=side, fill="x", expand=True, padx=(0, 8))
        else:
            frame.pack(fill="x", pady=(8, 0))
        ttb.Label(frame, text=label).pack(anchor="w", pady=(0, 2))
        ttb.Combobox(frame, textvariable=self._vars[key], values=values, state="readonly").pack(fill="x")

    def _bind_canvas_mousewheel(self, canvas: tk.Canvas, inner: ttb.Frame) -> None:
        def on_wheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                return
        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", on_wheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))
        inner.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", on_wheel))
        inner.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

    def _sync_collaborator_state(self) -> None:
        is_individual = self._vars["tipo_meta"].get() == GOAL_TYPE_INDIVIDUAL
        self.collaborator_combo.configure(state="readonly" if is_individual else "disabled")
        if not is_individual:
            self._vars["colaborador_label"].set("")

    def _save(self) -> None:
        payload = {key: var.get().strip() for key, var in self._vars.items()}
        collaborator_label = payload.pop("colaborador_label", "")
        payload["colaborador_id"] = self._collaborator_id_by_label.get(collaborator_label, "")
        payload["nome_colaborador"] = collaborator_label
        try:
            self._on_save(payload)
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message, parent=self)
            return
        except Exception as exc:
            messagebox.showerror("Erro", str(exc), parent=self)
            return
        self.destroy()
