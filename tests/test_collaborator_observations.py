from __future__ import annotations

from app.ui.collaborator_view import (
    _format_observation_sections,
    _format_task_observation,
    _observation_text,
    _row_has_observation,
)


def test_detects_task_observation_text():
    row = {"observacoes": "  Texto longo cadastrado pelo administrador.  "}

    assert _row_has_observation(row)
    assert _observation_text(row) == "Texto longo cadastrado pelo administrador."


def test_detects_legacy_observation_field_names():
    assert _observation_text({"observacao": "Observacao antiga"}) == "Observacao antiga"
    assert _observation_text({"Observações": "Observacao com acento"}) == "Observacao com acento"


def test_ignores_empty_observation_text():
    assert not _row_has_observation({"observacoes": "   "})
    assert not _row_has_observation({})


def test_formats_multiple_read_only_observation_sections():
    text = _format_observation_sections(
        [
            ("Colaborador", "Aviso do cadastro."),
            ("Jornada / Escala", "Orientacao da jornada."),
            ("Sem texto", ""),
        ]
    )

    assert "Colaborador" in text
    assert "Aviso do cadastro." in text
    assert "Jornada / Escala" in text
    assert "Orientacao da jornada." in text
    assert "Sem texto" not in text


def test_formats_task_observation_with_name_and_schedule():
    text = _format_task_observation(
        {
            "nome": "Limpar balcão",
            "descricao": "Conferir o POP antes de iniciar.",
            "horario_inicio": "08:00",
            "horario_limite": "09:00",
            "observacoes": "Usar checklist do POP.",
        }
    )

    assert "Limpar balcão" in text
    assert "Conferir o POP antes de iniciar." in text
    assert "08:00" in text
    assert "09:00" in text
    assert "Usar checklist do POP." in text
