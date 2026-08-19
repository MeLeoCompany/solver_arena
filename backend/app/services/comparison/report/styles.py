from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm

from app.services.comparison.report.fonts import FONT_MONO, FONT_REGULAR, register_fonts

register_fonts()

PAGE_MARGIN = 15 * mm

COLOR_MUTED = colors.HexColor("#5a6472")
COLOR_HEADER_BG = colors.HexColor("#eef1f6")
COLOR_ERROR = colors.HexColor("#c23b4a")
COLOR_OK = colors.HexColor("#1f8a53")
COLOR_WARNING = colors.HexColor("#a3720f")

TITLE = ParagraphStyle("Title", fontName=FONT_REGULAR, fontSize=18, leading=22, spaceAfter=10)

SECTION_HEADING = ParagraphStyle(
    "SectionHeading", fontName=FONT_REGULAR, fontSize=13, leading=16, spaceBefore=14, spaceAfter=6
)

INTRO = ParagraphStyle(
    "Intro", fontName=FONT_REGULAR, fontSize=9.5, leading=13, textColor=COLOR_MUTED, spaceAfter=10
)

BODY = ParagraphStyle("Body", fontName=FONT_REGULAR, fontSize=9, leading=13, spaceAfter=4)

FORMULA = ParagraphStyle(
    "Formula",
    fontName=FONT_MONO,
    fontSize=8.5,
    leading=12,
    textColor=colors.HexColor("#1a1f29"),
    backColor=colors.HexColor("#f4f6fa"),
    borderPadding=6,
    spaceAfter=10,
)

TABLE_CELL = ParagraphStyle("TableCell", fontName=FONT_REGULAR, fontSize=8, leading=10)

TABLE_HEADER_CELL = ParagraphStyle(
    "TableHeaderCell", fontName=FONT_REGULAR, fontSize=8, leading=10, textColor=colors.white
)

TABLE_ERROR_CELL = ParagraphStyle(
    "TableErrorCell", fontName=FONT_REGULAR, fontSize=8, leading=10, textColor=COLOR_ERROR
)

WARNING_NOTE = ParagraphStyle(
    "WarningNote", fontName=FONT_REGULAR, fontSize=8, leading=11, textColor=COLOR_WARNING, spaceAfter=3
)

SUMMARY_NOTE = ParagraphStyle(
    "SummaryNote", fontName=FONT_REGULAR, fontSize=9, leading=12, textColor=COLOR_MUTED, spaceAfter=8
)
