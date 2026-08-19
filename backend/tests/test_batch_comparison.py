import io
import json
import math
import time
import zipfile
from pathlib import Path

import pytest

from tests.conftest import EXAMPLES_DIR

MPS_FILE = EXAMPLES_DIR / "hour[0]_task[1].mps"
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


def _submit_batch(client, solver: str, files: list[tuple[str, Path]]) -> dict:
    zip_bytes = _build_zip(files)
    response = client.post(
        "/batches",
        files={"zip_file": ("batch.zip", zip_bytes, "application/zip")},
        data={"solver": solver, "flags": json.dumps({"flags": {"time-limit": 5} if solver == "cuopt" else {}})},
    )
    assert response.status_code == 200, response.text
    return _wait_for_batch(client, response.json()["batch_id"])


@pytest.fixture(scope="session")
def cuopt_batch(client):
    return _submit_batch(client, "cuopt", [("first.mps", MPS_FILE), ("second.mps", MPS_FILE)])


@pytest.fixture(scope="session")
def alglib_batch(client):
    return _submit_batch(client, "alglib", [("first.mps", MPS_FILE), ("second.mps", MPS_FILE)])


@pytest.fixture(scope="session")
def short_alglib_batch(client):
    """Only one file — used to test batches of mismatched length."""
    return _submit_batch(client, "alglib", [("first.mps", MPS_FILE)])


def test_compare_batches_aligns_by_index(client, cuopt_batch, alglib_batch):
    response = client.post(
        "/compare/batches",
        json={"reference_batch_id": cuopt_batch["batch_id"], "alt_batch_id": alglib_batch["batch_id"]},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["reference_batch_id"] == cuopt_batch["batch_id"]
    assert data["alt_batch_id"] == alglib_batch["batch_id"]

    ref_job_id_by_index = {job["batch_index"]: job["job_id"] for job in cuopt_batch["jobs"]}

    objective_rows = data["objective"]
    assert [row["batch_index"] for row in objective_rows] == [1, 2]
    assert [row["reference_filename"] for row in objective_rows] == ["first.mps", "second.mps"]
    assert [row["alt_filename"] for row in objective_rows] == ["first.mps", "second.mps"]
    for row in objective_rows:
        assert row["error"] is None
        assert row["reference_job_id"] == ref_job_id_by_index[row["batch_index"]]
        assert math.isclose(row["reference_objective"], EXPECTED_OBJECTIVE, rel_tol=1e-6)
        # both solvers land on essentially the same objective for this file
        assert abs(row["delta_abs"]) < 1e-3

    violation_rows = data["violations"]
    assert len(violation_rows) == 4  # 2 indices x (reference + alt)
    assert {row["batch_index"] for row in violation_rows} == {1, 2}
    for row in violation_rows:
        assert row["error"] is None
        assert row["filename"] == "first.mps" or row["filename"] == "second.mps"

    diff_rows = data["solution_diff"]
    assert [row["batch_index"] for row in diff_rows] == [1, 2]
    for row in diff_rows:
        assert row["error"] is None
        assert row["reference_job_id"] == ref_job_id_by_index[row["batch_index"]]


def test_compare_batches_mismatched_length_reports_error_without_crashing(client, cuopt_batch, short_alglib_batch):
    response = client.post(
        "/compare/batches",
        json={"reference_batch_id": cuopt_batch["batch_id"], "alt_batch_id": short_alglib_batch["batch_id"]},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    objective_rows = sorted(data["objective"], key=lambda r: r["batch_index"])
    assert [row["batch_index"] for row in objective_rows] == [1, 2]
    assert objective_rows[0]["error"] is None
    assert objective_rows[1]["error"] is not None
    assert objective_rows[1]["alt_filename"] is None
    assert objective_rows[1]["reference_filename"] == "second.mps"


def test_compare_batches_unknown_reference_returns_404(client, alglib_batch):
    response = client.post(
        "/compare/batches",
        json={"reference_batch_id": "does-not-exist", "alt_batch_id": alglib_batch["batch_id"]},
    )
    assert response.status_code == 404


def test_compare_batches_unknown_alt_returns_404(client, cuopt_batch):
    response = client.post(
        "/compare/batches",
        json={"reference_batch_id": cuopt_batch["batch_id"], "alt_batch_id": "does-not-exist"},
    )
    assert response.status_code == 404
