from __future__ import annotations

from datetime import datetime

from app.bot.message_templates import (
    pause_confirmation,
    point_entry_confirmation,
    point_reminder,
    return_reminder,
    return_tolerance_reminder,
    task_reminder,
    task_tolerance_reminder,
)
from app.bot.reminder_scheduler import (
    REMINDER_POINT_BREAK_CONFIRMED,
    REMINDER_POINT_ENTRY_CONFIRMED,
    REMINDER_POINT_RETURN,
    REMINDER_POINT_RETURN_TOLERANCE,
    REMINDER_TASK_START,
    REMINDER_TASK_TOLERANCE,
)
from app.bot.whatsapp_bot import normalize_whatsapp_phone
from app.config.settings import SCALE_TYPE_WEEKLY


def test_whatsapp_phone_normalization_accepts_common_brazilian_formats():
    assert normalize_whatsapp_phone("(32) 99999-8888") == "5532999998888"
    assert normalize_whatsapp_phone("32 99999 8888") == "5532999998888"
    assert normalize_whatsapp_phone("55 32 99999-8888") == "5532999998888"
    assert normalize_whatsapp_phone("123") == ""


def test_whatsapp_message_templates_are_rendered():
    assert point_entry_confirmation("João", "08:01") == "Olá, João. Você bateu seu ponto de entrada às 08:01."
    assert pause_confirmation("João", "12:00", "13:00") == "Olá, João. Você bateu o ponto de pausa às 12:00. Seu retorno está previsto para 13:00."
    assert task_reminder("João", "Limpar loja", "12:00", "13:00") == "Olá, João. A tarefa 'Limpar loja' deve ser executada até 13:00."
    assert task_tolerance_reminder("João", "Limpar loja", 15) == "Olá, João. A tarefa 'Limpar loja' está em atraso. Conclua em até 15 minutos para não receber ocorrência."
    assert point_reminder("João", "entrada") == "Olá, João. Lembrete para registrar seu ponto de entrada."
    assert return_reminder("João", "13:00") == "Olá, João. Seu retorno do intervalo está previsto para 13:00. Não esqueça de bater o ponto."
    assert return_tolerance_reminder("João", "13:15") == "Olá, João. Seu retorno do intervalo está em período de tolerância. Registre o retorno até 13:15 para evitar ocorrência."


def test_entry_time_record_sends_confirmation_when_bot_is_connected(stack):
    collaborator = stack["collaborators"].create_collaborator("João", setor="Atendimento", telefone="32999990001")

    record = stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 1))

    assert stack["bot_bridge"].sent[0][0] == "5532999990001"
    assert stack["bot_bridge"].sent[0][1] == "Olá, João. Você bateu seu ponto de entrada às 08:01."
    assert stack["bot"].queued_messages()[0]["tipo"] == REMINDER_POINT_ENTRY_CONFIRMED
    assert stack["bot"].queued_messages()[0]["ponto_id"] == record["ponto_id"]


def test_entry_time_record_does_not_break_when_bot_is_disconnected(stack):
    collaborator = stack["collaborators"].create_collaborator("Sem Conexão", setor="Atendimento", telefone="32999990002")
    stack["bot_bridge"].status = "Desconectado"

    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))

    assert stack["bot_bridge"].sent == []
    reminders = stack["bot"].sent_reminders()
    assert reminders[0]["status"] == "bot desconectado"


def test_entry_time_record_without_valid_phone_is_logged_without_sending(stack):
    collaborator = stack["collaborators"].create_collaborator("Telefone Ruim", setor="Atendimento", telefone="123")

    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))

    assert stack["bot_bridge"].sent == []
    assert stack["bot"].sent_reminders()[0]["status"] == "telefone inválido"


def test_task_reminder_requires_entry_before_sending(stack):
    journey = stack["journeys"].create_journey("Comercial", tipo_escala=SCALE_TYPE_WEEKLY, entrada="08:00", saida="17:00", dias_semana="segunda")
    stack["collaborators"].create_collaborator("Maria Limpeza", setor="Limpeza", telefone="32999990003", jornada_id=journey["jornada_id"])
    stack["tasks"].create_task("Limpar loja", horario_inicio="12:00", horario_limite="13:00", nome_setor="Limpeza", dias_semana="segunda")

    rows = stack["bot"].run_scheduler_once(datetime(2026, 5, 4, 12, 0))

    assert rows == []


def test_task_reminder_selects_collaborators_by_entry_sector_and_journey(stack):
    journey = stack["journeys"].create_journey("Comercial", tipo_escala=SCALE_TYPE_WEEKLY, entrada="08:00", saida="17:00", dias_semana="segunda")
    target = stack["collaborators"].create_collaborator("Maria Limpeza", setor="Limpeza", telefone="(32) 99999-0004", jornada_id=journey["jornada_id"])
    other = stack["collaborators"].create_collaborator("João Atendimento", setor="Atendimento", telefone="(32) 99999-0005", jornada_id=journey["jornada_id"])
    stack["time"].record_time(target["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    stack["time"].record_time(other["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    task = stack["tasks"].create_task("Limpar loja", descricao="Limpeza da loja", horario_inicio="12:00", horario_limite="13:00", nome_setor="Limpeza", dias_semana="segunda")
    stack["bot_bridge"].sent.clear()

    rows = stack["bot"].run_scheduler_once(datetime(2026, 5, 4, 12, 0))

    task_rows = [row for row in rows if row["tipo"] == REMINDER_TASK_START]
    assert len(task_rows) == 1
    assert task_rows[0]["colaborador_id"] == target["colaborador_id"]
    assert task_rows[0]["tarefa_id"] == task["tarefa_id"]
    assert "Limpeza da loja" in task_rows[0]["mensagem"]


def test_task_tolerance_reminder_and_duplicate_guard(stack):
    journey = stack["journeys"].create_journey("Comercial", entrada="08:00", saida="17:00", dias_semana="segunda")
    collaborator = stack["collaborators"].create_collaborator("Carlos", setor="Atendimento", telefone="32999990006", jornada_id=journey["jornada_id"])
    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    stack["tasks"].create_task("Conferir caixa", horario_inicio="12:00", horario_limite="13:00", tolerancia_minutos=15, nome_setor="Atendimento", dias_semana="segunda")

    first = stack["bot"].run_scheduler_once(datetime(2026, 5, 4, 13, 5))
    second = stack["bot"].run_scheduler_once(datetime(2026, 5, 4, 13, 6))

    tolerance_rows = [row for row in first if row["tipo"] == REMINDER_TASK_TOLERANCE]
    assert len(tolerance_rows) == 1
    assert "em até 15 minutos" in tolerance_rows[0]["mensagem"]
    assert [row for row in second if row["tipo"] == REMINDER_TASK_TOLERANCE] == []


def test_pause_confirmation_uses_pause_plus_journey_interval(stack):
    journey = stack["journeys"].create_journey("Com intervalo", entrada="08:00", saida="17:00", tempo_intervalo=60, dias_semana="segunda")
    collaborator = stack["collaborators"].create_collaborator("Bruna", setor="Atendimento", telefone="32999990007", jornada_id=journey["jornada_id"])
    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    stack["bot_bridge"].sent.clear()

    record = stack["time"].record_time(collaborator["colaborador_id"], "pausa", when=datetime(2026, 5, 4, 12, 0))

    assert stack["bot_bridge"].sent[-1][1] == "Olá, Bruna. Você bateu o ponto de pausa às 12:00. Seu retorno está previsto para 13:00."
    assert stack["bot"].queued_messages()[-1]["tipo"] == REMINDER_POINT_BREAK_CONFIRMED
    assert stack["bot"].queued_messages()[-1]["ponto_id"] == record["ponto_id"]


def test_return_reminder_uses_pause_plus_journey_interval(stack):
    journey = stack["journeys"].create_journey("Com intervalo", entrada="08:00", saida="17:00", tempo_intervalo=60, tolerancia_minutos=15, dias_semana="segunda")
    collaborator = stack["collaborators"].create_collaborator("Bia", setor="Atendimento", telefone="32999990008", jornada_id=journey["jornada_id"])
    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    stack["time"].record_time(collaborator["colaborador_id"], "pausa", when=datetime(2026, 5, 4, 12, 0))
    stack["bot"].save_config({"minutos_antes_inicio": "10"})

    rows = stack["bot"].run_scheduler_once(datetime(2026, 5, 4, 12, 55))

    return_rows = [row for row in rows if row["tipo"] == REMINDER_POINT_RETURN]
    assert len(return_rows) == 1
    assert "13:00" in return_rows[0]["mensagem"]


def test_return_tolerance_reminder_uses_limit_and_duplicate_guard(stack):
    journey = stack["journeys"].create_journey("Com intervalo", entrada="08:00", saida="17:00", tempo_intervalo=60, tolerancia_minutos=15, dias_semana="segunda")
    collaborator = stack["collaborators"].create_collaborator("Dora", setor="Atendimento", telefone="32999990009", jornada_id=journey["jornada_id"])
    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    stack["time"].record_time(collaborator["colaborador_id"], "pausa", when=datetime(2026, 5, 4, 12, 0))

    first = stack["bot"].run_scheduler_once(datetime(2026, 5, 4, 13, 5))
    second = stack["bot"].run_scheduler_once(datetime(2026, 5, 4, 13, 6))

    rows = [row for row in first if row["tipo"] == REMINDER_POINT_RETURN_TOLERANCE]
    assert len(rows) == 1
    assert "13:15" in rows[0]["mensagem"]
    assert [row for row in second if row["tipo"] == REMINDER_POINT_RETURN_TOLERANCE] == []


def test_invalid_phone_is_logged_without_sending(stack):
    journey = stack["journeys"].create_journey("Comercial", entrada="08:00", saida="17:00", dias_semana="segunda")
    collaborator = stack["collaborators"].create_collaborator("Sem Telefone", setor="Atendimento", telefone="123", jornada_id=journey["jornada_id"])
    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    stack["tasks"].create_task("Abrir loja", horario_inicio="08:00", horario_limite="09:00", nome_setor="Atendimento", dias_semana="segunda")

    rows = stack["bot"].run_scheduler_once(datetime(2026, 5, 4, 8, 0))

    assert rows[0]["status"] == "telefone inválido"
    assert stack["bot_bridge"].sent == []


def test_queue_marks_message_sent_only_after_node_confirmation(stack):
    journey = stack["journeys"].create_journey("Comercial", entrada="08:00", saida="17:00", dias_semana="segunda")
    collaborator = stack["collaborators"].create_collaborator("Ana", setor="Atendimento", telefone="32999990010", jornada_id=journey["jornada_id"])
    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    stack["tasks"].create_task("Abrir loja", horario_inicio="08:00", horario_limite="09:00", nome_setor="Atendimento", dias_semana="segunda")
    stack["bot_bridge"].sent.clear()

    queued = stack["bot"].run_scheduler_once(datetime(2026, 5, 4, 8, 0))
    task_queue = [row for row in queued if row["tipo"] == REMINDER_TASK_START]
    assert task_queue[0]["status"] == "pendente"

    stack["bot"].process_message_queue_once(datetime(2026, 5, 4, 8, 1))
    message_id = task_queue[0]["mensagem_id"]
    rows = [row for row in stack["bot"].queued_messages() if row["mensagem_id"] == message_id]
    assert rows[0]["status"] == "enviando"

    stack["bot"]._handle_event({"event": "send_result", "id": message_id, "ok": True, "message": "Mensagem enviada com sucesso."})

    rows = [row for row in stack["bot"].queued_messages() if row["mensagem_id"] == message_id]
    assert rows[0]["status"] == "enviado"
    sent = [row for row in stack["bot"].sent_reminders() if row["lembrete_id"] == message_id]
    assert sent[0]["colaborador_id"] == collaborator["colaborador_id"]


def test_queue_failure_schedules_retry(stack):
    journey = stack["journeys"].create_journey("Comercial", entrada="08:00", saida="17:00", dias_semana="segunda")
    collaborator = stack["collaborators"].create_collaborator("Pedro", setor="Atendimento", telefone="32999990011", jornada_id=journey["jornada_id"])
    stack["time"].record_time(collaborator["colaborador_id"], "entrada", when=datetime(2026, 5, 4, 8, 0))
    stack["tasks"].create_task("Conferir balcão", horario_inicio="08:00", horario_limite="09:00", nome_setor="Atendimento", dias_semana="segunda")
    stack["bot_bridge"].sent.clear()

    queued = [row for row in stack["bot"].run_scheduler_once(datetime(2026, 5, 4, 8, 0)) if row["tipo"] == REMINDER_TASK_START]
    stack["bot"].process_message_queue_once(datetime(2026, 5, 4, 8, 1))
    message_id = queued[0]["mensagem_id"]

    stack["bot"]._handle_event({"event": "send_result", "id": message_id, "ok": False, "message": "Falha temporária."})

    rows = [row for row in stack["bot"].queued_messages() if row["mensagem_id"] == message_id]
    assert rows[0]["status"] == "erro"
    assert rows[0]["ultimo_erro"] == "Falha temporária."
    assert rows[0]["proxima_tentativa_em"]
