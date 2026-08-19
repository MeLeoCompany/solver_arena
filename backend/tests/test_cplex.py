import math

from tests.conftest import EXAMPLES_DIR

MPS_FILE = EXAMPLES_DIR / "hour[0]_task[1].mps"
EXPECTED_OBJECTIVE = -19517.094


def test_solve_cplex_returns_optimal(client):
    with open(MPS_FILE, "rb") as f:
        response = client.post(
            "/solve/cplex",
            files={"mps_file": ("m.mps", f, "text/plain")},
            data={"flags": '{"flags": {}}'},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["solver"] == "cplex"
    assert body["state"] == "done"
    assert body["solve_status"] == "optimal"
    assert math.isclose(body["objective"], EXPECTED_OBJECTIVE, rel_tol=1e-4)
    assert body["error"] is None

    job_id = body["job_id"]

    solution = client.get(f"/jobs/{job_id}/solution")
    assert solution.status_code == 200
    variables = solution.json()["variables"]
    assert len(variables) == 164

    log = client.get(f"/jobs/{job_id}/log")
    assert log.status_code == 200
    assert len(log.text) > 0


def test_solve_cplex_accepts_a_parameter(client):
    with open(MPS_FILE, "rb") as f:
        response = client.post(
            "/solve/cplex",
            files={"mps_file": ("m.mps", f, "text/plain")},
            data={"flags": '{"flags": {"CPX_PARAM_TILIM": 30}}'},
        )
    assert response.status_code == 200
    assert response.json()["state"] == "done"
