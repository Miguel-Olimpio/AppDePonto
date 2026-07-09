"""Interface inicial simplificada para colaboradores."""

from __future__ import annotations

import tkinter as tk
import unicodedata
from tkinter import messagebox
from tkinter import ttk

import ttkbootstrap as ttb

from app.config.settings import (
    APP_TITLE,
    TASK_STATUS_DONE,
    TASK_STATUS_IN_PROGRESS,
    TASK_STATUS_LATE,
    TASK_STATUS_MISSED,
    TASK_STATUS_PARTIAL,
    TASK_STATUS_TOLERANCE,
    TIME_RECORD_TYPES,
)
from app.repositories.excel_database import ExcelSaveError
from app.bot.bot_service import BotService
from app.services.collaborator_service import CollaboratorService
from app.services.journey_service import JourneyService
from app.services.task_service import TaskService
from app.services.time_clock_service import TimeClockService
from app.ui.observation_dialog import ObservationDialog

PRIMARY = "#005CA9"
BACKGROUND = "#F4F8FC"
WHITE = "#FFFFFF"
MUTED = "#64748B"


class CollaboratorView(ttb.Frame):
    def __init__(
        self,
        master: tk.Misc,
        collaborator_service: CollaboratorService,
        time_clock_service: TimeClockService,
        task_service: TaskService,
        bot_service: BotService,
        on_admin_request,
        journey_service: JourneyService | None = None,
    ):
        super().__init__(master, padding=(24, 18), style="Content.TFrame")
        self.collaborator_service = collaborator_service
        self.time_clock_service = time_clock_service
        self.task_service = task_service
        self.bot_service = bot_service
        self.on_admin_request = on_admin_request
        self.journey_service = journey_service
        self._collaborators: list[dict] = []
        self._current_tasks: dict[str, dict] = {}
        self._selected = tk.StringVar()
        self._last_point_var = tk.StringVar(value="Selecione um colaborador.")
        self._next_action_var = tk.StringVar(value="")
        self._task_hint_var = tk.StringVar(value="Selecione uma tarefa e clique em Marcar como feita.")
        self._bot_status_var = tk.StringVar(value="WhatsApp: verificando")
        self._point_buttons: dict[str, ttb.Button] = {}
        self._auto_refresh_after: str | None = None
        self._bot_status_after: str | None = None
        self._build()
        self.bind("<Destroy>", self._on_destroy, add="+")
        self.refresh()
        self._schedule_auto_refresh()
        self._schedule_bot_status_refresh()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        header = ttb.Frame(self, style="Content.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)
        ttb.Label(header, text=APP_TITLE, font=("Segoe UI", 18, "bold"), foreground=PRIMARY).grid(row=0, column=0, sticky="w")
        ttb.Label(
            header,
            text="Registre seu ponto e confira as tarefas do dia.",
            foreground=MUTED,
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        header_actions = ttb.Frame(header, style="Content.TFrame")
        header_actions.grid(row=0, column=1, rowspan=2, sticky="e")
        self.bot_status_button = ttb.Button(
            header_actions,
            textvariable=self._bot_status_var,
            command=self._update_bot_status,
            bootstyle="secondary-outline",
            width=24,
        )
        self.bot_status_button.pack(side="left", padx=(0, 8))
        ttb.Button(
            header_actions,
            text="\u00c1rea do administrador",
            command=self.on_admin_request,
            bootstyle="secondary-outline",
        ).pack(side="left")

        person_box = ttb.Labelframe(self, text="Colaborador", padding=12)
        person_box.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        person_box.columnconfigure(1, weight=1)
        ttb.Label(person_box, text="Selecionar colaborador").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.combo = ttb.Combobox(person_box, textvariable=self._selected, state="readonly")
        self.combo.grid(row=0, column=1, sticky="ew")
        self.combo.bind("<<ComboboxSelected>>", lambda _event: self._on_collaborator_change())
        self.collaborator_observation_button = ttb.Button(
            person_box,
            text="Ver observações",
            command=self._show_collaborator_observations,
            bootstyle="info-outline",
            state="disabled",
            width=18,
        )
        self.collaborator_observation_button.grid(row=0, column=2, sticky="e", padx=(10, 0))

        point_box = ttb.Labelframe(self, text="Ponto", padding=12)
        point_box.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        point_box.columnconfigure(0, weight=1)
        ttb.Label(point_box, textvariable=self._last_point_var, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        ttb.Label(point_box, textvariable=self._next_action_var, foreground=MUTED).grid(row=1, column=0, sticky="w", pady=(2, 8))
        buttons = ttb.Frame(point_box)
        buttons.grid(row=2, column=0, sticky="w")
        for tipo in TIME_RECORD_TYPES:
            button = ttb.Button(
                buttons,
                text=tipo.capitalize(),
                command=lambda t=tipo: self._record_time(t),
                bootstyle="primary" if tipo == "entrada" else "secondary-outline",
                width=12,
            )
            button.pack(side="left", padx=(0, 8), pady=2)
            self._point_buttons[tipo] = button

        activity_columns = ("atividade", "status", "detalhe")
        self.point_activity_tree = ttk.Treeview(point_box, columns=activity_columns, show="headings", height=4)
        self.point_activity_tree.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        for col, label, width in [
            ("atividade", "Atividade", 130),
            ("status", "Status", 190),
            ("detalhe", "Detalhe", 360),
        ]:
            self.point_activity_tree.heading(col, text=label, anchor="center")
            self.point_activity_tree.column(col, width=width, minwidth=90, anchor="center")
        self.point_activity_tree.tag_configure("done", background="#D8F5D0")
        self.point_activity_tree.tag_configure("running", background="#FFF3C4")
        self.point_activity_tree.tag_configure("late", background="#FFD6D6")
        self.point_activity_tree.tag_configure("pending", background="#F1F5F9")

        tasks_box = ttb.Labelframe(self, text="Tarefas / POPs do dia", padding=12)
        tasks_box.grid(row=3, column=0, sticky="nsew")
        tasks_box.rowconfigure(0, weight=1)
        tasks_box.columnconfigure(0, weight=1)
        columns = ("nome", "horario", "status", "setor", "observacao")
        self.task_tree = ttk.Treeview(tasks_box, columns=columns, show="headings", height=10)
        y_scroll = ttb.Scrollbar(tasks_box, orient="vertical", command=self.task_tree.yview)
        x_scroll = ttb.Scrollbar(tasks_box, orient="horizontal", command=self.task_tree.xview)
        self.task_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.task_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        for col, label, width in [
            ("nome", "Tarefa", 260),
            ("horario", "Hor\u00e1rio", 150),
            ("status", "Status", 130),
            ("setor", "Setor", 140),
            ("observacao", "Observação", 150),
        ]:
            self.task_tree.heading(col, text=label, anchor="center")
            self.task_tree.column(col, width=width, minwidth=90, anchor="center")
        self.task_tree.tag_configure("running", background="#FFF3C4")
        self.task_tree.tag_configure("late", background="#FFD6D6")
        self.task_tree.tag_configure("done", background="#D8F5D0")
        self.task_tree.tag_configure("pending", background="#F1F5F9")
        self.task_tree.bind("<<TreeviewSelect>>", lambda _event: self._update_task_observation_button())
        self.task_tree.bind("<ButtonRelease-1>", self._handle_task_tree_click)
        self.task_tree.bind("<Return>", lambda _event: self._show_selected_task_observation_if_available())
        self.task_tree.bind("<Enter>", lambda _event: self._bind_tree_mousewheel())
        self.task_tree.bind("<Leave>", lambda _event: self._unbind_tree_mousewheel())

        task_actions = ttb.Frame(tasks_box)
        task_actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttb.Button(task_actions, text="Marcar como feita", command=self._mark_selected_task_done, bootstyle="primary").pack(
            side="left"
        )
        self.task_observation_button = ttb.Button(
            task_actions,
            text="Ver observação",
            command=self._show_selected_task_observation,
            bootstyle="info-outline",
            state="disabled",
        )
        self.task_observation_button.pack(side="left", padx=(8, 0))
        ttb.Label(task_actions, textvariable=self._task_hint_var, foreground=MUTED).pack(side="left", padx=(12, 0))
        ttb.Button(task_actions, text="Atualizar", command=self.refresh, bootstyle="secondary-outline").pack(side="right")

    def refresh(self) -> None:
        self._collaborators = self.collaborator_service.list_active()
        values = [self._label(row) for row in self._collaborators]
        self.combo.configure(values=values)
        if values and self._selected.get() not in values:
            self._selected.set(values[0])
        elif not values:
            self._selected.set("")
        self._update_point_context()
        self._refresh_tasks()
        self._update_bot_status()

    def _label(self, row: dict) -> str:
        cargo = str(row.get("cargo", "") or "").strip()
        return f"{row.get('nome', '')} - {cargo}" if cargo else str(row.get("nome", ""))

    def _selected_collaborator(self) -> dict | None:
        label = self._selected.get()
        for row in self._collaborators:
            if self._label(row) == label:
                return row
        return None

    def _on_collaborator_change(self) -> None:
        self._update_point_context()
        self._refresh_tasks()
        self._update_collaborator_observation_button()

    def _update_point_context(self) -> None:
        collaborator = self._selected_collaborator()
        if not collaborator:
            self._last_point_var.set("Nenhum colaborador selecionado.")
            self._next_action_var.set("Procure o administrador para cadastrar colaboradores.")
            for button in self._point_buttons.values():
                button.configure(state="disabled")
            self._refresh_point_activities(None)
            self._update_collaborator_observation_button()
            return
        context = self.time_clock_service.point_context(str(collaborator.get("colaborador_id")))
        self._last_point_var.set(context["last_text"])
        self._next_action_var.set(context["next_text"])
        allowed = set(context["allowed_types"])
        for tipo, button in self._point_buttons.items():
            button.configure(state="normal" if tipo in allowed else "disabled")
        self._refresh_point_activities(collaborator)
        self._update_collaborator_observation_button()

    def _refresh_point_activities(self, collaborator: dict | None) -> None:
        if not hasattr(self, "point_activity_tree"):
            return
        self.point_activity_tree.delete(*self.point_activity_tree.get_children())
        if not collaborator:
            for tipo in TIME_RECORD_TYPES:
                self.point_activity_tree.insert(
                    "",
                    "end",
                    iid=f"point-{tipo}",
                    values=(tipo.capitalize(), "Pendente", "Selecione um colaborador."),
                    tags=("pending",),
                )
            return
        activities = self.time_clock_service.point_activities_for_collaborator(str(collaborator.get("colaborador_id")))
        for activity in activities:
            self.point_activity_tree.insert(
                "",
                "end",
                iid=f"point-{activity.get('tipo', '')}",
                values=(activity.get("label", ""), activity.get("status", ""), activity.get("detail", "")),
                tags=(activity.get("tag", "pending"),),
            )

    def _record_time(self, tipo: str) -> None:
        collaborator = self._selected_collaborator()
        if not collaborator:
            messagebox.showwarning("Ponto", "Selecione um colaborador.")
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
        self.refresh()

    def _refresh_tasks(self) -> None:
        selected = self.task_tree.selection()[0] if self.task_tree.selection() else ""
        collaborator = self._selected_collaborator()
        checked_task_ids = self._checked_task_ids_for_collaborator(str((collaborator or {}).get("colaborador_id", "")))
        self.task_tree.delete(*self.task_tree.get_children())
        tasks = self.task_service.tasks_for_collaborator(collaborator) if collaborator else []
        self._current_tasks = {}
        for task in tasks:
            state = self._collaborator_task_state(task, checked_task_ids)
            task_id = str(task.get("tarefa_id"))
            self._current_tasks[task_id] = task
            self.task_tree.insert(
                "",
                "end",
                iid=task_id,
                values=(
                    task.get("nome", ""),
                    f"{task.get('horario_inicio', '')} at\u00e9 {task.get('horario_limite', '')}",
                    state["status"],
                    task.get("nome_setor", ""),
                    "Ver observação" if _row_has_observation(task) else "",
                ),
                tags=(state["tag"],),
            )
        if selected and self.task_tree.exists(selected):
            self.task_tree.selection_set(selected)
        self._update_task_observation_button()

    def _checked_task_ids_for_collaborator(self, colaborador_id: str) -> set[str]:
        if not colaborador_id:
            return set()
        return {
            str(row.get("tarefa_id", ""))
            for row in self.task_service.checks_for_date()
            if str(row.get("colaborador_id", "")) == colaborador_id
        }

    def _collaborator_task_state(self, task: dict, checked_task_ids: set[str]) -> dict:
        tarefa_id = str(task.get("tarefa_id", ""))
        if tarefa_id in checked_task_ids:
            return {"status": "cumprida", "tag": "done"}
        state = self.task_service.task_display_state(task)
        status = str(state.get("status", ""))
        if status == TASK_STATUS_DONE:
            return {"status": "cumprida", "tag": "done"}
        if status in {TASK_STATUS_LATE, TASK_STATUS_MISSED}:
            return {"status": "atrasada", "tag": "late"}
        if status in {TASK_STATUS_IN_PROGRESS, TASK_STATUS_TOLERANCE, TASK_STATUS_PARTIAL}:
            return {"status": "em hor\u00e1rio", "tag": "running"}
        return {"status": "pendente", "tag": "pending"}

    def _selected_task_id(self) -> str | None:
        selected = self.task_tree.selection()
        return str(selected[0]) if selected else None

    def _selected_task(self) -> dict | None:
        task_id = self._selected_task_id()
        return self._current_tasks.get(task_id or "")

    def _update_task_observation_button(self) -> None:
        if not hasattr(self, "task_observation_button"):
            return
        task = self._selected_task()
        has_observation = _row_has_observation(task or {})
        self.task_observation_button.configure(state="normal" if has_observation else "disabled")

    def _show_selected_task_observation_if_available(self) -> None:
        if _row_has_observation(self._selected_task() or {}):
            self._show_selected_task_observation()

    def _handle_task_tree_click(self, event) -> None:
        if self.task_tree.identify_region(event.x, event.y) != "cell":
            return
        if self.task_tree.identify_column(event.x) != "#5":
            return
        task_id = self.task_tree.identify_row(event.y)
        if not task_id:
            return
        self.task_tree.selection_set(task_id)
        self.task_tree.focus(task_id)
        self._update_task_observation_button()
        task = self._current_tasks.get(str(task_id))
        if task:
            self._show_task_observation(task)

    def _show_selected_task_observation(self) -> None:
        task = self._selected_task()
        self._show_task_observation(task or {})
        return
        if not task:
            messagebox.showwarning("Observação", "Selecione uma tarefa.")
            return
        observation = _observation_text(task)
        if not observation:
            messagebox.showinfo("Observação", "Esta tarefa não possui observação cadastrada.")
            return
        ObservationDialog(
            self,
            f"Observação - {task.get('nome', 'Tarefa')}",
            observation,
        )

    def _show_task_observation(self, task: dict) -> None:
        if not task:
            messagebox.showwarning("Observação", "Selecione uma tarefa.")
            return
        observation = _observation_text(task)
        if not observation:
            messagebox.showinfo("Observação", "Esta tarefa não possui observações cadastradas.")
            return
        ObservationDialog(
            self,
            "Observações da tarefa",
            _format_task_observation(task),
        )

    def _collaborator_observation_sections(self) -> list[tuple[str, str]]:
        collaborator = self._selected_collaborator()
        if not collaborator:
            return []
        sections = [("Colaborador", _observation_text(collaborator))]
        jornada_id = str(collaborator.get("jornada_id", "") or "").strip()
        if self.journey_service and jornada_id:
            try:
                journey = self.journey_service.get(jornada_id)
            except Exception:
                journey = None
            if journey:
                label = str(journey.get("nome", "") or "Jornada / Escala")
                sections.append((f"Jornada / Escala - {label}", _observation_text(journey)))
        return [(title, text) for title, text in sections if text]

    def _update_collaborator_observation_button(self) -> None:
        if not hasattr(self, "collaborator_observation_button"):
            return
        has_observations = bool(self._collaborator_observation_sections())
        self.collaborator_observation_button.configure(state="normal" if has_observations else "disabled")

    def _show_collaborator_observations(self) -> None:
        sections = self._collaborator_observation_sections()
        if not sections:
            messagebox.showinfo("Observações", "Este colaborador não possui observações cadastradas.")
            return
        ObservationDialog(self, "Observações do colaborador", _format_observation_sections(sections))

    def _mark_selected_task_done(self) -> None:
        collaborator = self._selected_collaborator()
        if not collaborator:
            messagebox.showwarning("Tarefas", "Selecione um colaborador.")
            return
        task_id = self._selected_task_id()
        if not task_id:
            messagebox.showwarning("Tarefas", "Selecione uma tarefa.")
            return
        try:
            self.task_service.mark_done(task_id, str(collaborator.get("colaborador_id")))
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message)
            return
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))
            return
        messagebox.showinfo("Tarefas", "Tarefa marcada como feita.")
        self.refresh()

    def _schedule_auto_refresh(self) -> None:
        if self._auto_refresh_after:
            try:
                self.after_cancel(self._auto_refresh_after)
            except tk.TclError:
                pass
        self._auto_refresh_after = self.after(60000, self._auto_refresh)

    def _auto_refresh(self) -> None:
        self._auto_refresh_after = None
        try:
            if not self.winfo_exists():
                return
            self._update_point_context()
            self._refresh_tasks()
            self._update_bot_status()
            self._schedule_auto_refresh()
        except tk.TclError:
            return

    def _update_bot_status(self) -> None:
        status = str(self.bot_service.status() or "Desconectado")
        self._bot_status_var.set(f"WhatsApp: {status}")
        if not hasattr(self, "bot_status_button"):
            return
        normalized = status.strip().lower()
        if normalized == "conectado":
            style = "success-outline"
        elif normalized in {"aguardando qr code", "autenticado", "reconectando sessão", "aquecendo", "conectando"}:
            style = "warning-outline"
        elif normalized == "erro":
            style = "danger-outline"
        else:
            style = "secondary-outline"
        self.bot_status_button.configure(bootstyle=style)

    def _schedule_bot_status_refresh(self) -> None:
        if self._bot_status_after:
            try:
                self.after_cancel(self._bot_status_after)
            except tk.TclError:
                pass
        self._bot_status_after = self.after(5000, self._auto_refresh_bot_status)

    def _auto_refresh_bot_status(self) -> None:
        self._bot_status_after = None
        try:
            if not self.winfo_exists():
                return
            self._update_bot_status()
            self._schedule_bot_status_refresh()
        except tk.TclError:
            return

    def _on_destroy(self, event) -> None:
        if event.widget is not self:
            return
        if self._auto_refresh_after:
            try:
                self.after_cancel(self._auto_refresh_after)
            except tk.TclError:
                pass
            self._auto_refresh_after = None
        if self._bot_status_after:
            try:
                self.after_cancel(self._bot_status_after)
            except tk.TclError:
                pass
            self._bot_status_after = None

    def _bind_tree_mousewheel(self) -> None:
        self.task_tree.bind_all("<MouseWheel>", lambda event: self.task_tree.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        self.task_tree.bind_all("<Shift-MouseWheel>", lambda event: self.task_tree.xview_scroll(int(-1 * (event.delta / 120)), "units"))

    def _unbind_tree_mousewheel(self) -> None:
        self.task_tree.unbind_all("<MouseWheel>")
        self.task_tree.unbind_all("<Shift-MouseWheel>")


def _observation_text(row: dict) -> str:
    for key, value in row.items():
        if _normalize_field_key(key) in {"observacoes", "observacao"}:
            text = str(value or "").strip()
            if text:
                return text
    return ""


def _row_has_observation(row: dict) -> bool:
    return bool(_observation_text(row))


def _format_task_observation(task: dict) -> str:
    name = str(task.get("nome", "") or "Tarefa").strip()
    description = str(task.get("descricao", "") or "").strip()
    start = str(task.get("horario_inicio", "") or "").strip()
    limit = str(task.get("horario_limite", "") or "").strip()
    observation = _observation_text(task) or "Esta tarefa nao possui observacoes cadastradas."
    lines = [f"Tarefa: {name}"]
    if start or limit:
        lines.append(f"Horario: {start} ate {limit}".strip())
    if description:
        lines.extend(["", "Descricao:", description])
    lines.extend(["", "Observacao:", observation])
    return "\n".join(lines)


def _format_observation_sections(sections: list[tuple[str, str]]) -> str:
    parts = []
    for title, text in sections:
        clean_title = str(title or "").strip()
        clean_text = str(text or "").strip()
        if not clean_text:
            continue
        parts.append(f"{clean_title}\n{'=' * len(clean_title)}\n{clean_text}" if clean_title else clean_text)
    return "\n\n".join(parts)


def _normalize_field_key(value: object) -> str:
    text = str(value or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.replace("ç", "c")
    return "".join(char for char in normalized if char.isalnum() or char == "_")
