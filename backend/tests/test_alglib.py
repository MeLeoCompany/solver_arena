import math

from tests.conftest import EXAMPLES_DIR

MPS_FILE = EXAMPLES_DIR / "hour[0]_task[1].mps"
EXPECTED_OBJECTIVE = -19517.094


def test_solve_alglib_returns_optimal(client):
    with open(MPS_FILE, "rb") as f:
        response = client.post(
            "/solve/alglib",
            files={"mps_file": ("m.mps", f, "text/plain")},
            data={"flags": '{"flags": {}}'},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["solver"] == "alglib"
    assert body["state"] == "done"
    assert body["solve_status"] == "optimal"
    assert math.isclose(body["objective"], EXPECTED_OBJECTIVE, rel_tol=1e-4)
    assert body["error"] is None

    job_id = body["job_id"]

    solution = client.get(f"/jobs/{job_id}/solution")
    assert solution.status_code == 200
    assert len(solution.json()["variables"]) == 164

    log = client.get(f"/jobs/{job_id}/log")
    assert log.status_code == 200
    # this file has 36 integer/binary variables — real branch-and-bound now
    # (minlpsolversetintkth), not the old relaxation-only path
    assert "integer/binary variables" in log.text
    assert "branch-and-bound" in log.text


def test_solve_alglib_accepts_algorithm_and_eps_flags(client):
    with open(MPS_FILE, "rb") as f:
        response = client.post(
            "/solve/alglib",
            files={"mps_file": ("m.mps", f, "text/plain")},
            data={"flags": '{"flags": {"algorithm": "ipm", "eps": "1e-8"}}'},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "done"
    assert math.isclose(body["objective"], EXPECTED_OBJECTIVE, rel_tol=1e-3)


def test_solve_alglib_rejects_garbage_mps(client):
    response = client.post(
        "/solve/alglib",
        files={"mps_file": ("bad.mps", b"this is not a valid mps file", "text/plain")},
        data={"flags": '{"flags": {}}'},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "failed"
