"""Schemas canonicos dos workbooks Excel do AppDePonto."""

from __future__ import annotations

from app.config.settings import (
    SHEET_COLLABORATORS,
    SHEET_JOURNEYS,
    SHEET_OCCURRENCES,
    SHEET_SECTORS,
    SHEET_TASK_CHECKS,
    SHEET_TASKS,
    SHEET_TIME_RECORDS,
    SHEET_BOT_CONFIG,
    SHEET_SENT_REMINDERS,
    SHEET_BOT_QUEUE,
    SHEET_GOALS,
)

COLLABORATOR_HEADERS = [
    "colaborador_id",
    "nome",
    "cargo",
    "telefone",
    "setor_id",
    "nome_setor",
    "salario_base",
    "jornada_id",
    "bonus_assiduidade",
    "bonus_tarefas",
    "status",
    "data_cadastro",
    "data_atualizacao",
    "observacoes",
]

TIME_RECORD_HEADERS = [
    "ponto_id",
    "colaborador_id",
    "nome_colaborador",
    "tipo_ponto",
    "data",
    "hora",
    "data_hora",
    "observacoes",
]

JOURNEY_HEADERS = [
    "jornada_id",
    "nome",
    "tipo_jornada",
    "entrada",
    "saida",
    "carga_horaria",
    "tempo_intervalo",
    "tolerancia_minutos",
    "dias_semana",
    "descricao_escala",
    "horas_trabalho",
    "horas_descanso",
    "data_inicio_escala",
    "horario_inicio_escala",
    "active",
    "data_cadastro",
    "data_atualizacao",
    "observacoes",
]

TASK_HEADERS = [
    "tarefa_id",
    "nome",
    "descricao",
    "horario_inicio",
    "horario_limite",
    "tolerancia_minutos",
    "dias_semana",
    "setor_id",
    "nome_setor",
    "active",
    "data_cadastro",
    "data_atualizacao",
    "observacoes",
]

TASK_CHECK_HEADERS = [
    "check_id",
    "tarefa_id",
    "nome_tarefa",
    "colaborador_id",
    "nome_colaborador",
    "data",
    "hora_check",
    "status",
    "observacoes",
]

OCCURRENCE_HEADERS = [
    "ocorrencia_id",
    "data",
    "tipo",
    "descricao",
    "colaborador_id",
    "nome_colaborador",
    "tarefa_id",
    "nome_tarefa",
    "setor_id",
    "nome_setor",
    "horario_limite",
    "data_hora_registro",
    "status",
    "abonado",
    "motivo_abono",
    "observacao_abono",
    "data_abono",
]

SECTOR_HEADERS = [
    "setor_id",
    "nome",
    "descricao",
    "active",
    "data_cadastro",
    "data_atualizacao",
]

BOT_CONFIG_HEADERS = [
    "chave",
    "valor",
]

SENT_REMINDER_HEADERS = [
    "lembrete_id",
    "data",
    "tipo",
    "colaborador_id",
    "nome_colaborador",
    "tarefa_id",
    "nome_tarefa",
    "ponto_id",
    "telefone",
    "enviado_em",
    "status",
    "observacoes",
]

BOT_QUEUE_HEADERS = [
    "mensagem_id",
    "data",
    "tipo",
    "colaborador_id",
    "nome_colaborador",
    "telefone",
    "tarefa_id",
    "nome_tarefa",
    "ponto_id",
    "mensagem",
    "status",
    "tentativas",
    "proxima_tentativa_em",
    "ultimo_erro",
    "criado_em",
    "enviado_em",
    "observacoes",
]

GOAL_HEADERS = [
    "meta_id",
    "nome_meta",
    "tipo_meta",
    "descricao",
    "periodo_mes",
    "valor_bonus",
    "valor_meta",
    "valor_realizado",
    "atingida",
    "colaborador_id",
    "nome_colaborador",
    "active",
    "data_cadastro",
    "data_atualizacao",
    "observacoes",
]

# Mantido apenas para compatibilidade de chamadas antigas em codigo legado.
WORK_SCHEDULE_HEADERS = [
    "entrada",
    "saida",
    "carga_horaria",
    "tempo_intervalo",
    "tolerancia_minutos",
    "data_atualizacao",
]

COLLABORATORS_SHEETS_CONFIG = {
    SHEET_COLLABORATORS: COLLABORATOR_HEADERS,
}

POINT_SHEETS_CONFIG = {
    SHEET_TIME_RECORDS: TIME_RECORD_HEADERS,
    SHEET_JOURNEYS: JOURNEY_HEADERS,
}

TASKS_SHEETS_CONFIG = {
    SHEET_TASKS: TASK_HEADERS,
    SHEET_TASK_CHECKS: TASK_CHECK_HEADERS,
}

OCCURRENCES_SHEETS_CONFIG = {
    SHEET_OCCURRENCES: OCCURRENCE_HEADERS,
}

SECTORS_SHEETS_CONFIG = {
    SHEET_SECTORS: SECTOR_HEADERS,
}

BOT_SHEETS_CONFIG = {
    SHEET_BOT_CONFIG: BOT_CONFIG_HEADERS,
    SHEET_SENT_REMINDERS: SENT_REMINDER_HEADERS,
    SHEET_BOT_QUEUE: BOT_QUEUE_HEADERS,
}

GOALS_SHEETS_CONFIG = {
    SHEET_GOALS: GOAL_HEADERS,
}

SHEETS_CONFIG = {
    SHEET_COLLABORATORS: COLLABORATOR_HEADERS,
    SHEET_TIME_RECORDS: TIME_RECORD_HEADERS,
    SHEET_JOURNEYS: JOURNEY_HEADERS,
    SHEET_TASKS: TASK_HEADERS,
    SHEET_TASK_CHECKS: TASK_CHECK_HEADERS,
    SHEET_OCCURRENCES: OCCURRENCE_HEADERS,
    SHEET_SECTORS: SECTOR_HEADERS,
}
