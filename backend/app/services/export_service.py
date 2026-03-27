"""
Export service: CSV and PDF report generation.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from loguru import logger

from ..models.schemas import GradingResult


GRADE_COLORS = {
    "A": colors.HexColor("#22D47C"),
    "B": colors.HexColor("#4FC3F7"),
    "C": colors.HexColor("#FFB347"),
    "D": colors.HexColor("#FF7043"),
    "F": colors.HexColor("#FF5C7C"),
}

PRIMARY_COLOR = colors.HexColor("#6C63FF")
HEADER_BG = colors.HexColor("#1E2038")
ROW_ALT = colors.HexColor("#F8F8FF")


class ExportService:
    """Generates CSV and PDF exports from grading results."""

    # ──────────────────────────────────────────────────────────────────────
    # CSV
    # ──────────────────────────────────────────────────────────────────────

    def to_csv_bytes(self, results: list[GradingResult], exam_title: str) -> bytes:
        """Generate a CSV file from a list of GradingResult objects."""
        if not results:
            return b""

        output = io.StringIO()

        # Build question column headers from first result
        q_keys = self._sorted_q_keys(results[0].question_scores)

        headers = (
            ["Roll No", "Student Name", "Grade"]
            + [f"Q{results[0].question_scores[k].question_number}" for k in q_keys]
            + ["Total Obtained", "Total Marks", "Percentage"]
        )

        writer = csv.writer(output, lineterminator="\n")

        # Metadata header rows
        writer.writerow([f"Exam: {exam_title}"])
        writer.writerow([f"Date: {datetime.now().strftime('%d %b %Y %H:%M')}"])
        writer.writerow([f"Students: {len(results)}"])
        avg = sum(r.percentage for r in results) / len(results) if results else 0
        writer.writerow([f"Class Average: {avg:.1f}%"])
        writer.writerow([])  # blank separator

        writer.writerow(headers)

        for r in sorted(results, key=lambda x: x.percentage, reverse=True):
            row = [r.roll_number, r.student_name, r.grade]
            for k in q_keys:
                score = r.question_scores.get(k)
                row.append(score.display if score else "N/A")
            row += [r.total_marks_obtained, r.total_marks_available, f"{r.percentage:.1f}%"]
            writer.writerow(row)

        return output.getvalue().encode("utf-8-sig")  # BOM for Excel compatibility

    # ──────────────────────────────────────────────────────────────────────
    # PDF
    # ──────────────────────────────────────────────────────────────────────

    def to_pdf_bytes(self, results: list[GradingResult], exam_title: str) -> bytes:
        """Generate a styled PDF report."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            textColor=PRIMARY_COLOR,
            fontSize=22,
            spaceAfter=4,
        )
        meta_style = ParagraphStyle(
            "Meta",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#555555"),
            spaceAfter=6,
        )
        section_style = ParagraphStyle(
            "Section",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=colors.HexColor("#333333"),
            spaceBefore=12,
            spaceAfter=6,
        )

        story = []
        date_str = datetime.now().strftime("%d %B %Y")
        avg = sum(r.percentage for r in results) / len(results) if results else 0
        pass_count = sum(1 for r in results if r.percentage >= 50)

        # ── Title block
        story.append(Paragraph(exam_title, title_style))
        story.append(Paragraph(f"Results Report · {date_str}", meta_style))
        story.append(HRFlowable(width="100%", color=PRIMARY_COLOR, thickness=1.5))
        story.append(Spacer(1, 10))

        # ── Summary stats table
        summary_data = [
            ["Total Students", "Class Average", "Pass Rate", "Highest Score", "Lowest Score"],
            [
                str(len(results)),
                f"{avg:.1f}%",
                f"{pass_count}/{len(results)} ({pass_count / len(results) * 100:.0f}%)" if results else "--",
                f"{max(r.percentage for r in results):.1f}%" if results else "--",
                f"{min(r.percentage for r in results):.1f}%" if results else "--",
            ],
        ]
        summary_table = Table(summary_data, colWidths=[3.5 * cm] * 5)
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWHEIGHT", (0, 0), (-1, -1), 20),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 16))

        # ── Results leaderboard table
        story.append(Paragraph("Student Results", section_style))

        sorted_results = sorted(results, key=lambda r: r.percentage, reverse=True)
        q_keys = self._sorted_q_keys(results[0].question_scores) if results else []

        # Build header
        headers = ["#", "Roll No", "Name"] + [
            f"Q{results[0].question_scores[k].question_number}" for k in q_keys
        ] + ["Score", "Total", "%", "Grade"]

        col_widths = [0.7 * cm, 2.2 * cm, 4.0 * cm]
        col_widths += [1.2 * cm] * len(q_keys)
        col_widths += [1.4 * cm, 1.4 * cm, 1.4 * cm, 1.2 * cm]

        table_data = [headers]
        for i, r in enumerate(sorted_results):
            grade_color_name = r.grade
            row = [str(i + 1), r.roll_number, r.student_name]
            for k in q_keys:
                score = r.question_scores.get(k)
                row.append(score.display if score else "--")
            row += [
                str(r.total_marks_obtained),
                str(r.total_marks_available),
                f"{r.percentage:.1f}%",
                r.grade,
            ]
            table_data.append(row)

        results_table = Table(table_data, colWidths=col_widths, repeatRows=1)

        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWHEIGHT", (0, 0), (-1, -1), 18),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
        ]

        # Alternate row colors + grade column coloring
        for i, r in enumerate(sorted_results):
            row_idx = i + 1
            if i % 2 == 0:
                style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), ROW_ALT))
            grad_col = GRADE_COLORS.get(r.grade, colors.grey)
            style_cmds.append(("TEXTCOLOR", (-1, row_idx), (-1, row_idx), grad_col))
            style_cmds.append(("FONTNAME", (-1, row_idx), (-1, row_idx), "Helvetica-Bold"))

        results_table.setStyle(TableStyle(style_cmds))
        story.append(results_table)

        # ── Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.read()

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _sorted_q_keys(question_scores: dict) -> list[str]:
        return sorted(
            question_scores.keys(),
            key=lambda k: int(k.replace("q", "")) if k.replace("q", "").isdigit() else 0,
        )
