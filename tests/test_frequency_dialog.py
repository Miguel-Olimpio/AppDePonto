from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.config.settings import OCCURRENCE_POINT_MISSING
from app.ui.frequency_dialog import _detail_text


def test_admin_dashboard_has_frequency_button():
    source = (Path(__file__).resolve().parents[1] / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")

    assert "Ver frequência" in source
    assert "_show_frequency_report" in source
    assert "FrequencyDialog" in source


def test_frequency_uses_monthly_report_details(stack):
    journey = stack["journeys"].create_journey("Segundas", entrada="08:00", saida="17:00", dias_semana="segunda")
    collaborator = stack["collaborators"].create_collaborator(
        "Consulta Frequencia",
        setor="Atendimento",
        salario_base=1000,
        jornada_id=journey["jornada_id"],
        bonus_assiduidade=100,
        bonus_tarefas=80,
    )
    expected_days = stack["journeys"].expected_workdays(journey, "01/06/2026", "30/06/2026")
    absent_day = expected_days[0]
    worked_day = expected_days[1]
    stack["time"].record_time(
        collaborator["colaborador_id"],
        "entrada",
        when=datetime(worked_day.year, worked_day.month, worked_day.day, 8, 0),
    )
    occurrence = stack["occurrences"].create_occurrence(
        tipo=OCCURRENCE_POINT_MISSING,
        descricao="Falta abonada para teste.",
        day=absent_day,
        colaborador_id=collaborator["colaborador_id"],
        nome_colaborador=collaborator["nome"],
    )
    stack["occurrences"].waive_occurrence(
        occurrence["ocorrencia_id"],
        motivo_abono="Atestado",
        observacao_abono="Documento apresentado.",
    )

    row = stack["monthly_report"].calculate_month("06/2026")["colaboradores"][0]
    detail = _detail_text(row)

    assert row["datas_trabalhadas"] == [f"{worked_day.day:02d}/06/2026"]
    assert row["faltas_abonadas"] == 1
    assert "Atestado" in detail
    assert "Documento apresentado" in detail
    assert "Consulta Frequencia" in detail
