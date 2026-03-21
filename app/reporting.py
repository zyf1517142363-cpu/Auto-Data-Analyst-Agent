import os
from typing import Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _table_from_dict(data: Dict) -> Table:
    rows = [["Metric", "Value"]]
    rows += [[key, str(value)] for key, value in data.items()]
    table = Table(rows, colWidths=[2.4 * inch, 3.6 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def build_pdf_report(
    report_path: str,
    overview: Dict,
    column_summary: List[Dict],
    numeric_stats: List[Dict],
    categorical_preview: Dict,
    modeling: Dict,
    figures: List[str],
    summary: str,
) -> None:
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(report_path, pagesize=letter)
    story = []

    story.append(Paragraph("Auto Data Analyst Report", styles["Title"]))
    story.append(Paragraph("Executive Summary", styles["Heading2"]))
    story.append(Paragraph(summary, styles["BodyText"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Dataset Overview", styles["Heading2"]))
    story.append(_table_from_dict(overview))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Columns Snapshot (Top 12)", styles["Heading2"]))
    col_rows = [["Name", "Type", "Missing", "Unique", "Example"]]
    for item in column_summary[:12]:
        col_rows.append(
            [
                item["name"],
                item["dtype"],
                str(item["missing"]),
                str(item["unique"]),
                item["example"],
            ]
        )
    col_table = Table(col_rows, repeatRows=1)
    col_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#22223B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(col_table)
    story.append(Spacer(1, 0.2 * inch))

    if numeric_stats:
        story.append(Paragraph("Numeric Summary (Top 10)", styles["Heading2"]))
        num_rows = [
            ["Column", "Mean", "Std", "Min", "Median", "Max", "Missing"]
        ]
        for item in numeric_stats[:10]:
            num_rows.append(
                [
                    item["index"],
                    f"{item.get('mean', 0):.3f}",
                    f"{item.get('std', 0):.3f}",
                    f"{item.get('min', 0):.3f}",
                    f"{item.get('50%', 0):.3f}",
                    f"{item.get('max', 0):.3f}",
                    str(item.get("missing", 0)),
                ]
            )
        num_table = Table(num_rows, repeatRows=1)
        num_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4A4E69")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(num_table)
        story.append(Spacer(1, 0.2 * inch))

    if categorical_preview:
        story.append(Paragraph("Categorical Preview", styles["Heading2"]))
        for col, values in categorical_preview.items():
            story.append(Paragraph(f"{col} (Top values)", styles["Heading4"]))
            rows = [["Value", "Count"]]
            for item in values:
                rows.append([item["value"], str(item["count"])])
            table = Table(rows, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#9A8C98")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Modeling Results", styles["Heading2"]))
    story.append(_table_from_dict(modeling))
    story.append(Spacer(1, 0.2 * inch))

    if figures:
        story.append(Paragraph("Visualizations", styles["Heading2"]))
        for fig_path in figures[:6]:
            if os.path.exists(fig_path):
                story.append(Image(fig_path, width=5.8 * inch, height=3.6 * inch))
                story.append(Spacer(1, 0.2 * inch))

    doc.build(story)
