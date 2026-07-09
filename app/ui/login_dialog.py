"""Login simples da area administrativa."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttb

from app.ui.window_icon import apply_window_icon

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"


def validate_admin_credentials(username: str, password: str) -> bool:
    return username.strip() == ADMIN_USERNAME and password == ADMIN_PASSWORD


class AdminLoginDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, on_success):
        super().__init__(master)
        self.title("Acesso do administrador")
        self.geometry("560x460")
        self.minsize(500, 380)
        self.resizable(True, True)
        apply_window_icon(self)
        self.transient(master.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.on_success = on_success
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self._build()
        self.grab_set()
        self.focus_force()
        self.user_entry.focus_set()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        outer = ttb.Frame(self, padding=(14, 14, 10, 8))
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        canvas = tk.Canvas(outer, highlightthickness=0, borderwidth=0)
        scrollbar = ttb.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(8, 0))

        container = ttb.Frame(canvas, padding=18)
        window_id = canvas.create_window((0, 0), window=container, anchor="nw")
        container.columnconfigure(0, weight=1)

        def _update_scrollregion(_event=None) -> None:
            if canvas.winfo_exists():
                canvas.configure(scrollregion=canvas.bbox("all"))

        def _resize_inner(event) -> None:
            if canvas.winfo_exists():
                canvas.itemconfigure(window_id, width=event.width)

        def _on_mousewheel(event) -> None:
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                return

        container.bind("<Configure>", _update_scrollregion)
        canvas.bind("<Configure>", _resize_inner)
        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))
        canvas.bind("<Destroy>", lambda _event: canvas.unbind_all("<MouseWheel>"), add="+")

        ttb.Label(container, text="Área do administrador", font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttb.Label(
            container,
            text="Informe usuário e senha para acessar cadastros, jornada, dashboard e ocorrências.",
            foreground="#64748B",
            wraplength=460,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 18))

        form = ttb.Labelframe(container, text="Login", padding=14)
        form.grid(row=2, column=0, sticky="ew")
        form.columnconfigure(0, weight=1)

        ttb.Label(form, text="Usuário").grid(row=0, column=0, sticky="w")
        self.user_entry = ttb.Entry(form, textvariable=self.username_var)
        self.user_entry.grid(row=1, column=0, sticky="ew", pady=(4, 12))

        ttb.Label(form, text="Senha").grid(row=2, column=0, sticky="w")
        password_entry = ttb.Entry(form, textvariable=self.password_var, show="*")
        password_entry.grid(row=3, column=0, sticky="ew", pady=(4, 4))
        password_entry.bind("<Return>", lambda _event: self._try_login())

        actions = ttb.Frame(self, padding=(14, 8, 14, 14))
        actions.grid(row=1, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)
        ttb.Button(actions, text="Cancelar", command=self._close, bootstyle="secondary-outline").grid(
            row=0, column=1, sticky="e", padx=(8, 0)
        )
        ttb.Button(actions, text="Entrar", command=self._try_login, bootstyle="primary").grid(
            row=0, column=2, sticky="e"
        )

    def _close(self) -> None:
        try:
            self.unbind_all("<MouseWheel>")
        except tk.TclError:
            pass
        self.destroy()

    def _try_login(self) -> None:
        if not validate_admin_credentials(self.username_var.get(), self.password_var.get()):
            messagebox.showwarning("Login", "Usuário ou senha inválidos.", parent=self)
            return
        self._close()
        self.on_success()
