"""Estado simples de navegação entre colaborador e administrador."""

from __future__ import annotations

APP_MODE_COLLABORATOR = "colaborador"
APP_MODE_ADMIN = "administrador"


class AppModeState:
    def __init__(self) -> None:
        self.mode = APP_MODE_COLLABORATOR

    def enter_admin(self) -> None:
        self.mode = APP_MODE_ADMIN

    def exit_admin(self) -> None:
        self.mode = APP_MODE_COLLABORATOR

    @property
    def is_admin(self) -> bool:
        return self.mode == APP_MODE_ADMIN
