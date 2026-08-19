from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONTS_DIR = Path(__file__).resolve().parent / "fonts"

FONT_REGULAR = "DejaVu"
FONT_MONO = "DejaVuMono"

_registered = False


def register_fonts() -> None:
    """Registers the vendored DejaVu fonts with reportlab. Base-14 PDF fonts
    (Helvetica etc.) have no Cyrillic glyphs at all, so this is required for
    any Russian text to render — not just for the Greek/math symbols in the
    metric formulas.
    """
    global _registered
    if _registered:
        return
    pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(FONTS_DIR / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_MONO, str(FONTS_DIR / "DejaVuSansMono.ttf")))
    _registered = True
