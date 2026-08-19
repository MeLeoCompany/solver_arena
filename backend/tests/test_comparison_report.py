import io
import json
import time
import zipfile
from pathlib import Path

import pytest

from tests.conftest import EXAMPLES_DIR

MPS_FILE = EXAMPLES_DIR / "hour[0]_task[1].mps"
BATCH_WAIT_TIMEOUT_SEC = 60


def _solve(client, solver: str) -> dict:
    with open(MPS_FILE, "rb") as f:
        response = client.post(
            f"/solve/{solver}",
            files={"mps_file": ("m.mps", f, "text/plain")},
            data={"flags": json.dumps({"flags": {}})},
        )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture(scope="session")
def alglib_job(client):
    return _solve(client, "alglib")


@pytest.fixture(scope="session")
def cplex_job(client):
    return _solve(client, "cplex")


def _wait_for_batch(client, batch_id: str, timeout: float = BATCH_WAIT_TIMEOUT_SEC) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/batches/{batch_id}")
        assert response.status_code == 200
        data = response.json()
        if data["state"] != "running":
            return data
        time.sleep(0.5)
    raise AssertionError(f"batch {batch_id} did not finish within {timeout}s")


def _build_zip(entries: list[tuple[str, Path]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, path in entries:
            zf.writestr(name, path.read_bytes())
    return buf.getvalue()


def _submit_batch(client, solver: str, files: list[tuple[str, Path]]) -> dict:
    zip_bytes = _build_zip(files)
    response = client.post(
        "/batches",
        files={"zip_file": ("batch.zip", zip_bytes, "application/zip")},
        data={"solver": solver, "flags": json.dumps({"flags": {}})},
    )
    assert response.status_code == 200, response.text
    return _wait_for_batch(client, response.json()["batch_id"])


@pytest.fixture(scope="session")
def alglib_batch_a(client):
    return _submit_batch(client, "alglib", [("first.mps", MPS_FILE)])


@pytest.fixture(scope="session")
def alglib_batch_b(client):
    return _submit_batch(client, "alglib", [("first.mps", MPS_FILE)])


def test_compare_jobs_report_returns_pdf(client, alglib_job, cplex_job):
    response = client.post(
        "/compare/jobs/report",
        json={"reference_job_id": alglib_job["job_id"], "alt_job_ids": [cplex_job["job_id"]]},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 500


def test_compare_jobs_report_unknown_job_returns_404(client, alglib_job):
    response = client.post(
        "/compare/jobs/report",
        json={"reference_job_id": alglib_job["job_id"], "alt_job_ids": ["does-not-exist"]},
    )
    assert response.status_code == 404


def test_compare_batches_report_returns_pdf(client, alglib_batch_a, alglib_batch_b):
    response = client.post(
        "/compare/batches/report",
        json={"reference_batch_id": alglib_batch_a["batch_id"], "alt_batch_id": alglib_batch_b["batch_id"]},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 500


def test_compare_batches_report_unknown_batch_returns_404(client, alglib_batch_a):
    response = client.post(
        "/compare/batches/report",
        json={"reference_batch_id": alglib_batch_a["batch_id"], "alt_batch_id": "does-not-exist"},
    )
    assert response.status_code == 404
