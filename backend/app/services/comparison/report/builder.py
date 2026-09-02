from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from app.services.comparison.report.styles import (
    BODY,
    COLOR_HEADER_BG,
    FORMULA,
    PAGE_MARGIN,
    SECTION_HEADING,
    TABLE_CELL,
    TABLE_ERROR_CELL,
    TABLE_HEADER_CELL,
)

TABLE_WIDTH = A4[0] - 2 * PAGE_MARGIN
MIN_COL_CHARS = 4
MAX_COL_CHARS_SAMPLE = 20


def format_num(value: float | None, digits: int = 6) -> str:
    """Mirrors frontend/src/utils/formatNumber.ts::formatNum exactly."""
    if value is None:
        return "—"
    if value == 0:
        return "0"
    if abs(value) < 1e-4:
        return f"{value:.3e}"
    text = f"{value:,.{digits}f}".rstrip("0").rstrip(".")
    return text if text not in ("", "-") else "0"


def section_heading(text: str) -> Paragraph:
    return Paragraph(text, SECTION_HEADING)


def metric_explainer(description: str, formula: str) -> list:
    formula_html = formula.replace("\n", "<br/>")
    return [
        Paragraph(description, BODY),
        Paragraph(formula_html, FORMULA),
        Spacer(1, 4),
    ]


def _column_widths(headers: list[str], rows: list[list[str]]) -> list[float]:
    """Without explicit colWidths, reportlab sizes each column to its widest
    cell and lets the table grow past the page margins — fine for the
    5-7 column job-comparison tables, but the 9-10 column batch-comparison
    tables (extra "#"/"Файл"/"Эталон"/"Альт" columns) run off the page.
    Weight each column by its longest cell text (capped so one long error
    message can't dominate — Paragraph wraps within its cell regardless)
    and scale to fill the fixed table width exactly.
    """
    weights = []
    for i, header in enumerate(headers):
        longest = len(header)
        for row in rows:
            if i < len(row):
                longest = max(longest, min(len(str(row[i])), MAX_COL_CHARS_SAMPLE))
        weights.append(max(longest, MIN_COL_CHARS))
    total = sum(weights)
    return [TABLE_WIDTH * w / total for w in weights]


def data_table(headers: list[str], rows: list[list[str]], error_row_flags: list[bool]) -> Table:
    """A plain grid table — header row + data rows, each already formatted as
    strings. error_row_flags marks which data rows should render in the
    error color (mirrors .compare-table__error on the frontend).
    """
    header_cells = [Paragraph(h, TABLE_HEADER_CELL) for h in headers]
    body_rows = []
    for row, is_error in zip(rows, error_row_flags):
        style = TABLE_ERROR_CELL if is_error else TABLE_CELL
        body_rows.append([Paragraph(str(cell), style) for cell in row])

    table = Table([header_cells, *body_rows], colWidths=_column_widths(headers, rows), repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3547")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7cdd8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_HEADER_BG]),
            ]
        )
    )
    return table
