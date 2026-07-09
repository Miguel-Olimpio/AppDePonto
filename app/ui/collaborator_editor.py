"""Modal de cadastro/edicao de colaborador."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttb

from app.repositories.excel_database import ExcelSaveError
from app.ui.window_icon import apply_window_icon


class CollaboratorEditor(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        on_save,
        initial: dict | None = None,
        journey_options: list[tuple[str, str]] | None = None,
        sector_options: list[tuple[str, str]] | None = None,
    ):
        super().__init__(master)
        self.title("Colaborador")
        self.geometry("640x660")
        self.minsize(520, 440)
        self.resizable(True, True)
        apply_window_icon(self)
        self.transient(master.winfo_toplevel())
        self.grab_set()
        self._on_save = on_save
        self._initial = initial or {}
        self._journey_options = journey_options or []
        self._sector_options = sector_options or []
        self._journey_label_by_id = {jornada_id: label for jornada_id, label in self._journey_options}
        self._journey_id_by_label = {label: jornada_id for jornada_id, label in self._journey_options}
        self._sector_label_by_id = {setor_id: label for setor_id, label in self._sector_options}
        self._sector_id_by_label = {label: setor_id for setor_id, label in self._sector_options}
        initial_sector_label = self._sector_label_by_id.get(
            str(self._initial.get("setor_id", "")),
            str(self._initial.get("nome_setor", "")),
        )
        self._vars = {
            "nome": tk.StringVar(value=str(self._initial.get("nome", ""))),
            "cargo": tk.StringVar(value=str(self._initial.get("cargo", ""))),
            "telefone": tk.StringVar(value=str(self._initial.get("telefone", ""))),
            "setor_label": tk.StringVar(value=initial_sector_label),
            "salario_base": tk.StringVar(value=str(self._initial.get("salario_base", "") or "")),
            "bonus_assiduidade": tk.StringVar(value=str(self._initial.get("bonus_assiduidade", "") or "")),
            "bonus_tarefas": tk.StringVar(value=str(self._initial.get("bonus_tarefas", "") or "")),
            "jornada_label": tk.StringVar(value=self._journey_label_by_id.get(str(self._initial.get("jornada_id", "")), "")),
            "observacoes": tk.StringVar(value=str(self._initial.get("observacoes", ""))),
        }
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

        ttb.Label(inner, text="Dados do colaborador", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 12))
        self._entry(inner, "Nome", "nome")
        self._entry(inner, "Cargo", "cargo")
        self._entry(inner, "Telefone", "telefone")
        ttb.Label(inner, text="Setor *").pack(anchor="w", pady=(8, 2))
        ttb.Combobox(
            inner,
            textvariable=self._vars["setor_label"],
            values=[label for _setor_id, label in self._sector_options],
            state="readonly",
        ).pack(fill="x")
        self._entry(inner, "Salario base", "salario_base")
        self._entry(inner, "Bonus por assiduidade", "bonus_assiduidade")
        self._entry(inner, "Bonus por tarefas em dia", "bonus_tarefas")
        ttb.Label(inner, text="Jornada / escala vinculada").pack(anchor="w", pady=(8, 2))
        ttb.Combobox(
            inner,
            textvariable=self._vars["jornada_label"],
            values=[label for _jornada_id, label in self._journey_options],
            state="readonly",
        ).pack(fill="x")
        self._entry(inner, "Observacoes", "observacoes")

        buttons = ttb.Frame(inner)
        buttons.pack(fill="x", pady=(18, 0))
        ttb.Button(buttons, text="Cancelar", command=self.destroy, bootstyle="secondary-outline").pack(side="right")
        ttb.Button(buttons, text="Salvar", command=self._save, bootstyle="primary").pack(side="right", padx=(0, 8))

    def _entry(self, parent: ttb.Frame, label: str, key: str) -> None:
        ttb.Label(parent, text=label).pack(anchor="w", pady=(8, 2))
        ttb.Entry(parent, textvariable=self._vars[key]).pack(fill="x")

    def _bind_canvas_mousewheel(self, canvas: tk.Canvas, inner: ttb.Frame) -> None:
        def on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", on_wheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))
        inner.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", on_wheel))
        inner.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

    def _save(self) -> None:
        payload = {key: var.get().strip() for key, var in self._vars.items()}
        journey_label = payload.pop("jornada_label", "")
        sector_label = payload.pop("setor_label", "")
        payload["jornada_id"] = self._journey_id_by_label.get(journey_label, "")
        payload["setor_id"] = self._sector_id_by_label.get(sector_label, "")
        payload["nome_setor"] = sector_label
        try:
            self._on_save(payload)
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message, parent=self)
            return
        except Exception as exc:
            messagebox.showerror("Erro", str(exc), parent=self)
            return
        self.destroy()
