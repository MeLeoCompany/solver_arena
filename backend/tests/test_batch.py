import asyncio
import io
import json
import math
import time
import zipfile
from pathlib import Path

import httpx2
import pytest
from httpx2 import ASGITransport

from app.config import settings
from tests.conftest import EXAMPLES_DIR, TEST_PASSWORD, TEST_USERNAME

MPS_FILE = EXAMPLES_DIR / "hour[0]_task[1].mps"
LONG_MPS_FILE = EXAMPLES_DIR / "qp_dv_iter_11.mps"
EXPECTED_OBJECTIVE = -19517.094

BATCH_WAIT_TIMEOUT_SEC = 60


def _build_zip(entries: list[tuple[str, Path]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, path in entries:
            zf.writestr(name, path.read_bytes())
    return buf.getvalue()


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


async def _wait_for_batch_async(async_client, batch_id: str, timeout: float = BATCH_WAIT_TIMEOUT_SEC) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = await async_client.get(f"/batches/{batch_id}")
        assert response.status_code == 200
        data = response.json()
        if data["state"] != "running":
            return data
        await asyncio.sleep(0.5)
    raise AssertionError(f"batch {batch_id} did not finish within {timeout}s")


@pytest.fixture(scope="session")
def solved_batch(client):
    zip_bytes = _build_zip([("first.mps", MPS_FILE), ("second.mps", MPS_FILE)])
    response = client.post(
        "/batches",
        files={"zip_file": ("batch.zip", zip_bytes, "application/zip")},
        data={"solver": "cuopt", "flags": json.dumps({"flags": {"time-limit": 5}})},
    )
    assert response.status_code == 200, response.text
    return _wait_for_batch(client, response.json()["batch_id"])


def test_batch_returns_running_immediately_with_no_children_yet(client):
    zip_bytes = _build_zip([("only.mps", MPS_FILE)])
    response = client.post(
        "/batches",
        files={"zip_file": ("batch.zip", zip_bytes, "application/zip")},
        data={"solver": "cuopt", "flags": json.dumps({"flags": {"time-limit": 5}})},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "running"
    assert data["total"] == 1
    assert data["completed"] == 0
    assert data["jobs"] == []

    _wait_for_batch(client, data["batch_id"])  # drain so it doesn't linger into later tests


def test_batch_solves_all_files_and_reports_done(solved_batch):
    assert solved_batch["state"] == "done"
    assert solved_batch["total"] == 2
    assert solved_batch["completed"] == 2
    assert len(solved_batch["jobs"]) == 2


def test_batch_child_jobs_have_correct_metadata(solved_batch):
    jobs = sorted(solved_batch["jobs"], key=lambda j: j["batch_index"])
    assert [j["batch_index"] for j in jobs] == [1, 2]
    assert [j["original_filename"] for j in jobs] == ["first.mps", "second.mps"]
    assert jobs[0]["job_id"] != jobs[1]["job_id"]
    for job in jobs:
        assert job["batch_id"] == solved_batch["batch_id"]
        assert job["state"] == "done"
        assert job["solve_status"] == "optimal"
        assert math.isclose(job["objective"], EXPECTED_OBJECTIVE, rel_tol=1e-6)


def test_batch_children_excluded_from_top_level_job_list(client, solved_batch):
    response = client.get("/jobs")
    assert response.status_code == 200
    top_level_ids = {job["job_id"] for job in response.json()}
    for job in solved_batch["jobs"]:
        assert job["job_id"] not in top_level_ids


def test_batch_child_job_individually_fetchable(client, solved_batch):
    job = solved_batch["jobs"][0]
    response = client.get(f"/jobs/{job['job_id']}")
    assert response.status_code == 200
    assert response.json()["state"] == "done"


def test_batch_appears_in_batch_list(client, solved_batch):
    response = client.get("/batches")
    assert response.status_code == 200
    ids = {batch["batch_id"] for batch in response.json()}
    assert solved_batch["batch_id"] in ids


def test_unknown_batch_returns_404(client):
    assert client.get("/batches/does-not-exist").status_code == 404


def test_cancel_unknown_batch_returns_404(client):
    assert client.post("/batches/does-not-exist/cancel").status_code == 404


def test_batch_rejects_unknown_solver(client):
    zip_bytes = _build_zip([("only.mps", MPS_FILE)])
    response = client.post(
        "/batches",
        files={"zip_file": ("batch.zip", zip_bytes, "application/zip")},
        data={"solver": "does-not-exist", "flags": "{}"},
    )
    assert response.status_code == 400


def test_batch_rejects_non_zip_upload(client):
    response = client.post(
        "/batches",
        files={"zip_file": ("not-a-zip.mps", MPS_FILE.read_bytes(), "text/plain")},
        data={"solver": "cuopt", "flags": "{}"},
    )
    assert response.status_code == 400


def test_batch_rejects_zip_with_no_mps_files(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", "hello")
    response = client.post(
        "/batches",
        files={"zip_file": ("batch.zip", buf.getvalue(), "application/zip")},
        data={"solver": "cuopt", "flags": "{}"},
    )
    assert response.status_code == 400


def test_batch_rejects_duplicate_filenames_in_zip(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a/dup.mps", MPS_FILE.read_bytes())
        zf.writestr("b/dup.mps", MPS_FILE.read_bytes())
    response = client.post(
        "/batches",
        files={"zip_file": ("batch.zip", buf.getvalue(), "application/zip")},
        data={"solver": "cuopt", "flags": "{}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cancel_stops_batch_after_current_job(fastapi_app, client):
    """Cancelling mid-batch should stop the currently running job promptly
    (not let it run to its time limit) and never start the next file.
    """
    zip_bytes = _build_zip(
        [("first.mps", LONG_MPS_FILE), ("second.mps", LONG_MPS_FILE), ("third.mps", LONG_MPS_FILE)]
    )
    transport = ASGITransport(app=fastapi_app)
    async with httpx2.AsyncClient(transport=transport, base_url="http://test", timeout=120) as async_client:
        login = await async_client.post(
            "/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        assert login.status_code == 200

        t0 = time.monotonic()
        response = await async_client.post(
            "/batches",
            files={"zip_file": ("batch.zip", zip_bytes, "application/zip")},
            data={"solver": "cuopt", "flags": json.dumps({"flags": {"time-limit": 30}})},
        )
        assert response.status_code == 200
        batch_id = response.json()["batch_id"]

        upload_deadline = time.monotonic() + 20
        job_id = None
        while time.monotonic() < upload_deadline:
            await asyncio.sleep(0.2)
            uploads = sorted(settings.uploads_dir.glob("*.mps"), key=lambda p: p.stat().st_mtime)
            if uploads:
                job_id = uploads[-1].stem
                break
        assert job_id is not None, "batch never started uploading its first job"

        await asyncio.sleep(1.0)
        cancel_response = await async_client.post(f"/batches/{batch_id}/cancel")
        assert cancel_response.status_code == 200
        assert cancel_response.json() == {"batch_id": batch_id, "cancelling": True}

        data = await _wait_for_batch_async(async_client, batch_id)
        elapsed = time.monotonic() - t0

    assert elapsed < 30, "batch outlived the per-job time limit — cancel did not stop the running job"
    assert data["state"] == "cancelled"
    assert data["completed"] < data["total"]
    assert len(data["jobs"]) < data["total"]
