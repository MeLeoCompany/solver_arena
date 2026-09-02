from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
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
CELL_FONT_SIZE = 8  # matches TABLE_CELL/TABLE_HEADER_CELL/TABLE_ERROR_CELL fontSize
CELL_LEADING_RATIO = TABLE_CELL.leading / TABLE_CELL.fontSize
CELL_H_PADDING = 10  # LEFTPADDING + RIGHTPADDING set on the TableStyle below
MIN_CELL_FONT_SIZE = 6.5  # below this, prefer the last-resort width squeeze over illegible text


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


def _fit_table(headers: list[str], rows: list[list[str]]) -> tuple[list[float], float]:
    """Sizes columns to fill TABLE_WIDTH exactly, without ever forcing a
    mid-word character split. Returns (col_widths, font_size).

    reportlab's Paragraph only wraps at spaces — it force-splits a single
    "word" (space-free run of characters) mid-character if the column is
    narrower than that word, which reads as garbled ("2503\n37da",
    "Obj (эт\nалон)"). A column is *not* safe from this just because its
    header or some cell contains a space somewhere (an earlier version of
    this function got that wrong) — every individual word in every cell of
    that column needs to fit, including e.g. "(эталон)" inside a two-word
    header. So: floor[i] is the width of the single longest word across
    every cell in column i at CELL_FONT_SIZE (guarantees zero forced
    mid-word splits), desired[i] is the width of the longest whole cell
    (zero wrapping at all). Every column gets at least its floor; slack is
    handed out proportional to remaining demand (desired - floor).

    A 9-10 column table with many rows can have a "#" column whose floor
    (e.g. two-digit indices) alone, summed with the other columns' floors,
    slightly exceeds TABLE_WIDTH even though no single column is
    unreasonable — measured empirically against a realistic 40-row batch.
    Word widths scale linearly with font size, so in that case shrink the
    font just enough for the floors to fit (bounded by MIN_CELL_FONT_SIZE)
    rather than letting any column dip below its word floor.
    """
    font = TABLE_CELL.fontName
    n = len(headers)

    def word_width_units(text: str) -> float:
        words = text.split(" ") or [text]
        return max(stringWidth(w, font, 1.0) for w in words)

    def full_width_units(text: str) -> float:
        return stringWidth(text, font, 1.0)

    floor_units = []
    desired_units = []
    for i in range(n):
        cells = [headers[i]] + [str(row[i]) for row in rows if i < len(row)]
        floor_units.append(max(word_width_units(c) for c in cells))
        desired_units.append(max(full_width_units(c) for c in cells))

    text_budget = TABLE_WIDTH - n * CELL_H_PADDING
    total_floor_units = sum(floor_units)
    font_size = CELL_FONT_SIZE
    if total_floor_units * font_size > text_budget:
        font_size = max(text_budget / total_floor_units, MIN_CELL_FONT_SIZE)

    floors = [u * font_size + CELL_H_PADDING for u in floor_units]
    desired = [u * font_size + CELL_H_PADDING for u in desired_units]

    total_floor = sum(floors)
    if total_floor > TABLE_WIDTH:
        # Font size floored at MIN_CELL_FONT_SIZE and it still doesn't fit —
        # genuinely too much content (e.g. an unusually long error message
        # or an enormous batch). Scale widths down as an absolute last
        # resort; only this pathological case can still wrap mid-word.
        scale = TABLE_WIDTH / total_floor
        return [w * scale for w in floors], font_size

    slack = TABLE_WIDTH - total_floor
    demand = [max(d - f, 0) for d, f in zip(desired, floors)]
    total_demand = sum(demand)
    widths = (
        [f + slack * d / total_demand for f, d in zip(floors, demand)]
        if total_demand > 0
        else [f + slack / n for f in floors]
    )
    return widths, font_size


def data_table(headers: list[str], rows: list[list[str]], error_row_flags: list[bool]) -> Table:
    """A plain grid table — header row + data rows, each already formatted as
    strings. error_row_flags marks which data rows should render in the
    error color (mirrors .compare-table__error on the frontend).
    """
    col_widths, font_size = _fit_table(headers, rows)
    if font_size == CELL_FONT_SIZE:
        header_style, cell_style, error_style = TABLE_HEADER_CELL, TABLE_CELL, TABLE_ERROR_CELL
    else:
        leading = font_size * CELL_LEADING_RATIO
        header_style = TABLE_HEADER_CELL.clone("TableHeaderCellFit", fontSize=font_size, leading=leading)
        cell_style = TABLE_CELL.clone("TableCellFit", fontSize=font_size, leading=leading)
        error_style = TABLE_ERROR_CELL.clone("TableErrorCellFit", fontSize=font_size, leading=leading)

    header_cells = [Paragraph(h, header_style) for h in headers]
    body_rows = []
    for row, is_error in zip(rows, error_row_flags):
        style = error_style if is_error else cell_style
        body_rows.append([Paragraph(str(cell), style) for cell in row])

    table = Table([header_cells, *body_rows], colWidths=col_widths, repeatRows=1)
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
