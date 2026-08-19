import math

import pytest

from app.config import settings
from tests.conftest import EXAMPLES_DIR

MPS_FILE = EXAMPLES_DIR / "hour[0]_task[1].mps"
EXPECTED_OBJECTIVE = -19517.094
EXPECTED_VAR_COUNT = 164


@pytest.fixture(scope="session")
def solved_job(client):
    with open(MPS_FILE, "rb") as f:
        response = client.post(
            "/solve/cuopt",
            files={"mps_file": ("m.mps", f, "text/plain")},
            data={"flags": '{"flags": {"time-limit": 5}}'},
        )
    assert response.status_code == 200
    return response.json()


def test_solve_returns_optimal(solved_job):
    assert solved_job["state"] == "done"
    assert solved_job["solve_status"] == "optimal"
    assert math.isclose(solved_job["objective"], EXPECTED_OBJECTIVE, rel_tol=1e-6)
    assert solved_job["error"] is None


def test_solve_response_has_solution_and_log_links(solved_job):
    job_id = solved_job["job_id"]
    assert solved_job["solution_url"] == f"/jobs/{job_id}/solution"
    assert solved_job["log_url"] == f"/jobs/{job_id}/log"


def test_get_job_matches_solve_response(client, solved_job):
    job_id = solved_job["job_id"]
    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "done"
    assert data["solve_status"] == "optimal"
    assert math.isclose(data["objective"], EXPECTED_OBJECTIVE, rel_tol=1e-6)


def test_get_solution_returns_vector(client, solved_job):
    job_id = solved_job["job_id"]
    response = client.get(f"/jobs/{job_id}/solution")
    assert response.status_code == 200
    variables = response.json()["variables"]
    assert len(variables) == EXPECTED_VAR_COUNT
    assert math.isclose(variables[0], 9.539, rel_tol=1e-3)


def test_get_log_returns_full_text(client, solved_job):
    job_id = solved_job["job_id"]
    response = client.get(f"/jobs/{job_id}/log")
    assert response.status_code == 200
    assert "Optimal" in response.text


def test_solution_and_log_files_live_in_separate_dirs(solved_job):
    job_id = solved_job["job_id"]
    assert (settings.results_dir / f"{job_id}.npy").exists()
    assert (settings.logs_dir / f"{job_id}.log").exists()
    assert not (settings.results_dir / f"{job_id}.log").exists()
    assert not (settings.logs_dir / f"{job_id}.npy").exists()


def test_unknown_job_returns_404(client):
    assert client.get("/jobs/does-not-exist").status_code == 404
    assert client.get("/jobs/does-not-exist/solution").status_code == 404
    assert client.get("/jobs/does-not-exist/log").status_code == 404
