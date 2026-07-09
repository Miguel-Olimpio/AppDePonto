"""Constantes do Controle de Ponto e Tarefas."""

APP_TITLE = "Controle de Ponto e Tarefas"
APP_THEME = "flatly"

DATABASE_FILENAME = "banco_ponto_tarefas.xlsx"
COLLABORATORS_DATABASE_FILENAME = "colaboradores.xlsx"
POINT_DATABASE_FILENAME = "ponto.xlsx"
TASKS_DATABASE_FILENAME = "tarefas_pops.xlsx"
OCCURRENCES_DATABASE_FILENAME = "ocorrencias.xlsx"
SECTORS_DATABASE_FILENAME = "setores.xlsx"
BOT_CONFIG_DATABASE_FILENAME = "bot_config.xlsx"
GOALS_DATABASE_FILENAME = "metas.xlsx"

BACKUP_STEM = "banco_ponto_tarefas"

SHEET_COLLABORATORS = "Colaboradores"
SHEET_TIME_RECORDS = "Pontos"
SHEET_TASKS = "Tarefas"
SHEET_TASK_CHECKS = "ChecksTarefas"
SHEET_OCCURRENCES = "Ocorrencias"
SHEET_JOURNEYS = "Jornadas"
SHEET_SECTORS = "Setores"
SHEET_BOT_CONFIG = "Config"
SHEET_SENT_REMINDERS = "LembretesEnviados"
SHEET_BOT_QUEUE = "FilaMensagensBot"
SHEET_GOALS = "Metas"

COLLABORATOR_STATUS_ACTIVE = "ativo"
COLLABORATOR_STATUS_INACTIVE = "inativo"

SCALE_TYPE_WEEKLY = "Semanal fixa"
SCALE_TYPE_SCALE = "Escala"
SCALE_TYPE_12X36 = SCALE_TYPE_SCALE  # Compatibilidade com versões anteriores.
SCALE_TYPES = (SCALE_TYPE_WEEKLY, SCALE_TYPE_SCALE)

TIME_RECORD_TYPES = ("entrada", "pausa", "retorno", "saída")

TASK_STATUS_DONE = "cumprida"
TASK_STATUS_LATE = "atrasada"
TASK_STATUS_MISSED = "não cumprida"
TASK_STATUS_PENDING = "pendente"
TASK_STATUS_PARTIAL = "parcial"
TASK_STATUS_IN_PROGRESS = "em execução"
TASK_STATUS_TOLERANCE = "em tolerância"

OCCURRENCE_POINT_MISSING = "falta"
OCCURRENCE_POINT_LATE = "ponto atrasado"
OCCURRENCE_BREAK_OUT_OF_TIME = "pausa fora do horário"
OCCURRENCE_RETURN_OUT_OF_TIME = "retorno fora do horário"
OCCURRENCE_EXIT_OUT_OF_TIME = "saída fora do horário"
OCCURRENCE_TASK_MISSED = "tarefa não cumprida"
OCCURRENCE_TASK_LATE = "tarefa atrasada"

OCCURRENCE_STATUS_OPEN = "pendente"
OCCURRENCE_STATUS_RESOLVED = "resolvida"
OCCURRENCE_STATUSES = (OCCURRENCE_STATUS_OPEN, OCCURRENCE_STATUS_RESOLVED)

DATE_FORMAT = "%d/%m/%Y"
TIME_FORMAT = "%H:%M"
DATETIME_FORMAT = "%d/%m/%Y %H:%M:%S"

WEEKDAY_NAMES = (
    "segunda",
    "terça",
    "quarta",
    "quinta",
    "sexta",
    "sábado",
    "domingo",
)

GOAL_TYPE_COLLECTIVE = "coletiva"
GOAL_TYPE_INDIVIDUAL = "individual"
GOAL_TYPES = (GOAL_TYPE_COLLECTIVE, GOAL_TYPE_INDIVIDUAL)
