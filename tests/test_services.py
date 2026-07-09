from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from app.config.settings import (
    COLLABORATOR_STATUS_INACTIVE,
    OCCURRENCE_POINT_LATE,
    OCCURRENCE_POINT_MISSING,
    OCCURRENCE_RETURN_OUT_OF_TIME,
    OCCURRENCE_STATUS_OPEN,
    OCCURRENCE_STATUS_RESOLVED,
    OCCURRENCE_TASK_LATE,
    OCCURRENCE_TASK_MISSED,
    SCALE_TYPE_SCALE,
    SCALE_TYPE_WEEKLY,
    SCALE_TYPES,
    TASK_STATUS_DONE,
    TASK_STATUS_IN_PROGRESS,
    TASK_STATUS_LATE,
    TASK_STATUS_MISSED,
    TASK_STATUS_PARTIAL,
)


def test_create_and_deactivate_collaborator(stack):
    collaborator = stack["collaborators"].create_collaborator("Ana Souza", setor="Atendimento", cargo="Atendente")

    assert collaborator["nome"] == "Ana Souza"
    assert len(stack["collaborators"].list_active()) == 1

    updated = stack["collaborators"].set_active(collaborator["colaborador_id"], False)

    assert updated["status"] == COLLABORATOR_STATUS_INACTIVE
    assert stack["collaborators"].list_active() == []


def test_record_time(stack):
    collaborator = stack["collaborators"].create_collaborator("Bruno Lima", setor="Atendimento")
    stamp = datetime(2026, 5, 4, 8, 0)

    record = stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=stamp)

    assert record["nome_colaborador"] == "Bruno Lima"
    assert record["tipo_ponto"] == "entrada"
    assert record["data"] == "04/05/2026"
    assert record["hora"] == "08:00"


def test_create_task(stack):
    task = stack["tasks"].create_task(
        "Limpar loja",
        descricao="Limpar piso e balcão.",
        horario_inicio="12:00",
        horario_limite="13:00",
        nome_setor="Todos",
    )

    assert task["nome"] == "Limpar loja"
    assert task["horario_limite"] == "13:00"
    assert task["active"] is True


def test_task_done_inside_limit(stack):
    collaborator = stack["collaborators"].create_collaborator("Carla Dias", setor="Atendimento")
    task = stack["tasks"].create_task("Conferir estoque", nome_setor="Todos", horario_inicio="09:00", horario_limite="10:00")

    check = stack["tasks"].mark_done(task["tarefa_id"], collaborator["colaborador_id"], when=datetime(2026, 5, 4, 9, 30))

    assert check["status"] == TASK_STATUS_DONE
    assert stack["occurrences"].list_all() == []


def test_task_late_creates_occurrence(stack):
    collaborator = stack["collaborators"].create_collaborator("Diego Alves", setor="Atendimento")
    task = stack["tasks"].create_task("Higienizar balcão", nome_setor="Todos", horario_inicio="12:00", horario_limite="13:00")

    check = stack["tasks"].mark_done(task["tarefa_id"], collaborator["colaborador_id"], when=datetime(2026, 5, 4, 13, 15))
    occurrences = stack["occurrences"].list_all()

    assert check["status"] == TASK_STATUS_LATE
    assert len(occurrences) == 1
    assert occurrences[0]["tipo"] == OCCURRENCE_TASK_LATE
    assert occurrences[0]["nome_colaborador"] == "Diego Alves"


def test_pending_task_creates_missed_occurrence_for_present_collaborator(stack):
    collaborator = stack["collaborators"].create_collaborator("Eva Rocha", setor="Atendimento")
    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    task = stack["tasks"].create_task("Fechar caixa", nome_setor="Todos", horario_inicio="12:00", horario_limite="13:00")

    created = stack["tasks"].verify_pending_tasks(now=datetime(2026, 5, 4, 14, 0))
    created_again = stack["tasks"].verify_pending_tasks(now=datetime(2026, 5, 4, 14, 5))

    assert len(created) == 1
    assert created_again == []
    assert created[0]["tipo"] == OCCURRENCE_TASK_MISSED
    assert created[0]["tarefa_id"] == task["tarefa_id"]
    assert created[0]["colaborador_id"] == collaborator["colaborador_id"]


def test_present_collaborator_basic_rule(stack):
    collaborator = stack["collaborators"].create_collaborator("Fabio Martins", setor="Atendimento")
    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))

    present_at_13 = stack["time"].present_collaborators("04/05/2026", "13:00")
    assert [row["nome"] for row in present_at_13] == ["Fabio Martins"]

    stack["time"].record_time(collaborator["colaborador_id"], "saída", when=datetime(2026, 5, 4, 12, 30))
    present_after_exit = stack["time"].present_collaborators("04/05/2026", "13:00")

    assert present_after_exit == []


def test_task_with_two_present_collaborators_requires_both_checks(stack):
    collaborator_a = stack["collaborators"].create_collaborator("Ana", setor="Atendimento")
    collaborator_b = stack["collaborators"].create_collaborator("Bruno", setor="Atendimento")
    stack["time"].record_time(collaborator_a["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    stack["time"].record_time(collaborator_b["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 5))
    task = stack["tasks"].create_task("Limpar loja", nome_setor="Todos", horario_inicio="12:00", horario_limite="13:00")

    stack["tasks"].mark_done(task["tarefa_id"], collaborator_a["colaborador_id"], when=datetime(2026, 5, 4, 12, 30))

    assert stack["tasks"].status_for_task(task["tarefa_id"], "04/05/2026", datetime(2026, 5, 4, 12, 30)) == TASK_STATUS_PARTIAL

    stack["tasks"].mark_done(task["tarefa_id"], collaborator_b["colaborador_id"], when=datetime(2026, 5, 4, 12, 35))

    assert stack["tasks"].status_for_task(task["tarefa_id"], "04/05/2026", datetime(2026, 5, 4, 12, 40)) == TASK_STATUS_DONE


def test_task_with_tolerance_does_not_create_late_occurrence_inside_tolerance(stack):
    collaborator = stack["collaborators"].create_collaborator("Gabi", setor="Atendimento")
    task = stack["tasks"].create_task(
        "Organizar vitrine", nome_setor="Todos",
        horario_inicio="12:00",
        horario_limite="13:00",
        tolerancia_minutos=15,
    )

    check = stack["tasks"].mark_done(task["tarefa_id"], collaborator["colaborador_id"], when=datetime(2026, 5, 4, 13, 10))

    assert check["status"] == TASK_STATUS_DONE
    assert stack["occurrences"].list_all() == []


def test_task_after_tolerance_creates_late_occurrence(stack):
    collaborator = stack["collaborators"].create_collaborator("Heitor", setor="Atendimento")
    task = stack["tasks"].create_task(
        "Guardar mercadorias", nome_setor="Todos",
        horario_inicio="12:00",
        horario_limite="13:00",
        tolerancia_minutos=15,
    )

    check = stack["tasks"].mark_done(task["tarefa_id"], collaborator["colaborador_id"], when=datetime(2026, 5, 4, 13, 16))

    assert check["status"] == TASK_STATUS_LATE
    assert stack["occurrences"].list_all()[0]["tipo"] == OCCURRENCE_TASK_LATE


def test_task_display_colors_by_status(stack):
    collaborator = stack["collaborators"].create_collaborator("Igor", setor="Atendimento")
    task = stack["tasks"].create_task("Conferir banheiro", nome_setor="Todos", horario_inicio="16:00", horario_limite="17:00", tolerancia_minutos=15)

    running = stack["tasks"].task_display_state(task, "04/05/2026", datetime(2026, 5, 4, 16, 30))
    late = stack["tasks"].task_display_state(task, "04/05/2026", datetime(2026, 5, 4, 17, 16))
    stack["tasks"].mark_done(task["tarefa_id"], collaborator["colaborador_id"], when=datetime(2026, 5, 4, 16, 40))
    done = stack["tasks"].task_display_state(task, "04/05/2026", datetime(2026, 5, 4, 16, 45))

    assert running["status"] == TASK_STATUS_IN_PROGRESS
    assert running["tag"] == "running"
    assert late["status"] == TASK_STATUS_MISSED
    assert late["tag"] == "late"
    assert done["status"] == TASK_STATUS_DONE
    assert done["tag"] == "done"


def test_task_restarts_pending_next_day(stack):
    collaborator = stack["collaborators"].create_collaborator("Julia", setor="Atendimento")
    task = stack["tasks"].create_task("Abrir loja", nome_setor="Todos", horario_inicio="08:00", horario_limite="09:00")

    stack["tasks"].mark_done(task["tarefa_id"], collaborator["colaborador_id"], when=datetime(2026, 5, 4, 8, 30))

    assert stack["tasks"].status_for_task(task["tarefa_id"], "05/05/2026", datetime(2026, 5, 5, 7, 30)) == "pendente"


def test_late_time_record_respects_schedule_tolerance(stack):
    journey = stack["journeys"].create_journey(
        "Comercial",
        tipo_escala=SCALE_TYPE_WEEKLY,
        entrada="08:00",
        tempo_intervalo="01:00",
        saida="17:00",
        tolerancia_minutos=15,
    )
    collaborator_ok = stack["collaborators"].create_collaborator("Karina", setor="Atendimento", jornada_id=journey["jornada_id"])
    collaborator_late = stack["collaborators"].create_collaborator("Lucas", setor="Atendimento", jornada_id=journey["jornada_id"])

    stack["time"].record_time(collaborator_ok["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 10))
    stack["time"].record_time(collaborator_late["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 20))

    occurrences = stack["occurrences"].list_all()
    assert len(occurrences) == 1
    assert occurrences[0]["tipo"] == OCCURRENCE_POINT_LATE
    assert occurrences[0]["nome_colaborador"] == "Lucas"


def test_journey_uses_dynamic_pause_interval_without_fixed_pause_fields(stack):
    journey = stack["journeys"].create_journey(
        "Com pausa dinâmica",
        tipo_escala=SCALE_TYPE_WEEKLY,
        entrada="08:00",
        saida="17:00",
        tempo_intervalo="01:00",
    )

    assert journey["tempo_intervalo"] == 60
    assert "pausa_inicio" not in journey
    assert "pausa_fim" not in journey


def test_return_inside_dynamic_pause_tolerance_does_not_create_occurrence(stack):
    journey = stack["journeys"].create_journey(
        "Intervalo 1h",
        entrada="08:00",
        saida="17:00",
        tempo_intervalo="01:00",
        tolerancia_minutos=15,
    )
    collaborator = stack["collaborators"].create_collaborator("Rita", setor="Atendimento", jornada_id=journey["jornada_id"])

    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    stack["time"].record_time(collaborator["colaborador_id"], "pausa", when=datetime(2026, 5, 4, 12, 0))
    stack["time"].record_time(collaborator["colaborador_id"], "retorno", when=datetime(2026, 5, 4, 13, 10))

    assert stack["occurrences"].list_all() == []


def test_return_after_dynamic_pause_tolerance_creates_occurrence(stack):
    journey = stack["journeys"].create_journey(
        "Intervalo 1h",
        entrada="08:00",
        saida="17:00",
        tempo_intervalo="01:00",
        tolerancia_minutos=15,
    )
    collaborator = stack["collaborators"].create_collaborator("Sandro", setor="Atendimento", jornada_id=journey["jornada_id"])

    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    stack["time"].record_time(collaborator["colaborador_id"], "pausa", when=datetime(2026, 5, 4, 12, 0))
    stack["time"].record_time(collaborator["colaborador_id"], "retorno", when=datetime(2026, 5, 4, 13, 20))

    occurrences = stack["occurrences"].list_all()
    assert len(occurrences) == 1
    assert occurrences[0]["tipo"] == OCCURRENCE_RETURN_OUT_OF_TIME
    assert occurrences[0]["nome_colaborador"] == "Sandro"



def test_dashboard_summary_by_period_counts_operational_indicators(stack):
    journey = stack["journeys"].create_journey(
        "Comercial",
        tipo_escala=SCALE_TYPE_WEEKLY,
        entrada="08:00",
        saida="17:00",
        tolerancia_minutos=10,
    )
    collaborator = stack["collaborators"].create_collaborator("Marina", setor="Atendimento", jornada_id=journey["jornada_id"])
    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 5, 8, 20))
    task = stack["tasks"].create_task("Limpar loja", nome_setor="Todos", horario_inicio="12:00", horario_limite="13:00")
    stack["tasks"].verify_pending_tasks(now=datetime(2026, 5, 5, 14, 0))

    summary = stack["dashboard"].summary_by_period("04/05/2026", "05/05/2026")

    assert summary["data_inicio"] == "04/05/2026"
    assert summary["data_fim"] == "05/05/2026"
    assert summary["presentes"] == 1
    assert summary["tarefas_dia"] == 1
    assert summary["ocorrencias_periodo"] >= 2
    assert summary["atrasos_periodo"] == 1
    assert summary["tarefas_nao_cumpridas"] >= 1


def test_dashboard_rankings_and_occurrence_chart(stack):
    collaborator = stack["collaborators"].create_collaborator("Lucas", setor="Atendimento")
    task = stack["tasks"].create_task("Conferir freezer", nome_setor="Todos", horario_inicio="10:00", horario_limite="11:00")
    stack["occurrences"].create_occurrence(
        tipo=OCCURRENCE_POINT_LATE,
        descricao="Entrada após tolerância.",
        day="04/05/2026",
        colaborador_id=collaborator["colaborador_id"],
        nome_colaborador="Lucas",
    )
    stack["occurrences"].create_occurrence(
        tipo=OCCURRENCE_TASK_MISSED,
        descricao="Tarefa não cumprida.",
        day="04/05/2026",
        tarefa_id=task["tarefa_id"],
        nome_tarefa="Conferir freezer",
    )

    by_type = stack["dashboard"].occurrences_by_type("04/05/2026", "04/05/2026")
    failed_tasks = stack["dashboard"].failed_tasks_ranking("04/05/2026", "04/05/2026")
    late_collaborators = stack["dashboard"].late_collaborators_ranking("04/05/2026", "04/05/2026")

    assert {row["tipo"] for row in by_type} >= {OCCURRENCE_POINT_LATE, OCCURRENCE_TASK_MISSED}
    assert failed_tasks == [{"nome_tarefa": "Conferir freezer", "falhas": 1}]
    assert late_collaborators == [{"nome_colaborador": "Lucas", "atrasos": 1}]


def test_dashboard_period_validation_blocks_inverted_dates(stack):
    import pytest

    with pytest.raises(ValueError, match="Data inicial"):
        stack["dashboard"].summary_by_period("05/05/2026", "04/05/2026")


def test_dashboard_critical_tasks_uses_reference_day(stack):
    stack["tasks"].create_task("Abrir loja", nome_setor="Todos", horario_inicio="08:00", horario_limite="09:00")

    critical = stack["dashboard"].critical_tasks("04/05/2026")

    assert critical
    assert critical[0]["nome"] == "Abrir loja"
    assert critical[0]["status"] in {TASK_STATUS_MISSED, TASK_STATUS_IN_PROGRESS, "pendente"}

def test_time_sequence_blocks_exit_before_entry(stack):
    collaborator = stack["collaborators"].create_collaborator("Nina", setor="Atendimento")

    with pytest.raises(ValueError, match="antes da entrada"):
        stack["time"].record_time(collaborator["colaborador_id"], "sa\u00edda", when=datetime(2026, 5, 4, 17, 0))


def test_time_sequence_blocks_return_without_break(stack):
    collaborator = stack["collaborators"].create_collaborator("Otavio", setor="Atendimento")
    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))

    with pytest.raises(ValueError, match="retorno sem pausa"):
        stack["time"].record_time(collaborator["colaborador_id"], "retorno", when=datetime(2026, 5, 4, 13, 0))


def test_time_sequence_blocks_two_entries_in_a_row(stack):
    collaborator = stack["collaborators"].create_collaborator("Paula", setor="Atendimento")
    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))

    with pytest.raises(ValueError, match="entrada aberta"):
        stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 5))


def test_time_sequence_allows_valid_day_flow(stack):
    collaborator = stack["collaborators"].create_collaborator("Rafa", setor="Atendimento")

    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    stack["time"].record_time(collaborator["colaborador_id"], "pausa", when=datetime(2026, 5, 4, 12, 0))
    stack["time"].record_time(collaborator["colaborador_id"], "retorno", when=datetime(2026, 5, 4, 13, 0))
    stack["time"].record_time(collaborator["colaborador_id"], "sa\u00edda", when=datetime(2026, 5, 4, 17, 0))

    context = stack["time"].point_context(collaborator["colaborador_id"], "04/05/2026")

    assert context["allowed_types"] == ("entrada",)
    assert "Jornada encerrada" in context["next_text"]


def test_time_context_shows_last_point_and_next_action(stack):
    collaborator = stack["collaborators"].create_collaborator("Sofia", setor="Atendimento")

    context_initial = stack["time"].point_context(collaborator["colaborador_id"], "04/05/2026")
    assert context_initial["allowed_types"] == ("entrada",)
    assert "Nenhum ponto" in context_initial["last_text"]

    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    context = stack["time"].point_context(collaborator["colaborador_id"], "04/05/2026")

    assert context["allowed_types"] == ("pausa", "sa\u00edda")
    assert "entrada" in context["last_text"]
    assert "08:00" in context["last_text"]

def test_collaborator_point_activities_load_all_day_items(stack):
    journey = stack["journeys"].create_journey(
        "Comercial",
        entrada="08:00",
        saida="17:00",
        tempo_intervalo="01:00",
        tolerancia_minutos=15,
        dias_semana="segunda",
    )
    collaborator = stack["collaborators"].create_collaborator("Tiago", setor="Atendimento", jornada_id=journey["jornada_id"])

    activities = stack["time"].point_activities_for_collaborator(collaborator["colaborador_id"], now=datetime(2026, 5, 4, 7, 50))

    assert [row["tipo"] for row in activities] == ["entrada", "pausa", "retorno", "saída"]
    assert all(row["tag"] == "pending" for row in activities)


def test_collaborator_point_activities_turn_green_after_each_record(stack):
    journey = stack["journeys"].create_journey(
        "Comercial",
        entrada="08:00",
        saida="17:00",
        tempo_intervalo="01:00",
        tolerancia_minutos=15,
        dias_semana="segunda",
    )
    collaborator = stack["collaborators"].create_collaborator("Valeria", setor="Atendimento", jornada_id=journey["jornada_id"])
    collaborator_id = collaborator["colaborador_id"]

    stack["time"].record_time(collaborator_id, "entrada", when=datetime(2026, 5, 4, 8, 0))
    by_type = {row["tipo"]: row for row in stack["time"].point_activities_for_collaborator(collaborator_id, now=datetime(2026, 5, 4, 8, 1))}
    assert by_type["entrada"]["tag"] == "done"
    assert by_type["entrada"]["status"] == "Confirmada às 08:00"

    stack["time"].record_time(collaborator_id, "pausa", when=datetime(2026, 5, 4, 12, 0))
    by_type = {row["tipo"]: row for row in stack["time"].point_activities_for_collaborator(collaborator_id, now=datetime(2026, 5, 4, 12, 1))}
    assert by_type["pausa"]["tag"] == "done"
    assert "13:00" in by_type["retorno"]["detail"]

    stack["time"].record_time(collaborator_id, "retorno", when=datetime(2026, 5, 4, 13, 5))
    by_type = {row["tipo"]: row for row in stack["time"].point_activities_for_collaborator(collaborator_id, now=datetime(2026, 5, 4, 13, 6))}
    assert by_type["retorno"]["tag"] == "done"

    stack["time"].record_time(collaborator_id, "saída", when=datetime(2026, 5, 4, 17, 0))
    by_type = {row["tipo"]: row for row in stack["time"].point_activities_for_collaborator(collaborator_id, now=datetime(2026, 5, 4, 17, 1))}
    assert by_type["saída"]["tag"] == "done"


def test_collaborator_point_activity_entry_colors_follow_tolerance(stack):
    journey = stack["journeys"].create_journey(
        "Comercial",
        entrada="08:00",
        saida="17:00",
        tempo_intervalo="01:00",
        tolerancia_minutos=15,
        dias_semana="segunda",
    )
    collaborator = stack["collaborators"].create_collaborator("William", setor="Atendimento", jornada_id=journey["jornada_id"])
    collaborator_id = collaborator["colaborador_id"]

    pending = stack["time"].point_activities_for_collaborator(collaborator_id, now=datetime(2026, 5, 4, 7, 50))[0]
    running = stack["time"].point_activities_for_collaborator(collaborator_id, now=datetime(2026, 5, 4, 8, 5))[0]
    late = stack["time"].point_activities_for_collaborator(collaborator_id, now=datetime(2026, 5, 4, 8, 20))[0]

    assert pending["tag"] == "pending"
    assert running["tag"] == "running"
    assert late["tag"] == "late"


def test_occurrence_defaults_pending_and_updates_treatment(stack):
    occurrence = stack["occurrences"].create_occurrence(
        tipo=OCCURRENCE_POINT_LATE,
        descricao="Entrada fora da tolerancia.",
        day="04/05/2026",
        nome_colaborador="Joao",
    )

    assert occurrence["status"] == OCCURRENCE_STATUS_OPEN

    updated = stack["occurrences"].update_treatment(
        occurrence["ocorrencia_id"],
        status=OCCURRENCE_STATUS_RESOLVED,
        acao_tomada="Conversado com colaborador.",
        responsavel_tratativa="Gestor",
        observacoes="Acompanhar reincidencia.",
    )

    assert updated["status"] == OCCURRENCE_STATUS_RESOLVED


def test_occurrence_filters_by_period_collaborator_type_and_status(stack):
    stack["occurrences"].create_occurrence(
        tipo=OCCURRENCE_POINT_LATE,
        descricao="Atraso.",
        day="04/05/2026",
        nome_colaborador="Marcos",
    )
    resolved = stack["occurrences"].create_occurrence(
        tipo=OCCURRENCE_TASK_MISSED,
        descricao="Tarefa nao cumprida.",
        day="05/05/2026",
        nome_colaborador="Ana",
    )
    stack["occurrences"].update_treatment(resolved["ocorrencia_id"], status=OCCURRENCE_STATUS_RESOLVED)

    pending_rows = stack["occurrences"].filter_occurrences(
        data_inicio="04/05/2026",
        data_fim="05/05/2026",
        colaborador="mar",
        tipo=OCCURRENCE_POINT_LATE,
        status=OCCURRENCE_STATUS_OPEN,
    )
    resolved_rows = stack["occurrences"].filter_occurrences(status=OCCURRENCE_STATUS_RESOLVED)

    assert len(pending_rows) == 1
    assert pending_rows[0]["nome_colaborador"] == "Marcos"
    assert len(resolved_rows) == 1
    assert resolved_rows[0]["tipo"] == OCCURRENCE_TASK_MISSED


def test_occurrence_pdf_export_creates_file(stack, tmp_path):
    from app.config.paths import set_root_override

    set_root_override(str(tmp_path))
    try:
        stack["occurrences"].create_occurrence(
            tipo=OCCURRENCE_TASK_MISSED,
            descricao="Relatorio de teste.",
            day="04/05/2026",
            nome_tarefa="Abrir loja",
        )
        rows = stack["occurrences"].filter_occurrences(data_inicio="04/05/2026", data_fim="04/05/2026")
        path = stack["occurrences"].export_pdf(rows, data_inicio="04/05/2026", data_fim="04/05/2026")
    finally:
        set_root_override(None)

    assert path.endswith(".pdf")
    assert Path(path).exists()
    assert "ocorrencias" in Path(path).parts

def test_weekly_journey_calculates_expected_days(stack):
    journey = stack["journeys"].create_journey(
        nome="Segunda a sexta",
        tipo_escala=SCALE_TYPE_WEEKLY,
        entrada="08:00",
        tempo_intervalo="01:00",
        saida="17:00",
        dias_semana="1,2,3,4,5",
    )

    days = stack["journeys"].expected_workdays(journey, "04/05/2026", "10/05/2026")

    assert len(days) == 5
    assert [day.strftime("%d/%m/%Y") for day in days][0] == "04/05/2026"


def test_journey_types_are_only_weekly_and_scale():
    assert SCALE_TYPES == (SCALE_TYPE_WEEKLY, SCALE_TYPE_SCALE)


def test_12x36_scale_description_calculates_expected_days(stack):
    journey = stack["journeys"].create_journey(
        nome="Plantao 12x36",
        tipo_escala=SCALE_TYPE_SCALE,
        descricao_escala="12x36",
        horas_trabalho=12,
        horas_descanso=36,
        horario_inicio_escala="07:00",
        data_inicio_escala="01/05/2026",
    )

    days = stack["journeys"].expected_workdays(journey, "01/05/2026", "07/05/2026")

    assert [day.strftime("%d/%m/%Y") for day in days] == ["01/05/2026", "03/05/2026", "05/05/2026", "07/05/2026"]


def test_24x48_scale_calculates_expected_days(stack):
    journey = stack["journeys"].create_journey(
        nome="Plantao 24x48",
        tipo_escala=SCALE_TYPE_SCALE,
        descricao_escala="24x48",
        horas_trabalho=24,
        horas_descanso=48,
        horario_inicio_escala="07:00",
        data_inicio_escala="01/05/2026",
    )

    days = stack["journeys"].expected_workdays(journey, "01/05/2026", "07/05/2026")

    assert [day.strftime("%d/%m/%Y") for day in days] == [
        "01/05/2026",
        "02/05/2026",
        "04/05/2026",
        "05/05/2026",
        "07/05/2026",
    ]


def test_collaborator_can_be_linked_to_journey_with_salary_and_bonus(stack):
    journey = stack["journeys"].create_journey("Comercial", entrada="08:00", saida="17:00")

    collaborator = stack["collaborators"].create_collaborator(
        "Lara", setor="Atendimento",
        salario_base="2200,50",
        jornada_id=journey["jornada_id"],
        bonus_assiduidade="100",
        bonus_tarefas="75",
    )

    assert collaborator["jornada_id"] == journey["jornada_id"]
    assert collaborator["salario_base"] == 2200.5
    assert collaborator["bonus_assiduidade"] == 100.0
    assert collaborator["bonus_tarefas"] == 75.0


def test_monthly_report_calculates_absence_discount_and_bonuses(stack):
    journey = stack["journeys"].create_journey(
        "Dois dias",
        entrada="08:00",
        saida="17:00",
        dias_semana="1,2",
    )
    collaborator = stack["collaborators"].create_collaborator(
        "Mateus", setor="Atendimento",
        salario_base=1000,
        jornada_id=journey["jornada_id"],
        bonus_assiduidade=100,
        bonus_tarefas=50,
    )
    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))

    report = stack["monthly_report"].calculate_month("05/2026")
    row = report["colaboradores"][0]

    assert row["dias_esperados"] == 8
    assert row["dias_trabalhados"] == 1
    assert row["faltas_nao_abonadas"] == 7
    assert row["desconto_faltas"] == 875
    assert row["bonus_assiduidade_concedido"] == 0
    assert row["bonus_tarefas_concedido"] == 0
    assert row["salario_estimado_final"] == 125


def test_waived_absence_does_not_discount_salary(stack):
    journey = stack["journeys"].create_journey("Segunda", entrada="08:00", saida="17:00", dias_semana="segunda")
    collaborator = stack["collaborators"].create_collaborator("Nadia", setor="Atendimento", salario_base=400, jornada_id=journey["jornada_id"])
    occurrence = stack["occurrences"].create_occurrence(
        tipo=OCCURRENCE_POINT_MISSING,
        descricao="Falta em dia esperado.",
        day="04/05/2026",
        colaborador_id=collaborator["colaborador_id"],
        nome_colaborador="Nadia",
    )
    stack["occurrences"].waive_occurrence(occurrence["ocorrencia_id"], motivo_abono="Atestado")

    row = stack["monthly_report"].calculate_month("05/2026")["colaboradores"][0]

    assert row["faltas_abonadas"] == 1
    assert row["faltas_nao_abonadas"] == 3
    assert row["desconto_faltas"] == 300


def test_task_late_blocks_task_bonus(stack):
    journey = stack["journeys"].create_journey("Segunda", entrada="08:00", saida="17:00", dias_semana="segunda")
    collaborator = stack["collaborators"].create_collaborator(
        "Olivia", setor="Atendimento",
        salario_base=400,
        jornada_id=journey["jornada_id"],
        bonus_tarefas=80,
    )
    stack["occurrences"].create_occurrence(
        tipo=OCCURRENCE_TASK_LATE,
        descricao="Tarefa feita fora do prazo.",
        day="04/05/2026",
        colaborador_id=collaborator["colaborador_id"],
        nome_colaborador="Olivia",
    )

    row = stack["monthly_report"].calculate_month("05/2026")["colaboradores"][0]

    assert row["tarefas_atrasadas"] == 1
    assert row["bonus_tarefas_concedido"] == 0


def test_monthly_report_pdf_is_generated(stack, tmp_path):
    from app.config.paths import set_root_override

    journey = stack["journeys"].create_journey("Segunda", entrada="08:00", saida="17:00", dias_semana="segunda")
    stack["collaborators"].create_collaborator("Paulo", setor="Atendimento", salario_base=500, jornada_id=journey["jornada_id"])
    set_root_override(str(tmp_path))
    try:
        path = stack["monthly_report"].generate_pdf("05/2026")
    finally:
        set_root_override(None)

    assert Path(path).exists()
    assert path.endswith("relatorio_ponto_tarefas_05_2026.pdf")



def test_startup_check_creates_missing_point_for_previous_day_without_duplicate(stack):
    journey = stack["journeys"].create_journey(
        "Segunda",
        tipo_escala=SCALE_TYPE_WEEKLY,
        entrada="08:00",
        saida="17:00",
        dias_semana="segunda",
    )
    collaborator = stack["collaborators"].create_collaborator("Renata", setor="Atendimento", jornada_id=journey["jornada_id"])

    created = stack["startup_check"].verify_previous_day(now=datetime(2026, 5, 5, 9, 0))
    created_again = stack["startup_check"].verify_previous_day(now=datetime(2026, 5, 5, 9, 5))

    missing = [row for row in created if row["tipo"] == OCCURRENCE_POINT_MISSING]
    assert len(missing) == 1
    assert missing[0]["colaborador_id"] == collaborator["colaborador_id"]
    assert missing[0]["data"] == "04/05/2026"
    assert created_again == []


def test_startup_check_creates_missed_task_for_previous_day_without_duplicate(stack):
    journey = stack["journeys"].create_journey(
        "Segunda",
        tipo_escala=SCALE_TYPE_WEEKLY,
        entrada="08:00",
        saida="17:00",
        dias_semana="segunda",
    )
    stack["collaborators"].create_collaborator("Ronaldo", setor="Atendimento", jornada_id=journey["jornada_id"])
    task = stack["tasks"].create_task(
        "Abrir caixa", nome_setor="Todos",
        horario_inicio="08:00",
        horario_limite="09:00",
        dias_semana="segunda",
    )

    created = stack["startup_check"].verify_previous_day(now=datetime(2026, 5, 5, 9, 0))
    created_again = stack["startup_check"].verify_previous_day(now=datetime(2026, 5, 5, 9, 5))

    missed = [row for row in created if row["tipo"] == OCCURRENCE_TASK_MISSED]
    assert len(missed) == 1
    assert missed[0]["tarefa_id"] == task["tarefa_id"]
    assert missed[0]["data"] == "04/05/2026"
    assert created_again == []


def test_occurrence_keeps_portuguese_accents(stack):
    occurrence = stack["occurrences"].create_occurrence(
        tipo="saída fora do horário",
        descricao="Saída registrada fora do horário esperado.",
        day="04/05/2026",
    )

    assert occurrence["tipo"] == "saída fora do horário"
    assert "horário" in occurrence["descricao"]


def test_scale_12x36_uses_hour_cycle_for_work_and_rest(stack):
    journey = stack["journeys"].create_journey(
        nome="Escala 12x36",
        tipo_escala=SCALE_TYPE_SCALE,
        descricao_escala="12x36",
        horas_trabalho=12,
        horas_descanso=36,
        data_inicio_escala="17/05/2026",
        horario_inicio_escala="08:00",
        dias_semana="segunda, terca",
    )

    assert stack["journeys"].calculate_scale_position(journey, datetime(2026, 5, 17, 8, 0))["is_working"] is True
    assert stack["journeys"].calculate_scale_position(journey, datetime(2026, 5, 17, 19, 59))["is_working"] is True
    assert stack["journeys"].calculate_scale_position(journey, datetime(2026, 5, 17, 20, 0))["is_working"] is False
    assert stack["journeys"].calculate_scale_position(journey, datetime(2026, 5, 19, 8, 0))["is_working"] is True
    assert journey["dias_semana"] == ""


def test_scale_24x48_uses_72_hour_cycle(stack):
    journey = stack["journeys"].create_journey(
        nome="Escala 24x48",
        tipo_escala=SCALE_TYPE_SCALE,
        descricao_escala="24x48",
        horas_trabalho=24,
        horas_descanso=48,
        data_inicio_escala="17/05/2026",
        horario_inicio_escala="20:00",
    )

    assert stack["journeys"].calculate_scale_position(journey, datetime(2026, 5, 17, 20, 0))["is_working"] is True
    assert stack["journeys"].calculate_scale_position(journey, datetime(2026, 5, 18, 12, 0))["is_working"] is True
    assert stack["journeys"].calculate_scale_position(journey, datetime(2026, 5, 18, 20, 0))["is_working"] is False
    position = stack["journeys"].calculate_scale_position(journey, datetime(2026, 5, 20, 20, 0))
    assert position["cycle_hours"] == 72
    assert position["position_hours"] == 0
    assert position["is_working"] is True


def test_scale_work_intervals_include_overnight_shift(stack):
    journey = stack["journeys"].create_journey(
        nome="Noite 24x48",
        tipo_escala=SCALE_TYPE_SCALE,
        descricao_escala="24x48",
        horas_trabalho=24,
        horas_descanso=48,
        data_inicio_escala="17/05/2026",
        horario_inicio_escala="20:00",
    )
    collaborator = stack["collaborators"].create_collaborator("Vera", setor="Atendimento", jornada_id=journey["jornada_id"])

    intervals = stack["journeys"].get_work_intervals_for_date(collaborator, "18/05/2026")

    assert intervals
    assert intervals[0][0] == datetime(2026, 5, 17, 20, 0)
    assert intervals[0][1] == datetime(2026, 5, 18, 20, 0)
    assert stack["journeys"].should_work_on_date(collaborator, "18/05/2026") is True


def test_task_expected_collaborators_uses_scale_at_task_time(stack):
    journey = stack["journeys"].create_journey(
        nome="Escala 12x36",
        tipo_escala=SCALE_TYPE_SCALE,
        descricao_escala="12x36",
        horas_trabalho=12,
        horas_descanso=36,
        data_inicio_escala="17/05/2026",
        horario_inicio_escala="08:00",
    )
    collaborator = stack["collaborators"].create_collaborator("Wagner", setor="Atendimento", jornada_id=journey["jornada_id"])
    task = stack["tasks"].create_task("Conferir loja", nome_setor="Todos", horario_inicio="12:00", horario_limite="13:00", dias_semana="domingo")

    expected = stack["tasks"].expected_collaborators_for_task(task, "17/05/2026")

    assert [row["colaborador_id"] for row in expected] == [collaborator["colaborador_id"]]


def test_startup_check_scale_missing_point_only_when_working(stack):
    journey = stack["journeys"].create_journey(
        nome="Escala 12x36",
        tipo_escala=SCALE_TYPE_SCALE,
        descricao_escala="12x36",
        horas_trabalho=12,
        horas_descanso=36,
        data_inicio_escala="17/05/2026",
        horario_inicio_escala="08:00",
    )
    collaborator = stack["collaborators"].create_collaborator("Xavier", setor="Atendimento", jornada_id=journey["jornada_id"])

    created = stack["startup_check"].verify_previous_day(now=datetime(2026, 5, 18, 9, 0))
    falta = [row for row in created if row["tipo"] == OCCURRENCE_POINT_MISSING]

    assert len(falta) == 1
    assert falta[0]["colaborador_id"] == collaborator["colaborador_id"]
    assert falta[0]["data"] == "17/05/2026"


def test_startup_check_scale_does_not_create_absence_on_rest_day(stack):
    journey = stack["journeys"].create_journey(
        nome="Escala 12x36",
        tipo_escala=SCALE_TYPE_SCALE,
        descricao_escala="12x36",
        horas_trabalho=12,
        horas_descanso=36,
        data_inicio_escala="17/05/2026",
        horario_inicio_escala="08:00",
    )
    stack["collaborators"].create_collaborator("Yara", setor="Atendimento", jornada_id=journey["jornada_id"])

    created = stack["startup_check"].verify_previous_day(now=datetime(2026, 5, 19, 9, 0))

    assert [row for row in created if row["tipo"] == OCCURRENCE_POINT_MISSING] == []


def test_startup_check_overnight_scale_accepts_entry_from_previous_calendar_day(stack):
    journey = stack["journeys"].create_journey(
        nome="Noite 24x48",
        tipo_escala=SCALE_TYPE_SCALE,
        descricao_escala="24x48",
        horas_trabalho=24,
        horas_descanso=48,
        data_inicio_escala="17/05/2026",
        horario_inicio_escala="20:00",
    )
    collaborator = stack["collaborators"].create_collaborator("Zelia", setor="Atendimento", jornada_id=journey["jornada_id"])
    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 17, 20, 0))

    created = stack["startup_check"].verify_previous_day(now=datetime(2026, 5, 19, 9, 0))

    assert [row for row in created if row["tipo"] == OCCURRENCE_POINT_MISSING] == []


def test_collaborator_requires_sector(stack):
    with pytest.raises(ValueError, match="setor"):
        stack["collaborators"].create_collaborator("Sem Setor")


def test_task_requires_execution_sector(stack):
    with pytest.raises(ValueError, match="setor"):
        stack["tasks"].create_task("Tarefa sem setor", horario_inicio="12:00", horario_limite="13:00")


def test_default_sectors_are_created(stack):
    names = [row["nome"] for row in stack["sectors"].list_active()]

    assert {"Atendimento", "Limpeza", "Cozinha", "Caixa", "Administrativo", "Estoque", "Todos"}.issubset(set(names))


def test_can_create_new_sector(stack):
    sector = stack["sectors"].create_sector("Delivery", descricao="Entregas")

    assert sector["nome"] == "Delivery"
    assert sector["active"] is True


def test_collaborator_and_task_store_sector_from_master_list(stack):
    collaborator = stack["collaborators"].create_collaborator("Ana", setor="Atendimento")
    task = stack["tasks"].create_task("Atender balcão", horario_inicio="10:00", horario_limite="11:00", nome_setor="Atendimento")

    assert collaborator["setor_id"]
    assert collaborator["nome_setor"] == "Atendimento"
    assert task["setor_id"] == collaborator["setor_id"]
    assert task["nome_setor"] == "Atendimento"


def test_task_check_filters_present_collaborators_by_execution_sector(stack):
    clean_worker = stack["collaborators"].create_collaborator("Lia", setor="Limpeza")
    attendant = stack["collaborators"].create_collaborator("Ari", setor="Atendimento")
    stack["time"].record_time(clean_worker["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    stack["time"].record_time(attendant["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    task = stack["tasks"].create_task("Limpar loja", horario_inicio="12:00", horario_limite="13:00", nome_setor="Limpeza")

    rows = stack["tasks"].collaborators_for_task_check(task["tarefa_id"], day="04/05/2026", now=datetime(2026, 5, 4, 12, 30))

    assert [row["colaborador_id"] for row in rows] == [clean_worker["colaborador_id"]]


def test_general_sector_task_appears_for_all_present_collaborators(stack):
    clean_worker = stack["collaborators"].create_collaborator("Mara", setor="Limpeza")
    attendant = stack["collaborators"].create_collaborator("Nilo", setor="Atendimento")
    stack["time"].record_time(clean_worker["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    stack["time"].record_time(attendant["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    task = stack["tasks"].create_task("Reuniao geral", horario_inicio="12:00", horario_limite="13:00", nome_setor="Todos")

    rows = stack["tasks"].collaborators_for_task_check(task["tarefa_id"], day="04/05/2026", now=datetime(2026, 5, 4, 12, 30))

    assert {row["colaborador_id"] for row in rows} == {clean_worker["colaborador_id"], attendant["colaborador_id"]}


def test_collaborator_view_task_source_filters_by_selected_collaborator_sector(stack):
    collaborator = stack["collaborators"].create_collaborator("Olga", setor="Limpeza")
    clean_task = stack["tasks"].create_task("Limpar geladeira", horario_inicio="10:00", horario_limite="11:00", nome_setor="Limpeza")
    stack["tasks"].create_task("Atender balcao", horario_inicio="10:00", horario_limite="11:00", nome_setor="Atendimento")
    general_task = stack["tasks"].create_task("Conferir avisos", horario_inicio="10:00", horario_limite="11:00", nome_setor="Todos")

    rows = stack["tasks"].tasks_for_collaborator(collaborator, "04/05/2026")

    assert {row["tarefa_id"] for row in rows} == {clean_task["tarefa_id"], general_task["tarefa_id"]}


def test_task_filter_uses_sector_name_when_legacy_sector_ids_do_not_match(stack):
    collaborator = stack["collaborators"].create_collaborator("Olga Legado", setor="Limpeza")
    task = stack["tasks"].create_task("Limpar area externa", horario_inicio="10:00", horario_limite="11:00", nome_setor="Limpeza")
    stack["collaborators"].repository.update(collaborator["colaborador_id"], {"setor_id": "colaborador-setor-antigo"})
    stack["tasks"].task_repository.update(task["tarefa_id"], {"setor_id": "tarefa-setor-antigo"})

    collaborator = stack["collaborators"].get(collaborator["colaborador_id"])
    rows = stack["tasks"].tasks_for_collaborator(collaborator, "04/05/2026")
    check = stack["tasks"].mark_done(task["tarefa_id"], collaborator["colaborador_id"], when=datetime(2026, 5, 4, 10, 30))

    assert [row["tarefa_id"] for row in rows] == [task["tarefa_id"]]
    assert check["status"] == TASK_STATUS_DONE


def test_pending_task_occurrence_is_created_only_for_responsible_sector(stack):
    clean_worker = stack["collaborators"].create_collaborator("Paula", setor="Limpeza")
    attendant = stack["collaborators"].create_collaborator("Queli", setor="Atendimento")
    stack["time"].record_time(clean_worker["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    stack["time"].record_time(attendant["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    stack["tasks"].create_task("Limpar piso", horario_inicio="12:00", horario_limite="13:00", nome_setor="Limpeza")

    created = stack["tasks"].verify_pending_tasks(day="04/05/2026", now=datetime(2026, 5, 4, 14, 0))

    assert len(created) == 1
    assert created[0]["colaborador_id"] == clean_worker["colaborador_id"]
    assert created[0]["nome_setor"] == "Limpeza"
    assert created[0]["colaborador_id"] != attendant["colaborador_id"]


def test_task_cannot_be_checked_by_collaborator_from_other_sector(stack):
    attendant = stack["collaborators"].create_collaborator("Rita", setor="Atendimento")
    task = stack["tasks"].create_task("Limpar bancada", horario_inicio="12:00", horario_limite="13:00", nome_setor="Limpeza")

    with pytest.raises(ValueError):
        stack["tasks"].mark_done(task["tarefa_id"], attendant["colaborador_id"], when=datetime(2026, 5, 4, 12, 30))


def _setup_payment_month_24_days(stack, *, waive_absence=False):
    journey = stack["journeys"].create_journey(
        "Fevereiro seis dias",
        entrada="08:00",
        saida="17:00",
        dias_semana="1,2,3,4,5,6",
    )
    collaborator = stack["collaborators"].create_collaborator(
        "Pagamento Teste",
        setor="Atendimento",
        cargo="Atendente",
        salario_base=2400,
        jornada_id=journey["jornada_id"],
        bonus_assiduidade=200,
        bonus_tarefas=150,
    )
    expected_days = stack["journeys"].expected_workdays(journey, "01/02/2026", "28/02/2026")
    assert len(expected_days) == 24
    absent_day = expected_days[0]
    for day in expected_days[1:]:
        stack["time"].record_time(
            collaborator["colaborador_id"],
            "entrada",
            when=datetime(day.year, day.month, day.day, 8, 0),
        )
    occurrence = stack["occurrences"].create_occurrence(
        tipo=OCCURRENCE_POINT_MISSING,
        descricao="Falta no dia esperado.",
        day=absent_day,
        colaborador_id=collaborator["colaborador_id"],
        nome_colaborador=collaborator["nome"],
    )
    if waive_absence:
        stack["occurrences"].waive_occurrence(
            occurrence["ocorrencia_id"],
            motivo_abono="Atestado",
            observacao_abono="Documento apresentado.",
        )
    return collaborator, absent_day


def test_payment_month_with_24_expected_days_one_absence_discount(stack):
    _setup_payment_month_24_days(stack)

    row = stack["monthly_report"].calculate_month("02/2026")["colaboradores"][0]

    assert row["dias_esperados"] == 24
    assert row["dias_trabalhados"] == 23
    assert row["faltas_nao_abonadas"] == 1
    assert row["salario_dia"] == pytest.approx(100)
    assert row["desconto_faltas"] == pytest.approx(100)
    assert row["bonus_assiduidade_aplicado"] == 0
    assert row["bonus_tarefas_aplicado"] == 0
    assert row["salario_final"] == pytest.approx(2300)
    assert "Perdeu bonus de assiduidade" in row["mensagem_assiduidade"]
    assert "falta nao abonada" in row["mensagem_tarefas"]
    assert row["faltas_nao_abonadas_detalhes"][0]["impacto"] == "Desconta salario e perde bonus de assiduidade."


def test_excused_absence_does_not_discount_or_remove_attendance_bonus(stack):
    _setup_payment_month_24_days(stack, waive_absence=True)

    row = stack["monthly_report"].calculate_month("02/2026")["colaboradores"][0]

    assert row["faltas_abonadas"] == 1
    assert row["faltas_nao_abonadas"] == 0
    assert row["desconto_faltas"] == 0
    assert row["bonus_assiduidade_aplicado"] == pytest.approx(200)
    assert row["bonus_tarefas_aplicado"] == pytest.approx(150)
    assert row["salario_final"] == pytest.approx(2750)
    assert row["faltas_abonadas_detalhes"][0]["motivo"] == "Atestado"
    assert row["faltas_abonadas_detalhes"][0]["impacto"] == "Nao desconta salario."


def test_payment_without_absence_or_task_failure_applies_both_bonuses(stack):
    journey = stack["journeys"].create_journey("Segundas", entrada="08:00", saida="17:00", dias_semana="segunda")
    collaborator = stack["collaborators"].create_collaborator(
        "Bonus Completo",
        setor="Atendimento",
        salario_base=1000,
        jornada_id=journey["jornada_id"],
        bonus_assiduidade=100,
        bonus_tarefas=80,
    )
    for day in stack["journeys"].expected_workdays(journey, "01/05/2026", "31/05/2026"):
        stack["time"].record_time(
            collaborator["colaborador_id"],
            "entrada",
            when=datetime(day.year, day.month, day.day, 8, 0),
        )

    row = stack["monthly_report"].calculate_month("05/2026")["colaboradores"][0]

    assert row["faltas_nao_abonadas"] == 0
    assert row["tarefas_nao_cumpridas"] == 0
    assert row["tarefas_atrasadas"] == 0
    assert row["bonus_assiduidade_aplicado"] == pytest.approx(100)
    assert row["bonus_tarefas_aplicado"] == pytest.approx(80)
    assert row["salario_final"] == pytest.approx(1180)


def test_task_violations_block_task_bonus_with_details(stack):
    collaborator = stack["collaborators"].create_collaborator(
        "Tarefa Bonus",
        setor="Atendimento",
        salario_base=1000,
        bonus_assiduidade=100,
        bonus_tarefas=80,
    )
    stack["occurrences"].create_occurrence(
        tipo=OCCURRENCE_TASK_MISSED,
        descricao="Tarefa nao cumprida.",
        day="05/05/2026",
        colaborador_id=collaborator["colaborador_id"],
        nome_colaborador=collaborator["nome"],
        tarefa_id="task-1",
        nome_tarefa="Limpar loja",
    )
    stack["occurrences"].create_occurrence(
        tipo=OCCURRENCE_TASK_LATE,
        descricao="Tarefa atrasada.",
        day="06/05/2026",
        colaborador_id=collaborator["colaborador_id"],
        nome_colaborador=collaborator["nome"],
        tarefa_id="task-2",
        nome_tarefa="Conferir caixa",
    )

    row = stack["monthly_report"].calculate_month("05/2026")["colaboradores"][0]

    assert row["tarefas_nao_cumpridas"] == 1
    assert row["tarefas_atrasadas"] == 1
    assert row["bonus_tarefas_aplicado"] == 0
    assert "Bonus por tarefas perdido" in row["mensagem_tarefas"]
    assert {item["tarefa"] for item in row["tarefas_falhas_detalhes"]} == {"Limpar loja", "Conferir caixa"}


def test_payment_zero_expected_days_does_not_divide_by_zero(stack):
    stack["collaborators"].create_collaborator(
        "Sem Jornada",
        setor="Atendimento",
        salario_base=1000,
        bonus_assiduidade=100,
        bonus_tarefas=50,
    )

    row = stack["monthly_report"].calculate_month("05/2026")["colaboradores"][0]

    assert row["dias_esperados"] == 0
    assert row["salario_dia"] == 0
    assert row["desconto_faltas"] == 0
    assert row["sem_dias_esperados_aviso"] == "Sem dias esperados de trabalho no periodo."


def test_payment_report_table_final_row_shows_salary():
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    from app.pdf.payment_report_pdf import _payment_table

    styles = getSampleStyleSheet()
    normal = styles["BodyText"]
    header = ParagraphStyle("HeaderWhiteTest", parent=normal, alignment=TA_CENTER, textColor=colors.white)

    table = _payment_table({"salario_final": 1484.46}, normal, header)
    last_row_index = len(table._cellvalues) - 1
    last_text = table._cellvalues[last_row_index][0].getPlainText()

    assert "SALÁRIO FINAL CALCULADO" in last_text
    assert "R$ 1.484,46" in last_text
    assert ("SPAN", (0, last_row_index), (-1, last_row_index)) in table._spanCmds


def test_payment_report_pdf_is_generated(stack, tmp_path):
    from app.config.paths import set_root_override

    _setup_payment_month_24_days(stack)
    set_root_override(str(tmp_path))
    try:
        path = stack["monthly_report"].generate_payment_pdf("02/2026")
    finally:
        set_root_override(None)

    assert Path(path).exists()
    assert path.endswith("relatorio_pagamento_02_2026.pdf")
    assert "relatorios_pagamento" in Path(path).parts

def test_goal_collective_bonus_applies_to_all_active_collaborators(stack):
    stack["collaborators"].create_collaborator("Ana Meta", setor="Atendimento", salario_base=1000)
    stack["collaborators"].create_collaborator("Beto Meta", setor="Atendimento", salario_base=1000)
    stack["goals"].create_goal(
        nome_meta="Meta coletiva",
        tipo_meta="coletiva",
        periodo_mes="05/2026",
        valor_bonus=120.50,
        atingida=True,
    )

    rows = stack["monthly_report"].calculate_month("05/2026")["colaboradores"]
    by_name = {row["nome"]: row for row in rows}

    assert by_name["Ana Meta"]["bonus_meta_aplicado"] == pytest.approx(120.50)
    assert by_name["Beto Meta"]["bonus_meta_aplicado"] == pytest.approx(120.50)
    assert by_name["Ana Meta"]["salario_final"] == pytest.approx(1120.50)
    assert by_name["Beto Meta"]["salario_final"] == pytest.approx(1120.50)


def test_goal_individual_bonus_applies_only_to_selected_collaborator(stack):
    ana = stack["collaborators"].create_collaborator("Ana Individual", setor="Atendimento", salario_base=1000)
    stack["collaborators"].create_collaborator("Beto Individual", setor="Atendimento", salario_base=1000)
    stack["goals"].create_goal(
        nome_meta="Meta individual",
        tipo_meta="individual",
        periodo_mes="05/2026",
        valor_bonus="75,50",
        atingida="sim",
        colaborador_id=ana["colaborador_id"],
    )

    rows = stack["monthly_report"].calculate_month("05/2026")["colaboradores"]
    by_name = {row["nome"]: row for row in rows}

    assert by_name["Ana Individual"]["bonus_meta_aplicado"] == pytest.approx(75.50)
    assert by_name["Beto Individual"]["bonus_meta_aplicado"] == 0


def test_goal_not_achieved_does_not_apply_bonus(stack):
    stack["collaborators"].create_collaborator("Meta Nao Atingida", setor="Atendimento", salario_base=1000)
    stack["goals"].create_goal(
        nome_meta="Meta perdida",
        tipo_meta="coletiva",
        periodo_mes="05/2026",
        valor_bonus=200,
        atingida=False,
    )

    row = stack["monthly_report"].calculate_month("05/2026")["colaboradores"][0]

    assert row["bonus_meta_aplicado"] == 0
    assert row["metas_nao_atingidas"]
    assert row["salario_final"] == pytest.approx(1000)


def test_unexcused_absence_blocks_attendance_and_task_bonus_but_keeps_goal_bonus(stack):
    _setup_payment_month_24_days(stack)
    stack["goals"].create_goal(
        nome_meta="Meta independente",
        tipo_meta="coletiva",
        periodo_mes="02/2026",
        valor_bonus=300,
        atingida=True,
    )

    row = stack["monthly_report"].calculate_month("02/2026")["colaboradores"][0]

    assert row["faltas_nao_abonadas"] == 1
    assert row["bonus_assiduidade_aplicado"] == 0
    assert row["bonus_tarefas_aplicado"] == 0
    assert row["bonus_meta_aplicado"] == pytest.approx(300)
    assert row["salario_final"] == pytest.approx(2600)


def test_occurrences_admin_buttons_do_not_include_resolved_or_pending_actions():
    source = (Path(__file__).resolve().parents[1] / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")

    assert "Marcar resolvida" not in source
    assert "Marcar pendente" not in source
    assert "Abonar falta" in source
    assert 'tag_configure("excused"' in source

def test_payment_report_pdf_breaks_pages_between_summary_and_collaborators(monkeypatch, tmp_path):
    from reportlab.platypus import PageBreak

    from app.pdf import payment_report_pdf

    captured_story = []

    class FakeDoc:
        def __init__(self, path, **_kwargs):
            self.path = path

        def build(self, story):
            captured_story.extend(story)

    monkeypatch.setattr(payment_report_pdf, "get_pdfs_dir", lambda: str(tmp_path))
    monkeypatch.setattr(payment_report_pdf, "SimpleDocTemplate", FakeDoc)

    payment_report_pdf.generate_payment_report_pdf(
        {
            "mes": "05/2026",
            "totais": {},
            "colaboradores": [
                {"nome": "Colaborador 1", "salario_final": 1000},
                {"nome": "Colaborador 2", "salario_final": 1200},
                {"nome": "Colaborador 3", "salario_final": 1300},
            ],
        }
    )

    break_indexes = [idx for idx, item in enumerate(captured_story) if isinstance(item, PageBreak)]
    collaborator_indexes = [
        idx
        for idx, item in enumerate(captured_story)
        if hasattr(item, "getPlainText") and item.getPlainText().startswith("Colaborador:")
    ]

    assert len(break_indexes) == 3
    assert len(collaborator_indexes) == 3
    assert break_indexes[0] < collaborator_indexes[0]
    assert break_indexes[1] < collaborator_indexes[1]
    assert break_indexes[2] < collaborator_indexes[2]

