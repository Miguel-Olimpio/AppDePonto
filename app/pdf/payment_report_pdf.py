"""PDF de pagamento mensal estimado por colaborador."""

from __future__ import annotations

import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.config.paths import get_pdfs_dir
from app.utils.dates import format_datetime


WARNING_TEXT = (
    "Este relatório é uma estimativa gerencial e deve ser conferido pelo "
    "responsável da empresa ou contador."
)


def generate_payment_report_pdf(report: dict) -> str:
    folder = os.path.join(get_pdfs_dir(), "relatorios_pagamento")
    os.makedirs(folder, exist_ok=True)
    month_file = str(report.get("mes", "mes")).replace("/", "_")
    path = os.path.join(folder, f"relatorio_pagamento_{month_file}.pdf")
    doc = SimpleDocTemplate(
        path,
        pagesize=landscape(A4),
        rightMargin=1.0 * cm,
        leftMargin=1.0 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleBlue",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#003F7D"),
    )
    normal = styles["BodyText"]
    normal.fontSize = 8
    normal.leading = 10
    header = ParagraphStyle("HeaderWhite", parent=normal, alignment=TA_CENTER, textColor=colors.white)
    section = ParagraphStyle("Section", parent=styles["Heading2"], textColor=colors.HexColor("#003F7D"), fontSize=12)

    story = [
        Paragraph("Relatório de Pagamento Estimado", title),
        Spacer(1, 0.12 * cm),
        Paragraph(f"Mês: {report.get('mes', '')} | Geração: {format_datetime()}", styles["BodyText"]),
        Paragraph(WARNING_TEXT, styles["BodyText"]),
        Spacer(1, 0.25 * cm),
        Paragraph("Resumo geral", section),
        _summary_table(report, normal, header),
        Spacer(1, 0.25 * cm),
    ]

    collaborators = report.get("colaboradores", [])
    if not collaborators:
        story.append(Paragraph("Nenhum colaborador ativo encontrado neste per?odo.", normal))
    else:
        story.append(PageBreak())
        for index, row in enumerate(collaborators):
            if index > 0:
                story.append(PageBreak())
            story.extend(_collaborator_section(row, styles, normal, header, section))

    doc.build(story)
    return path


def _summary_table(report: dict, normal, header) -> Table:
    totals = report.get("totais", {})
    data = [[Paragraph("Indicador", header), Paragraph("Valor", header)]]
    for label, key in [
        ("Salário base total", "salario_base"),
        ("Desconto por faltas", "desconto_faltas"),
        ("Bônus de assiduidade aplicado", "bonus_assiduidade"),
        ("Bônus por tarefas aplicado", "bonus_tarefas"),
        ("Bônus por meta aplicado", "bonus_meta"),
        ("Valor estimado total", "salario_estimado"),
    ]:
        data.append([Paragraph(label, normal), Paragraph(_money(totals.get(key, 0)), normal)])
    table = Table(data, colWidths=[8 * cm, 5 * cm])
    _style(table)
    return table


def _collaborator_section(row: dict, styles, normal, header, section) -> list:
    name = _safe(row.get("nome"))
    story = [Paragraph(f"Colaborador: {name}", section)]
    if row.get("sem_dias_esperados_aviso"):
        story.append(Paragraph(str(row.get("sem_dias_esperados_aviso")), normal))
    story.append(Paragraph("Tabela 1 - Resumo salarial", styles["Heading3"]))
    story.append(_payment_table(row, normal, header))
    story.append(Spacer(1, 0.12 * cm))
    story.append(Paragraph(_safe(row.get("mensagem_assiduidade")), normal))
    story.append(Paragraph(_safe(row.get("mensagem_tarefas")), normal))
    story.append(Paragraph(_safe(row.get("mensagem_metas")), normal))
    story.append(
        Paragraph(
            "Cálculo: salário final = salário base - desconto por faltas + "
            "bônus de assiduidade aplicado + bônus por tarefas aplicado + bônus meta aplicado.",
            normal,
        )
    )
    story.append(Spacer(1, 0.10 * cm))
    story.append(Paragraph("Tabela 2 - Faltas e abonos", styles["Heading3"]))
    story.append(_absence_combined_table(row, normal, header))
    story.append(Spacer(1, 0.10 * cm))
    story.append(Paragraph("Tabela 3 - Tarefas, metas e ocorrências", styles["Heading3"]))
    story.append(_task_goal_table(row, normal, header))
    story.append(Spacer(1, 0.28 * cm))
    return story


def _payment_table(row: dict, normal, header) -> Table:
    data = [
        [Paragraph("Campo", header), Paragraph("Valor", header), Paragraph("Campo", header), Paragraph("Valor", header)],
        [Paragraph("Cargo", normal), Paragraph(_safe(row.get("cargo")), normal), Paragraph("Setor", normal), Paragraph(_safe(row.get("setor")), normal)],
        [Paragraph("Jornada", normal), Paragraph(_safe(row.get("jornada")), normal), Paragraph("Salário base", normal), Paragraph(_money(row.get("salario_base")), normal)],
        [Paragraph("Dias esperados", normal), Paragraph(str(row.get("dias_esperados", 0)), normal), Paragraph("Dias trabalhados", normal), Paragraph(str(row.get("dias_trabalhados", 0)), normal)],
        [Paragraph("Faltas", normal), Paragraph(str(row.get("faltas", 0)), normal), Paragraph("Faltas abonadas", normal), Paragraph(str(row.get("faltas_abonadas", 0)), normal)],
        [Paragraph("Faltas não abonadas", normal), Paragraph(str(row.get("faltas_nao_abonadas", 0)), normal), Paragraph("Salário dia", normal), Paragraph(_money(row.get("salario_dia")), normal)],
        [Paragraph("Desconto por faltas", normal), Paragraph(_money(row.get("desconto_faltas")), normal), Paragraph("Atrasos", normal), Paragraph(str(row.get("atrasos", 0)), normal)],
        [Paragraph("Retornos atrasados", normal), Paragraph(str(row.get("retornos_pausa_atrasados", 0)), normal), Paragraph("Tarefas falhas", normal), Paragraph(str(int(row.get("tarefas_atrasadas", 0)) + int(row.get("tarefas_nao_cumpridas", 0))), normal)],
        [Paragraph("Bônus assiduidade aplicado", normal), Paragraph(_money(row.get("bonus_assiduidade_aplicado")), normal), Paragraph("Bônus tarefas aplicado", normal), Paragraph(_money(row.get("bonus_tarefas_aplicado")), normal)],
        [Paragraph("Bônus meta aplicado", normal), Paragraph(_money(row.get("bonus_meta_aplicado")), normal), Paragraph("", normal), Paragraph("", normal)],
        [Paragraph(f"SALÁRIO FINAL CALCULADO: {_money(row.get('salario_final'))}", header), "", "", ""],
    ]
    table = Table(data, colWidths=[5.0 * cm, 3.0 * cm, 5.0 * cm, 3.0 * cm], repeatRows=1)
    _style(table)
    final_row = len(data) - 1
    table.setStyle(TableStyle([
        ("SPAN", (0, final_row), (-1, final_row)),
        ("BACKGROUND", (0, final_row), (-1, final_row), colors.HexColor("#003F7D")),
        ("TEXTCOLOR", (0, final_row), (-1, final_row), colors.white),
        ("ALIGN", (0, final_row), (-1, final_row), "CENTER"),
        ("VALIGN", (0, final_row), (-1, final_row), "MIDDLE"),
    ]))
    return table


def _absence_combined_table(row: dict, normal, header) -> Table:
    data = [[Paragraph("Data", header), Paragraph("Tipo", header), Paragraph("Abonado", header), Paragraph("Motivo do abono", header), Paragraph("Impacto no salário", header)]]
    rows = []
    for item in row.get("faltas_nao_abonadas_detalhes", []):
        rows.append([
            Paragraph(_safe(item.get("data")), normal),
            Paragraph("falta", normal),
            Paragraph("Não", normal),
            Paragraph(_safe(item.get("motivo")), normal),
            Paragraph(_safe(item.get("impacto")), normal),
        ])
    for item in row.get("faltas_abonadas_detalhes", []):
        rows.append([
            Paragraph(_safe(item.get("data")), normal),
            Paragraph("falta", normal),
            Paragraph("Sim", normal),
            Paragraph(_safe(item.get("motivo")), normal),
            Paragraph(_safe(item.get("impacto")), normal),
        ])
    if not rows:
        rows.append([Paragraph("Nenhuma falta registrada no período.", normal), Paragraph("-", normal), Paragraph("-", normal), Paragraph("-", normal), Paragraph("-", normal)])
    data.extend(rows)
    table = Table(data, colWidths=[2.2 * cm, 4.0 * cm, 2.4 * cm, 7.0 * cm, 7.0 * cm], repeatRows=1)
    _style(table)
    return table


def _task_goal_table(row: dict, normal, header) -> Table:
    data = [[Paragraph("Data", header), Paragraph("Tipo", header), Paragraph("Tarefa/meta", header), Paragraph("Descrição", header), Paragraph("Impacto no bônus", header)]]
    rows = []
    for item in row.get("tarefas_falhas_detalhes", []):
        rows.append([
            Paragraph(_safe(item.get("data")), normal),
            Paragraph(_safe(item.get("tipo")), normal),
            Paragraph(_safe(item.get("tarefa")), normal),
            Paragraph(_safe(item.get("descricao")), normal),
            Paragraph(_safe(item.get("impacto")), normal),
        ])
    for item in row.get("metas_detalhes", []):
        rows.append([
            Paragraph(_safe(item.get("data")), normal),
            Paragraph(_safe(item.get("tipo")), normal),
            Paragraph(_safe(item.get("nome")), normal),
            Paragraph(_safe(item.get("descricao")), normal),
            Paragraph(_safe(item.get("impacto")), normal),
        ])
    if not rows:
        rows.append([Paragraph("Nenhuma falha de tarefa ou meta registrada no período.", normal), Paragraph("-", normal), Paragraph("-", normal), Paragraph("-", normal), Paragraph("-", normal)])
    data.extend(rows)
    table = Table(data, colWidths=[2.2 * cm, 4.4 * cm, 5.6 * cm, 7.2 * cm, 6.2 * cm], repeatRows=1)
    _style(table)
    return table


def _style(table: Table) -> None:
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#005CA9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C7D9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F8FC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))


def _safe(value) -> str:
    return str(value or "-").strip() or "-"


def _money(value) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0.0
    return f"R$ {number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
