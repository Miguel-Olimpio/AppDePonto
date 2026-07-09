"""Painel de checagem de tarefas do dia."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

import ttkbootstrap as ttb

from app.repositories.excel_database import ExcelSaveError
from app.services.collaborator_service import CollaboratorService
from app.services.task_service import TaskService


class TaskCheckPanel(ttb.Frame):
    def __init__(
        self,
        master: tk.Misc,
        collaborator_service: CollaboratorService,
        task_service: TaskService,
        on_change=None,
    ):
        super().__init__(master)
        self.collaborator_service = collaborator_service
        self.task_service = task_service
        self.on_change = on_change
        self._present_vars: dict[str, tk.BooleanVar] = {}
        self._present_rows: list[dict] = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        top = ttb.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        ttb.Label(top, text="Checagem de tarefas de hoje", font=("Segoe UI", 12, "bold")).pack(side="left")
        ttb.Button(top, text="Verificar tarefas pendentes", command=self._verify_pending, bootstyle="warning").pack(
            side="right"
        )

        columns = ("nome", "horario", "tolerancia", "status", "setor")
        table_frame = ttb.Frame(self)
        table_frame.pack(fill="both", expand=True)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        y_scroll = ttb.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttb.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        for col, text, width in [
            ("nome", "Tarefa", 220),
            ("horario", "Horário", 150),
            ("tolerancia", "Tolerância", 100),
            ("status", "Status", 130),
            ("setor", "Setor", 120),
        ]:
            self.tree.heading(col, text=text, anchor="center")
            self.tree.column(col, width=width, anchor="center", minwidth=70)

        self.tree.tag_configure("running", background="#FFF3C4")
        self.tree.tag_configure("late", background="#FFD6D6")
        self.tree.tag_configure("done", background="#D8F5D0")
        self.tree.tag_configure("pending", background="#F1F5F9")
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._load_present_collaborators())
        self.tree.bind("<Enter>", lambda _event: self._bind_tree_mousewheel())
        self.tree.bind("<Leave>", lambda _event: self._unbind_tree_mousewheel())

        present_box = ttb.Labelframe(self, text="Colaboradores presentes para a tarefa selecionada", padding=10)
        present_box.pack(fill="x", pady=(10, 0))
        self.present_frame = ttb.Frame(present_box)
        self.present_frame.pack(fill="x")

        actions = ttb.Frame(present_box)
        actions.pack(fill="x", pady=(8, 0))
        ttb.Button(
            actions,
            text="Marcar selecionados como cumpriram",
            command=self._mark_done,
            bootstyle="primary",
        ).pack(side="left")
        self.present_hint = ttb.Label(
            actions,
            text="Selecione uma tarefa para visualizar quem está presente.",
            foreground="#64748B",
        )
        self.present_hint.pack(side="left", padx=(12, 0))

    def refresh(self) -> None:
        selected = self._selected_task_id()
        self.tree.delete(*self.tree.get_children())
        for task in self.task_service.tasks_for_date():
            state = self.task_service.task_display_state(task)
            tolerance = int(task.get("tolerancia_minutos") or 0)
            self.tree.insert(
                "",
                "end",
                iid=str(task.get("tarefa_id")),
                values=(
                    task.get("nome", ""),
                    f"{task.get('horario_inicio', '')} até {task.get('horario_limite', '')}",
                    f"{tolerance} min",
                    state["status"],
                    task.get("nome_setor", ""),
                ),
                tags=(state["tag"],),
            )
        if selected and self.tree.exists(selected):
            self.tree.selection_set(selected)
            self._load_present_collaborators()
        else:
            self._clear_present_collaborators()

    def _selected_task_id(self) -> str | None:
        selected = self.tree.selection()
        return str(selected[0]) if selected else None

    def _load_present_collaborators(self) -> None:
        self._clear_present_collaborators()
        task_id = self._selected_task_id()
        if not task_id:
            return

        self._present_rows = self.task_service.collaborators_for_task_check(task_id)
        if not self._present_rows:
            self.present_hint.configure(text="Nenhum colaborador presente agora para esta tarefa.")
            return

        for idx, collaborator in enumerate(self._present_rows):
            collaborator_id = str(collaborator.get("colaborador_id", ""))
            var = tk.BooleanVar(value=True)
            self._present_vars[collaborator_id] = var
            ttb.Checkbutton(
                self.present_frame,
                text=str(collaborator.get("nome", "")),
                variable=var,
                bootstyle="primary",
            ).grid(row=idx // 3, column=idx % 3, sticky="w", padx=(0, 18), pady=3)
        self.present_hint.configure(text="Marque todos os colaboradores que participaram/cumpriram a tarefa.")

    def _clear_present_collaborators(self) -> None:
        for child in self.present_frame.winfo_children():
            child.destroy()
        self._present_vars = {}
        self._present_rows = []
        self.present_hint.configure(text="Selecione uma tarefa para visualizar quem está presente.")

    def _mark_done(self) -> None:
        task_id = self._selected_task_id()
        if not task_id:
            messagebox.showwarning("Tarefas", "Selecione uma tarefa.")
            return

        selected_ids = [collaborator_id for collaborator_id, var in self._present_vars.items() if var.get()]
        if not selected_ids:
            messagebox.showwarning("Tarefas", "Selecione pelo menos um colaborador presente.")
            return

        try:
            checks = self.task_service.mark_done_for_collaborators(task_id, selected_ids)
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message)
            return
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))
            return

        messagebox.showinfo("Tarefas", f"Checagens registradas: {len(checks)}.")
        self.refresh()
        if self.on_change:
            self.on_change()

    def _verify_pending(self) -> None:
        try:
            created = self.task_service.verify_pending_tasks()
        except ExcelSaveError as exc:
            messagebox.showerror("Erro ao salvar", exc.user_message)
            return
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))
            return
        messagebox.showinfo("Tarefas", f"Ocorrências criadas: {len(created)}.")
        self.refresh()
        if self.on_change:
            self.on_change()

    def _bind_tree_mousewheel(self) -> None:
        self.tree.bind_all("<MouseWheel>", lambda event: self.tree.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        self.tree.bind_all("<Shift-MouseWheel>", lambda event: self.tree.xview_scroll(int(-1 * (event.delta / 120)), "units"))

    def _unbind_tree_mousewheel(self) -> None:
        self.tree.unbind_all("<MouseWheel>")
        self.tree.unbind_all("<Shift-MouseWheel>")
