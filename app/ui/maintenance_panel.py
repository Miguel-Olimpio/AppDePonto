"""Painel administrativo de manutencao e limpeza controlada."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttb

from app.services.maintenance_service import (
    DEFAULT_MAX_PDFS_PER_FOLDER,
    DEFAULT_RETENTION_MONTHS,
    MaintenanceService,
)

BACKGROUND = "#F4F8FC"
MUTED = "#64748B"


class MaintenancePanel(ttb.Frame):
    def __init__(self, master: tk.Misc, maintenance_service: MaintenanceService):
        super().__init__(master, style="Content.TFrame")
        self.maintenance_service = maintenance_service
        self.retention_var = tk.StringVar(value=str(DEFAULT_RETENTION_MONTHS))
        self.max_pdfs_var = tk.StringVar(value=str(DEFAULT_MAX_PDFS_PER_FOLDER))
        self.summary_var = tk.StringVar(value="Nenhuma manutenção executada nesta sessão.")
        self._build()

    def _build(self) -> None:
        ttb.Label(
            self,
            text="Manutenção",
            font=("Segoe UI", 16, "bold"),
            foreground="#003F7D",
            background=BACKGROUND,
        ).pack(anchor="w")
        ttb.Label(
            self,
            text=(
                "Arquive dados antigos antes de compactar as planilhas. "
                "Cadastros de colaboradores, jornadas, setores e tarefas não são removidos."
            ),
            foreground=MUTED,
            background=BACKGROUND,
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(2, 12))

        config = ttb.Labelframe(self, text="Configuração", padding=12)
        config.pack(fill="x", pady=(0, 12))
        ttb.Label(config, text="Manter meses ativos").grid(row=0, column=0, sticky="w")
        ttb.Entry(config, textvariable=self.retention_var, width=8).grid(row=1, column=0, sticky="w", padx=(0, 20))
        ttb.Label(config, text="Máximo de PDFs por pasta").grid(row=0, column=1, sticky="w")
        ttb.Entry(config, textvariable=self.max_pdfs_var, width=8).grid(row=1, column=1, sticky="w", padx=(0, 20))
        config.columnconfigure(2, weight=1)

        actions = ttb.Labelframe(self, text="Ações", padding=12)
        actions.pack(fill="x", pady=(0, 12))
        ttb.Button(actions, text="Executar manutenção agora", command=self._run_all, bootstyle="primary").pack(
            side="left", padx=(0, 8)
        )
        ttb.Button(actions, text="Arquivar dados antigos", command=self._archive_data, bootstyle="secondary-outline").pack(
            side="left", padx=(0, 8)
        )
        ttb.Button(actions, text="Limpar PDFs antigos", command=self._cleanup_pdfs, bootstyle="secondary-outline").pack(
            side="left", padx=(0, 8)
        )
        ttb.Button(actions, text="Limpar logs", command=self._cleanup_logs, bootstyle="secondary-outline").pack(side="left")

        result = ttb.Labelframe(self, text="Resultado", padding=12)
        result.pack(fill="both", expand=True)
        ttb.Label(result, textvariable=self.summary_var, foreground=MUTED, wraplength=900, justify="left").pack(
            anchor="nw", fill="x"
        )

    def _retention_months(self) -> int:
        try:
            value = int(float(self.retention_var.get().replace(",", ".")))
        except ValueError as exc:
            raise ValueError("Informe um número válido de meses ativos.") from exc
        return max(value, 1)

    def _max_pdfs(self) -> int:
        try:
            value = int(float(self.max_pdfs_var.get().replace(",", ".")))
        except ValueError as exc:
            raise ValueError("Informe um número válido para máximo de PDFs.") from exc
        return max(value, 1)

    def _run_all(self) -> None:
        if not messagebox.askyesno("Manutenção", "Executar manutenção agora? Dados antigos serão arquivados antes da remoção das planilhas ativas."):
            return
        try:
            summary = self.maintenance_service.run(self._retention_months(), self._max_pdfs())
        except Exception as exc:
            messagebox.showerror("Manutenção", str(exc))
            return
        self.summary_var.set(_format_summary(summary))
        messagebox.showinfo("Manutenção", "Manutenção concluída.")

    def _archive_data(self) -> None:
        try:
            summary = self.maintenance_service.archive_old_data(self._retention_months())
        except Exception as exc:
            messagebox.showerror("Manutenção", str(exc))
            return
        self.summary_var.set(f"Dados arquivados: {summary or 'nenhum registro antigo encontrado.'}")

    def _cleanup_pdfs(self) -> None:
        try:
            removed = self.maintenance_service.cleanup_pdfs(self._max_pdfs())
        except Exception as exc:
            messagebox.showerror("Manutenção", str(exc))
            return
        self.summary_var.set(f"PDFs removidos: {removed}.")

    def _cleanup_logs(self) -> None:
        try:
            summary = self.maintenance_service.cleanup_logs()
        except Exception as exc:
            messagebox.showerror("Manutenção", str(exc))
            return
        self.summary_var.set(f"Logs: {summary}.")


def _format_summary(summary: dict) -> str:
    return (
        f"Executado em: {summary.get('executado_em', '-')}\n"
        f"Registros arquivados: {summary.get('arquivados') or 'nenhum'}\n"
        f"PDFs removidos: {summary.get('pdfs_removidos', 0)}\n"
        f"Logs: {summary.get('logs') or 'nenhum'}"
    )
