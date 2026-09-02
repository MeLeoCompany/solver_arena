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
CELL_H_PADDING = 10  # LEFTPADDING + RIGHTPADDING set on the TableStyle below


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
    cell and lets the table grow past the page margins — the 9-10 column
    batch-comparison tables run off the page. So columns need fixed
    colWidths that sum to TABLE_WIDTH. But reportlab's Paragraph only wraps
    at spaces — a column too narrow for a space-free "word" (a job-id hash,
    a formatted number, a percentage) gets hard character-split instead
    ("2503\n37da"), which reads as garbled. So: measure each column's real
    required width (actual glyph width, not a character-count guess), and
    only ever shrink columns below that when the content itself contains a
    space to wrap at — filenames, hashes and numbers (no spaces) always get
    their full natural width; "Статус"-style "optimal / optimal" text
    absorbs the compression instead.
    """
    natural_widths = []
    can_wrap = []
    for i, header in enumerate(headers):
        cells = [header] + [str(row[i]) for row in rows if i < len(row)]
        widest = max(stringWidth(c, TABLE_CELL.fontName, CELL_FONT_SIZE) for c in cells)
        natural_widths.append(widest + CELL_H_PADDING)
        can_wrap.append(any(" " in c for c in cells))

    total_natural = sum(natural_widths)
    flexible_total = sum(w for w, wrap in zip(natural_widths, can_wrap) if wrap)
    rigid_total = total_natural - flexible_total

    if total_natural <= TABLE_WIDTH:
        # Room to spare — hand it to the wrappable columns so they aren't
        # cramped; if every column is rigid, spread it evenly instead.
        extra = TABLE_WIDTH - total_natural
        if flexible_total > 0:
            return [
                w + (extra * w / flexible_total if wrap else 0)
                for w, wrap in zip(natural_widths, can_wrap)
            ]
        return [w + extra / len(natural_widths) for w in natural_widths]

    available_for_flexible = TABLE_WIDTH - rigid_total
    if available_for_flexible > 0 and flexible_total > 0:
        scale = available_for_flexible / flexible_total
        return [w * scale if wrap else w for w, wrap in zip(natural_widths, can_wrap)]

    # Even the rigid columns alone don't fit the page — genuinely too much
    # content (e.g. an unusually long error message); scale everything down
    # equally as a last resort rather than overflowing the page.
    scale = TABLE_WIDTH / total_natural
    return [w * scale for w in natural_widths]


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
