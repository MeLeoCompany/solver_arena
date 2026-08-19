import sys

from app.config import settings


def import_xalglib():
    """xalglib.py + its native .so/.dll are vendored under engines/alglib/
    (no working pip package — see registry.py's comment), not installed
    into site-packages. Point sys.path at it before importing.
    """
    path = str(settings.alglib_engine_dir)
    if path not in sys.path:
        sys.path.insert(0, path)
    import xalglib

    return xalglib
