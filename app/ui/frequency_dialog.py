"""Consulta administrativa de frequencia usando o calculo do relatorio mensal."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

import ttkbootstrap as ttb

from app.services.monthly_report_service import MonthlyReportService
from app.ui.window_icon import apply_window_icon
from app.utils.open_file_location import prompt_open_generated_file


class FrequencyDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, monthly_report_service: MonthlyReportService, month_text: str):
        super().__init__(master)
        self.monthly_report_service = monthly_report_service
        self.report: dict = {}
        self.rows_by_id: dict[str, dict] = {}
        self.title("Consulta de frequência")
        self.geometry("1180x760")
        self.minsize(980, 620)
        self.resizable(True, True)
        apply_window_icon(self)
        self.transient(master.winfo_toplevel())
        self.grab_set()

        self.month_var = tk.StringVar(value=month_text)
        self.collaborator_var = tk.StringVar(value="Todos")

        self._build()
        self.refresh()
        self.bind("<Escape>", lambda _event: self.destroy())

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        filters = ttb.Frame(self, padding=(14, 12))
        filters.grid(row=0, column=0, sticky="ew")
        ttb.Label(filters, text="Mês/Ano").pack(side="left")
        ttb.Entry(filters, textvariable=self.month_var, width=10).pack(side="left", padx=(6, 14))
        ttb.Label(filters, text="Colaborador").pack(side="left")
        self.collaborator_combo = ttb.Combobox(filters, textvariable=self.collaborator_var, state="readonly", width=34)
        self.collaborator_combo.pack(side="left", padx=(6, 14))
        self.collaborator_combo.bind("<<ComboboxSelected>>", lambda _event: self._fill_summary())
        ttb.Button(filters, text="Atualizar", command=self.refresh, bootstyle="primary").pack(side="left")
        ttb.Button(filters, text="Gerar PDF deste período", command=self._generate_pdf, bootstyle="info-outline").pack(
            side="left", padx=(8, 0)
        )
        ttb.Button(filters, text="Fechar", command=self.destroy, bootstyle="secondary-outline").pack(side="right")

        body = ttb.Panedwindow(self, orient="vertical")
        body.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))

        summary_box = ttb.Labelframe(body, text="Resumo de frequência", padding=10)
        summary_box.rowconfigure(0, weight=1)
        summary_box.columnconfigure(0, weight=1)
        body.add(summary_box, weight=3)

        columns = (
            "colaborador",
            "esperados",
            "trabalhados",
            "faltas",
            "abonadas",
            "nao_abonadas",
            "atrasos",
            "retornos",
            "tarefas",
            "bonus_assiduidade",
            "bonus_tarefas",
            "salario",
        )
        self.summary_tree = ttk.Treeview(summary_box, columns=columns, show="headings", height=12)
        y_scroll = ttb.Scrollbar(summary_box, orient="vertical", command=self.summary_tree.yview)
        x_scroll = ttb.Scrollbar(summary_box, orient="horizontal", command=self.summary_tree.xview)
        self.summary_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.summary_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        for col, label, width in [
            ("colaborador", "Colaborador", 210),
            ("esperados", "Dias esperados", 110),
            ("trabalhados", "Dias trabalhados", 120),
            ("faltas", "Faltas", 80),
            ("abonadas", "Faltas abonadas", 120),
            ("nao_abonadas", "Faltas não abonadas", 135),
            ("atrasos", "Atrasos", 80),
            ("retornos", "Retornos atrasados", 135),
            ("tarefas", "Tarefas atrasadas/não cumpridas", 190),
            ("bonus_assiduidade", "Bônus assiduidade", 145),
            ("bonus_tarefas", "Bônus tarefas", 120),
            ("salario", "Salário estimado", 130),
        ]:
            self.summary_tree.heading(col, text=label, anchor="center")
            self.summary_tree.column(col, width=width, minwidth=70, anchor="center")
        self.summary_tree.bind("<<TreeviewSelect>>", lambda _event: self._show_selected_details())
        self.summary_tree.bind("<Enter>", lambda _event: self._bind_tree_mousewheel(self.summary_tree))
        self.summary_tree.bind("<Leave>", lambda _event: self._unbind_tree_mousewheel(self.summary_tree))

        detail_box = ttb.Labelframe(body, text="Detalhamento do colaborador selecionado", padding=10)
        detail_box.rowconfigure(0, weight=1)
        detail_box.columnconfigure(0, weight=1)
        body.add(detail_box, weight=2)

        self.detail_text = tk.Text(detail_box, wrap="word", height=12, padx=10, pady=10, font=("Segoe UI", 10))
        detail_scroll = ttb.Scrollbar(detail_box, orient="vertical", command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=detail_scroll.set)
        self.detail_text.grid(row=0, column=0, sticky="nsew")
        detail_scroll.grid(row=0, column=1, sticky="ns")
        self.detail_text.configure(state="disabled")

    def refresh(self) -> None:
        try:
            self.report = self.monthly_report_service.calculate_month(self.month_var.get())
        except Exception as exc:
            messagebox.showerror("Frequência", f"Não foi possível carregar a frequência.\n\n{exc}", parent=self)
            return
        rows = self.report.get("colaboradores", [])
        options = ["Todos"] + [str(row.get("nome", "")) for row in rows]
        self.collaborator_combo.configure(values=options)
        if self.collaborator_var.get() not in options:
            self.collaborator_var.set("Todos")
        self._fill_summary()

    def _fill_summary(self) -> None:
        selected = self.summary_tree.selection()[0] if self.summary_tree.selection() else ""
        self.summary_tree.delete(*self.summary_tree.get_children())
        self.rows_by_id = {}
        for row in self._filtered_rows():
            collaborator_id = str(row.get("colaborador_id", ""))
            self.rows_by_id[collaborator_id] = row
            self.summary_tree.insert(
                "",
                "end",
                iid=collaborator_id,
                values=(
                    row.get("nome", ""),
                    row.get("dias_esperados", 0),
                    row.get("dias_trabalhados", 0),
                    row.get("faltas", 0),
                    row.get("faltas_abonadas", 0),
                    row.get("faltas_nao_abonadas", 0),
                    row.get("atrasos", 0),
                    row.get("retornos_pausa_atrasados", 0),
                    int(row.get("tarefas_atrasadas", 0) or 0) + int(row.get("tarefas_nao_cumpridas", 0) or 0),
                    _bonus_status(row.get("bonus_assiduidade_aplicado")),
                    _bonus_status(row.get("bonus_tarefas_aplicado")),
                    _money(row.get("salario_final")),
                ),
            )
        if selected and self.summary_tree.exists(selected):
            self.summary_tree.selection_set(selected)
        elif self.summary_tree.get_children():
            self.summary_tree.selection_set(self.summary_tree.get_children()[0])
        self._show_selected_details()

    def _filtered_rows(self) -> list[dict]:
        selected = self.collaborator_var.get()
        rows = list(self.report.get("colaboradores", []))
        if selected and selected != "Todos":
            rows = [row for row in rows if str(row.get("nome", "")) == selected]
        return rows

    def _show_selected_details(self) -> None:
        selected = self.summary_tree.selection()
        row = self.rows_by_id.get(str(selected[0])) if selected else None
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", _detail_text(row) if row else "Selecione um colaborador.")
        self.detail_text.configure(state="disabled")

    def _generate_pdf(self) -> None:
        try:
            path = self.monthly_report_service.generate_payment_pdf(self.month_var.get())
        except Exception as exc:
            messagebox.showerror("Relatório de pagamento", f"Não foi possível gerar o PDF.\n\n{exc}", parent=self)
            return
        prompt_open_generated_file(self, path, title="Relatório de pagamento", message_prefix="PDF salvo em:")

    def _bind_tree_mousewheel(self, tree: ttk.Treeview) -> None:
        tree.bind_all("<MouseWheel>", lambda event: tree.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        tree.bind_all("<Shift-MouseWheel>", lambda event: tree.xview_scroll(int(-1 * (event.delta / 120)), "units"))

    def _unbind_tree_mousewheel(self, tree: ttk.Treeview) -> None:
        tree.unbind_all("<MouseWheel>")
        tree.unbind_all("<Shift-MouseWheel>")


def _detail_text(row: dict) -> str:
    lines = [
        f"Colaborador: {row.get('nome', '')}",
        f"Jornada: {row.get('jornada', '-') or '-'}",
        "",
        f"Dias trabalhados: {_join(row.get('datas_trabalhadas', []))}",
        f"Datas de falta: {_join(row.get('dias_falta', []))}",
        f"Faltas abonadas: {_join(row.get('dias_falta_abonada', []))}",
        "",
        "Faltas abonadas e motivos:",
    ]
    excused = row.get("faltas_abonadas_detalhes", [])
    if excused:
        for item in excused:
            lines.append(f"- {item.get('data', '')}: {item.get('motivo', '') or '-'} {item.get('observacao', '') or ''}".strip())
    else:
        lines.append("- Nenhuma.")
    lines.extend(["", "Faltas não abonadas:"])
    unexcused = row.get("faltas_nao_abonadas_detalhes", [])
    if unexcused:
        for item in unexcused:
            lines.append(f"- {item.get('data', '')}: {item.get('motivo', '') or '-'}")
    else:
        lines.append("- Nenhuma.")
    lines.extend(["", "Ocorrências do período:"])
    occurrences = row.get("ocorrencias_periodo_detalhes", [])
    if occurrences:
        for item in occurrences:
            lines.append(f"- {item.get('data', '')} | {item.get('tipo', '')}: {item.get('descricao', '')}")
    else:
        lines.append("- Nenhuma.")
    lines.extend(["", "Tarefas atrasadas/não cumpridas:"])
    task_failures = row.get("tarefas_falhas_detalhes", [])
    if task_failures:
        for item in task_failures:
            lines.append(f"- {item.get('data', '')} | {item.get('tarefa', '-')}: {item.get('descricao', '')}")
    else:
        lines.append("- Nenhuma.")
    lines.extend(["", "Impacto nos bônus:", str(row.get("mensagem_assiduidade", "")), str(row.get("mensagem_tarefas", ""))])
    return "\n".join(lines)


def _join(values) -> str:
    values = [str(value) for value in values if str(value or "").strip()]
    return ", ".join(values) if values else "-"


def _bonus_status(value) -> str:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0.0
    return f"Aplicado ({_money(amount)})" if amount > 0 else "Perdido"


def _money(value) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0.0
    return f"R$ {number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
