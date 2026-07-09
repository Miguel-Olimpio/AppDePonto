"""PDF de ocorrencias operacionais."""

from __future__ import annotations

import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.config.paths import get_pdfs_dir
from app.utils.dates import format_datetime


def generate_occurrence_report_pdf(rows: list[dict], *, data_inicio: str = "", data_fim: str = "") -> str:
    folder = os.path.join(get_pdfs_dir(), "ocorrencias")
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"relatorio_ocorrencias_{stamp}.pdf"
    path = os.path.join(folder, filename)

    doc = SimpleDocTemplate(
        path,
        pagesize=landscape(A4),
        rightMargin=1.1 * cm,
        leftMargin=1.1 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "OccurrenceTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#003F7D"),
        fontSize=16,
        leading=20,
    )
    normal = styles["BodyText"]
    normal.fontSize = 8
    normal.leading = 10
    header = ParagraphStyle(
        "OccurrenceHeader",
        parent=normal,
        textColor=colors.white,
        alignment=TA_CENTER,
        fontSize=8,
        leading=10,
    )

    story = [
        Paragraph("Relat\u00f3rio de Ocorr\u00eancias", title_style),
        Spacer(1, 0.18 * cm),
        Paragraph(_period_text(data_inicio, data_fim), styles["BodyText"]),
        Paragraph(f"Data de gera\u00e7\u00e3o: {format_datetime()}", styles["BodyText"]),
        Spacer(1, 0.35 * cm),
    ]

    if not rows:
        story.append(Paragraph("Nenhuma ocorr\u00eancia encontrada para os filtros selecionados.", styles["BodyText"]))
    else:
        data = [[
            Paragraph("Data", header),
            Paragraph("Tipo", header),
            Paragraph("Colaborador", header),
            Paragraph("Tarefa", header),
            Paragraph("Status", header),
            Paragraph("A\u00e7\u00e3o tomada", header),
            Paragraph("Respons\u00e1vel", header),
            Paragraph("Descri\u00e7\u00e3o / observa\u00e7\u00f5es", header),
        ]]
        for row in rows:
            description = str(row.get("descricao", "") or "")
            notes = str(row.get("observacoes", "") or "")
            if notes:
                description = f"{description}<br/><b>Obs.:</b> {notes}"
            data.append([
                Paragraph(_safe(row.get("data")), normal),
                Paragraph(_safe(row.get("tipo")), normal),
                Paragraph(_safe(row.get("nome_colaborador")), normal),
                Paragraph(_safe(row.get("nome_tarefa")), normal),
                Paragraph(_safe(row.get("status")), normal),
                Paragraph(_safe(row.get("acao_tomada")), normal),
                Paragraph(_safe(row.get("responsavel_tratativa")), normal),
                Paragraph(description or "-", normal),
            ])

        table = Table(data, colWidths=[1.7 * cm, 3.2 * cm, 3.1 * cm, 3.2 * cm, 1.8 * cm, 4.0 * cm, 2.8 * cm, 6.1 * cm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#005CA9")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C7D9")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F8FC")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(table)

    doc.build(story)
    return path


def _period_text(data_inicio: str, data_fim: str) -> str:
    start = str(data_inicio or "").strip()
    end = str(data_fim or "").strip()
    if start and end:
        return f"Per\u00edodo: {start} a {end}"
    if start:
        return f"A partir de: {start}"
    if end:
        return f"At\u00e9: {end}"
    return "Per\u00edodo: todos os registros"


def _safe(value) -> str:
    text = str(value or "").strip()
    return text or "-"
