"""Modal somente leitura para observacoes administrativas."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import ttkbootstrap as ttb

from app.ui.window_icon import apply_window_icon


class ObservationDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, title: str, text: str):
        super().__init__(master)
        self.title(title)
        self.geometry("760x520")
        self.minsize(520, 360)
        self.resizable(True, True)
        apply_window_icon(self)
        self.transient(master.winfo_toplevel())
        self.grab_set()

        container = ttb.Frame(self, padding=14)
        container.pack(fill="both", expand=True)
        container.rowconfigure(1, weight=1)
        container.columnconfigure(0, weight=1)

        ttb.Label(container, text=title, font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))

        text_frame = ttb.Frame(container)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        self.text_box = tk.Text(
            text_frame,
            wrap="word",
            height=16,
            borderwidth=1,
            relief="solid",
            padx=10,
            pady=10,
            font=("Segoe UI", 10),
        )
        y_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.text_box.yview)
        x_scroll = ttk.Scrollbar(text_frame, orient="horizontal", command=self.text_box.xview)
        self.text_box.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.text_box.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.text_box.insert("1.0", text.strip() or "Nenhuma observacao cadastrada.")
        self.text_box.configure(state="disabled")

        actions = ttb.Frame(container)
        actions.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        ttb.Label(
            actions,
            text="Texto somente leitura. Use Ctrl+C para copiar trechos selecionados.",
            foreground="#64748B",
        ).pack(side="left")
        ttb.Button(actions, text="Fechar", command=self.destroy, bootstyle="secondary-outline").pack(side="right")

        self.bind("<Escape>", lambda _event: self.destroy())
        self.after(50, self._focus_text)

    def _focus_text(self) -> None:
        try:
            self.lift()
            self.focus_force()
            self.text_box.focus_set()
        except tk.TclError:
            return
