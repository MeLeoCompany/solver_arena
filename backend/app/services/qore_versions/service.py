import json
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.database import SessionLocal
from app.models.qore_version import QoreVersion

# Filename Python's import machinery expects for `import qore_opt_py` under
# this exact interpreter/platform — must match across every stored version.
QORE_MODULE_FILENAME = "qore_opt_py.cpython-38-x86_64-linux-gnu.so"
QORE_STUB_FILENAME = "qore_opt_py.pyi"


class QoreVersionError(ValueError):
    pass


class QoreVersionNotFoundError(QoreVersionError):
    pass


def _run_smoke_test(module_dir: Path) -> tuple[bool, str | None]:
    """Reuses the exact same check as app/solvers/qore/availability.py, just
    pointed at a candidate directory instead of the live engine dir.
    """
    spec = {
        "license_file": str(settings.qore_license_file),
        "module_dir": str(module_dir),
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
        return False, f"QORE's Python 3.8 interpreter not found at {settings.qore_python_executable}"
    except subprocess.TimeoutExpired:
        return False, "smoke test timed out"
    finally:
        Path(spec_path).unlink(missing_ok=True)

    if result.returncode != 0:
        output = (result.stderr.strip() or result.stdout.strip() or "unknown error")
        return False, output

    return True, None


def _regenerate_stub(module_dir: Path) -> tuple[bool, str | None]:
    spec = {"module_dir": str(module_dir), "output_dir": str(settings.qore_engine_dir)}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(spec, f)
        spec_path = f.name

    try:
        result = subprocess.run(
            [str(settings.qore_python_executable), str(settings.qore_stubgen_script), spec_path],
            capture_output=True,
            text=True,
            timeout=settings.availability_check_timeout_sec,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    finally:
        Path(spec_path).unlink(missing_ok=True)

    if result.returncode != 0:
        return False, (result.stderr.strip() or result.stdout.strip() or "unknown error")
    return True, None


def _ensure_bootstrapped(session) -> None:
    """First-ever use: if there's a live .so but no QoreVersion rows yet
    (the file predates this feature), register it as one so rollback/history
    stays uniform going forward instead of needing a special case.
    """
    if session.query(QoreVersion).count() > 0:
        return
    live_path = settings.qore_engine_dir / QORE_MODULE_FILENAME
    if not live_path.exists():
        return

    version_id = str(uuid.uuid4())
    version_dir = settings.qore_versions_dir / version_id
    version_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(live_path, version_dir / QORE_MODULE_FILENAME)

    row = QoreVersion(
        label="исходный файл (до системы версий)",
        so_path=str(version_dir / QORE_MODULE_FILENAME),
        active=True,
        smoke_test_ok=True,
        smoke_test_output=None,
        uploaded_by=None,
        uploaded_at=datetime.now(timezone.utc),
    )
    session.add(row)
    session.commit()


def list_versions() -> list[QoreVersion]:
    with SessionLocal() as session:
        _ensure_bootstrapped(session)
        return session.query(QoreVersion).order_by(QoreVersion.uploaded_at.desc()).all()


def upload_version(so_bytes: bytes, label: str, uploaded_by: str) -> QoreVersion:
    version_id = str(uuid.uuid4())
    version_dir = settings.qore_versions_dir / version_id
    version_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = version_dir / QORE_MODULE_FILENAME
    candidate_path.write_bytes(so_bytes)

    smoke_ok, smoke_output = _run_smoke_test(version_dir)

    with SessionLocal() as session:
        _ensure_bootstrapped(session)

        row = QoreVersion(
            label=label,
            so_path=str(candidate_path),
            active=False,
            smoke_test_ok=smoke_ok,
            smoke_test_output=smoke_output,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.now(timezone.utc),
        )
        session.add(row)
        session.commit()
        session.refresh(row)

        if smoke_ok:
            _activate(session, row, version_dir)
            session.commit()
            session.refresh(row)

        return row


def activate_version(version_id: int, activated_by: str) -> QoreVersion:
    with SessionLocal() as session:
        row = session.get(QoreVersion, version_id)
        if row is None:
            raise QoreVersionNotFoundError("version not found")

        version_dir = Path(row.so_path).parent
        # Re-verify — the environment may have changed since this version was
        # last live (e.g. license expired), don't trust a stale smoke test.
        smoke_ok, smoke_output = _run_smoke_test(version_dir)
        row.smoke_test_ok = smoke_ok
        row.smoke_test_output = smoke_output
        if not smoke_ok:
            session.commit()
            raise QoreVersionError(f"smoke test failed, not activating: {smoke_output}")

        _activate(session, row, version_dir)
        session.commit()
        session.refresh(row)
        return row


def _activate(session, row: QoreVersion, version_dir: Path) -> None:
    """Copies the candidate .so into the live path, regenerates the .pyi
    stub from it, and flips the active flag. Caller must have already
    confirmed the smoke test passed.
    """
    live_path = settings.qore_engine_dir / QORE_MODULE_FILENAME
    shutil.copy2(version_dir / QORE_MODULE_FILENAME, live_path)
    _regenerate_stub(settings.qore_engine_dir)

    session.query(QoreVersion).filter(QoreVersion.active.is_(True)).update({"active": False})
    row.active = True
