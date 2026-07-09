"""PDF mensal gerencial de ponto, tarefas e salario estimado."""

from __future__ import annotations

import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.config.paths import get_pdfs_dir
from app.utils.dates import format_datetime


def generate_monthly_report_pdf(report: dict) -> str:
    folder = os.path.join(get_pdfs_dir(), "relatorios")
    os.makedirs(folder, exist_ok=True)
    month_file = str(report.get("mes", "mes")).replace("/", "_")
    path = os.path.join(folder, f"relatorio_ponto_tarefas_{month_file}.pdf")
    doc = SimpleDocTemplate(
        path,
        pagesize=landscape(A4),
        rightMargin=1.0 * cm,
        leftMargin=1.0 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("TitleBlue", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#003F7D"))
    normal = styles["BodyText"]
    normal.fontSize = 8
    normal.leading = 10
    header = ParagraphStyle("HeaderWhite", parent=normal, alignment=TA_CENTER, textColor=colors.white)
    story = [
        Paragraph("Relat\u00f3rio Mensal de Ponto e Tarefas", title),
        Spacer(1, 0.15 * cm),
        Paragraph(f"M\u00eas: {report.get('mes', '')} | Gera\u00e7\u00e3o: {format_datetime()}", styles["BodyText"]),
        Paragraph(
            "Este c\u00e1lculo \u00e9 apenas gerencial e deve ser conferido pelo contador ou respons\u00e1vel trabalhista.",
            styles["BodyText"],
        ),
        Spacer(1, 0.35 * cm),
    ]
    story.append(_summary_table(report, normal, header))
    story.append(Spacer(1, 0.35 * cm))
    story.append(Paragraph("Resumo por colaborador", styles["Heading2"]))
    story.append(_collaborator_table(report.get("colaboradores", []), normal, header))
    story.append(Spacer(1, 0.35 * cm))
    story.append(Paragraph("Ocorr\u00eancias e abonos do per\u00edodo", styles["Heading2"]))
    story.append(_occurrence_table(report.get("ocorrencias", []), normal, header))
    doc.build(story)
    return path


def _summary_table(report: dict, normal, header) -> Table:
    totals = report.get("totais", {})
    data = [[Paragraph("Indicador", header), Paragraph("Valor", header)]]
    for label, key in [
        ("Sal\u00e1rio base total", "salario_base"),
        ("Desconto por faltas", "desconto_faltas"),
        ("B\u00f4nus assiduidade", "bonus_assiduidade"),
        ("B\u00f4nus tarefas", "bonus_tarefas"),
        ("Sal\u00e1rio estimado final", "salario_estimado"),
    ]:
        data.append([Paragraph(label, normal), Paragraph(_money(totals.get(key, 0)), normal)])
    table = Table(data, colWidths=[8 * cm, 5 * cm])
    _style(table)
    return table


def _collaborator_table(rows: list[dict], normal, header) -> Table:
    data = [[
        Paragraph("Nome", header), Paragraph("Cargo", header), Paragraph("Sal\u00e1rio", header),
        Paragraph("Jornada", header), Paragraph("Esperados", header), Paragraph("Trabalhados", header),
        Paragraph("Faltas", header), Paragraph("Abonadas", header), Paragraph("Atrasos", header),
        Paragraph("Tarefas falhas", header), Paragraph("Desconto", header), Paragraph("B\u00f4nus", header),
        Paragraph("Final", header),
    ]]
    if not rows:
        data.append([Paragraph("Nenhum colaborador ativo encontrado.", normal)] + [Paragraph("-", normal)] * 12)
    for row in rows:
        data.append([
            Paragraph(_safe(row.get("nome")), normal), Paragraph(_safe(row.get("cargo")), normal),
            Paragraph(_money(row.get("salario_base")), normal), Paragraph(_safe(row.get("jornada")), normal),
            Paragraph(str(row.get("dias_esperados", 0)), normal), Paragraph(str(row.get("dias_trabalhados", 0)), normal),
            Paragraph(str(row.get("faltas_nao_abonadas", 0)), normal), Paragraph(str(row.get("faltas_abonadas", 0)), normal),
            Paragraph(str(row.get("atrasos", 0)), normal),
            Paragraph(str(int(row.get("tarefas_atrasadas", 0)) + int(row.get("tarefas_nao_cumpridas", 0))), normal),
            Paragraph(_money(row.get("desconto_faltas")), normal),
            Paragraph(_money(float(row.get("bonus_assiduidade_concedido", 0)) + float(row.get("bonus_tarefas_concedido", 0))), normal),
            Paragraph(_money(row.get("salario_estimado_final")), normal),
        ])
    table = Table(data, colWidths=[3.0 * cm, 2.3 * cm, 2.0 * cm, 2.4 * cm, 1.5 * cm, 1.7 * cm, 1.2 * cm, 1.5 * cm, 1.2 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 2.0 * cm], repeatRows=1)
    _style(table)
    return table


def _occurrence_table(rows: list[dict], normal, header) -> Table:
    data = [[Paragraph("Data", header), Paragraph("Tipo", header), Paragraph("Colaborador", header), Paragraph("Status", header), Paragraph("Abono", header), Paragraph("Motivo", header), Paragraph("Descri\u00e7\u00e3o", header)]]
    if not rows:
        data.append([Paragraph("Nenhuma ocorr\u00eancia no per\u00edodo.", normal)] + [Paragraph("-", normal)] * 6)
    for row in rows:
        data.append([
            Paragraph(_safe(row.get("data")), normal), Paragraph(_safe(row.get("tipo")), normal),
            Paragraph(_safe(row.get("nome_colaborador")), normal), Paragraph(_safe(row.get("status")), normal),
            Paragraph("Sim" if row.get("abonado") else "N\u00e3o", normal), Paragraph(_safe(row.get("motivo_abono")), normal),
            Paragraph(_safe(row.get("descricao")), normal),
        ])
    table = Table(data, colWidths=[1.8 * cm, 3.3 * cm, 3.2 * cm, 1.9 * cm, 1.5 * cm, 3.4 * cm, 10.0 * cm], repeatRows=1)
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
