from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fpdf import FPDF

from app.api.schemas import PdfMetricIn, PdfReportIn, PdfTableIn

FONTS_DIR = Path(__file__).resolve().parent / "fonts"
MAX_ROWS = 250
MAX_CELL = 400


def render_pdf(report: PdfReportIn) -> bytes:
    max_columns = max((len(table.headers) for table in report.tables), default=0)
    landscape = max_columns >= 7
    pdf = _ReportPdf(orientation="L" if landscape else "P", format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_font("DejaVu", fname=str(FONTS_DIR / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", style="B", fname=str(FONTS_DIR / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    pdf.set_text_color(15, 23, 42)

    pdf.set_font("DejaVu", style="B", size=18)
    pdf.multi_cell(0, 8, _text(report.title), new_x="LMARGIN", new_y="NEXT")
    if report.subtitle:
        pdf.set_font("DejaVu", size=10)
        pdf.set_text_color(100, 116, 139)
        pdf.multi_cell(0, 6, _text(report.subtitle), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(15, 23, 42)
    pdf.ln(3)

    if report.metrics:
        _draw_metrics(pdf, report.metrics)
        pdf.ln(4)

    for table in report.tables:
        _draw_table(pdf, table)
        pdf.ln(3)

    if report.notes:
        pdf.set_font("DejaVu", style="B", size=12)
        pdf.cell(0, 8, "Notes", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("DejaVu", size=10)
        for note in report.notes:
            pdf.multi_cell(0, 5, f"• {_text(note)}", new_x="LMARGIN", new_y="NEXT")

    pdf.set_title(_text(report.title)[:200])
    pdf.set_author("PR Manager")
    return bytes(pdf.output())


class _ReportPdf(FPDF):
    def header(self) -> None:
        self.set_font("DejaVu", size=8)
        self.set_text_color(100, 116, 139)
        generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        self.cell(0, 6, f"PR Manager  ·  {generated}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(226, 232, 240)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)
        self.set_x(self.l_margin)
        self.set_text_color(15, 23, 42)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("DejaVu", size=8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


def _text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    if len(text) > MAX_CELL:
        return f"{text[: MAX_CELL - 1]}…"
    return text


def _draw_metrics(pdf: FPDF, metrics: list[PdfMetricIn]) -> None:
    rows = [[_text(item.label), _text(item.value)] for item in metrics]
    pdf.set_font("DejaVu", style="B", size=12)
    pdf.cell(0, 8, "Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", size=9)
    with pdf.table(
        first_row_as_headings=True,
        col_widths=(70, 120),
        text_align=("LEFT", "LEFT"),
        line_height=6,
    ) as table:
        heading = table.row()
        heading.cell("Metric")
        heading.cell("Value")
        for label, value in rows:
            row = table.row()
            row.cell(label)
            row.cell(value)


def _draw_table(pdf: FPDF, table_in: PdfTableIn) -> None:
    headers = [_text(item) for item in table_in.headers] or ["Value"]
    rows = table_in.rows[:MAX_ROWS]
    if table_in.title:
        pdf.set_font("DejaVu", style="B", size=12)
        pdf.multi_cell(0, 8, _text(table_in.title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", size=8)
    column_count = max(len(headers), 1)
    with pdf.table(
        first_row_as_headings=True,
        text_align="LEFT",
        line_height=5.5,
        markdown=False,
    ) as table:
        heading = table.row()
        for header in headers:
            heading.cell(header)
        if not rows:
            empty = table.row()
            empty.cell("No rows")
            for _ in range(column_count - 1):
                empty.cell("")
            return
        for raw in rows:
            padded = list(raw) + [""] * max(0, column_count - len(raw))
            row = table.row()
            for index in range(column_count):
                row.cell(_text(padded[index]))
    if len(table_in.rows) > MAX_ROWS:
        pdf.set_font("DejaVu", size=8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 6, f"Showing first {MAX_ROWS} of {len(table_in.rows)} rows", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(15, 23, 42)
