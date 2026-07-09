from __future__ import annotations

from datetime import datetime

from app.ui.app_mode import APP_MODE_ADMIN, APP_MODE_COLLABORATOR, AppModeState
from app.ui.login_dialog import validate_admin_credentials


def test_app_mode_starts_as_collaborator():
    state = AppModeState()

    assert state.mode == APP_MODE_COLLABORATOR
    assert not state.is_admin


def test_admin_credentials_allow_only_fixed_login():
    assert validate_admin_credentials("admin", "admin") is True
    assert validate_admin_credentials(" admin ", "admin") is True
    assert validate_admin_credentials("admin", "errada") is False
    assert validate_admin_credentials("colaborador", "admin") is False


def test_logout_admin_returns_to_collaborator_mode():
    state = AppModeState()

    state.enter_admin()
    assert state.mode == APP_MODE_ADMIN
    assert state.is_admin

    state.exit_admin()
    assert state.mode == APP_MODE_COLLABORATOR
    assert not state.is_admin


def test_collaborator_operational_flow_records_point_and_checks_task(stack):
    collaborator = stack["collaborators"].create_collaborator("Ana Operacional", setor="Atendimento")
    task = stack["tasks"].create_task("Abrir loja", nome_setor="Todos", horario_inicio="08:00", horario_limite="09:00")

    point = stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    check = stack["tasks"].mark_done(task["tarefa_id"], collaborator["colaborador_id"], when=datetime(2026, 5, 4, 8, 30))

    assert point["tipo_ponto"] == "entrada"
    assert point["nome_colaborador"] == "Ana Operacional"
    assert check["nome_tarefa"] == "Abrir loja"
    assert check["nome_colaborador"] == "Ana Operacional"


def test_admin_services_still_support_collaborator_and_task_registration(stack):
    collaborator = stack["collaborators"].create_collaborator("Gestor Teste", setor="Atendimento", cargo="Gerente")
    task = stack["tasks"].create_task("Conferir caixa", nome_setor="Todos", horario_inicio="10:00", horario_limite="11:00")

    assert stack["collaborators"].get(collaborator["colaborador_id"])["cargo"] == "Gerente"
    assert any(row["tarefa_id"] == task["tarefa_id"] for row in stack["tasks"].list_tasks())
