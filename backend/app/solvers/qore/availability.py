import json
import subprocess
import tempfile
from pathlib import Path

from app.config import settings


def check() -> dict:
    """Runs inside a spawned subprocess like the other solvers, but that's
    not enough on its own here — qore_opt_py only loads under its own
    CPython 3.8 interpreter, so the actual import+license check has to
    happen in a further subprocess running that interpreter.
    """
    spec = {
        "license_file": str(settings.qore_license_file),
        "module_dir": str(settings.qore_engine_dir),
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(spec, f)
        spec_path = f.name

    try:
        result = subprocess.run(
            [str(settings.qore_python_executable), str(settings.qore_check_script), spec_path],
            capture_output=True,
            text=True,
            timeout=settings.availability_check_timeout_sec,
        )
    except FileNotFoundError:
        return {
            "available": False,
            "detail": f"QORE's Python 3.8 interpreter not found at {settings.qore_python_executable}",
        }
    except subprocess.TimeoutExpired:
        return {"available": False, "detail": "availability check timed out"}
    finally:
        Path(spec_path).unlink(missing_ok=True)

    if result.returncode != 0:
        output = (result.stderr.strip() or result.stdout.strip() or "unknown error").splitlines()
        return {"available": False, "detail": output[-1] if output else "unknown error"}

    return {"available": True, "detail": None}
