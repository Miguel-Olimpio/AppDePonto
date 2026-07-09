"""Templates de mensagens do bot WhatsApp."""

from __future__ import annotations


def point_entry_confirmation(nome: str, hora: str) -> str:
    return f"Olá, {nome}. Você bateu seu ponto de entrada às {hora}."


def pause_confirmation(nome: str, hora_pausa: str, retorno_esperado: str) -> str:
    return f"Olá, {nome}. Você bateu o ponto de pausa às {hora_pausa}. Seu retorno está previsto para {retorno_esperado}."


def task_reminder(nome: str, tarefa: str, inicio: str = "", limite: str = "") -> str:
    return f"Olá, {nome}. A tarefa '{tarefa}' deve ser executada até {limite}."


def task_tolerance_reminder(nome: str, tarefa: str, tolerancia: str | int = "") -> str:
    suffix = f" em até {tolerancia} minutos" if str(tolerancia or "").strip() else ""
    return f"Olá, {nome}. A tarefa '{tarefa}' está em atraso. Conclua{suffix} para não receber ocorrência."


def point_reminder(nome: str, tipo_ponto: str) -> str:
    return f"Olá, {nome}. Lembrete para registrar seu ponto de {tipo_ponto}."


def return_reminder(nome: str, horario: str) -> str:
    return f"Olá, {nome}. Seu retorno do intervalo está previsto para {horario}. Não esqueça de bater o ponto."


def return_tolerance_reminder(nome: str, limite_tolerancia: str) -> str:
    return (
        f"Olá, {nome}. Seu retorno do intervalo está em período de tolerância. "
        f"Registre o retorno até {limite_tolerancia} para evitar ocorrência."
    )
