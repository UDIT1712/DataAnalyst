import io
import os
import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


REPORTS_DIR = Path(os.getenv("REPORTS_DIR", "./reports"))


class ReportGenerator:
    @staticmethod
    def generate_pdf(
        title: str,
        narrative: str,
        dataframes: dict[str, pd.DataFrame],
        charts_json: list[dict],
        thread_id: str,
    ) -> str:
        REPORTS_DIR.mkdir(exist_ok=True)
        filename = f"report_{thread_id}_{int(time.time())}.pdf"
        filepath = REPORTS_DIR / filename

        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "Title", parent=styles["Title"], fontSize=18, textColor=colors.HexColor("#1a1a2e")
        )
        body_style = styles["BodyText"]
        body_style.fontSize = 10

        story = []
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.5 * cm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#4a90d9")))
        story.append(Spacer(1, 0.5 * cm))

        for para in narrative.split("\n\n"):
            if para.strip():
                story.append(Paragraph(para.strip(), body_style))
                story.append(Spacer(1, 0.3 * cm))

        # Charts as images
        for i, chart_json in enumerate(charts_json[:6]):
            try:
                fig = go.Figure(chart_json)
                img_bytes = fig.to_image(format="png", width=700, height=400, scale=1.5)
                img_buf = io.BytesIO(img_bytes)
                img = Image(img_buf, width=16 * cm, height=9 * cm)
                story.append(Spacer(1, 0.5 * cm))
                story.append(img)
                story.append(Spacer(1, 0.3 * cm))
            except Exception:
                pass

        # Data tables
        for name, df in dataframes.items():
            story.append(Paragraph(f"Data: {name}", styles["Heading2"]))
            story.append(Spacer(1, 0.2 * cm))
            preview = df.head(20)
            table_data = [preview.columns.tolist()] + preview.values.tolist()
            t = Table(
                [[str(cell) for cell in row] for row in table_data],
                repeatRows=1,
            )
            t.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4a90d9")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4ff")]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ])
            )
            story.append(t)
            story.append(Spacer(1, 0.5 * cm))

        doc.build(story)
        return filename

    @staticmethod
    def generate_excel(
        dataframes: dict[str, pd.DataFrame],
        charts_json: list[dict],
        thread_id: str,
    ) -> str:
        REPORTS_DIR.mkdir(exist_ok=True)
        filename = f"report_{thread_id}_{int(time.time())}.xlsx"
        filepath = REPORTS_DIR / filename

        with pd.ExcelWriter(str(filepath), engine="openpyxl") as writer:
            for name, df in dataframes.items():
                sheet_name = name[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                ws = writer.sheets[sheet_name]
                for col_cells in ws.columns:
                    max_len = max(len(str(cell.value or "")) for cell in col_cells)
                    ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 2, 50)

        return filename
