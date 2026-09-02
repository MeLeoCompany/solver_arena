import json
import math

import pytest

from tests.conftest import EXAMPLES_DIR

MPS_FILE = EXAMPLES_DIR / "hour[0]_task[1].mps"
QP_MPS_FILE = EXAMPLES_DIR / "qp_dv_iter_11.mps"


@pytest.fixture(scope="session")
def cuopt_job(client):
    with open(MPS_FILE, "rb") as f:
        response = client.post(
            "/solve/cuopt",
            files={"mps_file": ("m.mps", f, "text/plain")},
            data={"flags": json.dumps({"flags": {"time-limit": 5}})},
        )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture(scope="session")
def alglib_job(client):
    with open(MPS_FILE, "rb") as f:
        response = client.post(
            "/solve/alglib",
            files={"mps_file": ("m.mps", f, "text/plain")},
            data={"flags": json.dumps({"flags": {}})},
        )
    assert response.status_code == 200, response.text
    return response.json()


def test_compare_self_shows_no_delta_and_no_diffs(client, cuopt_job):
    job_id = cuopt_job["job_id"]
    response = client.post("/compare/jobs", json={"reference_job_id": job_id, "alt_job_ids": [job_id]})
    assert response.status_code == 200, response.text
    data = response.json()

    obj_row = data["objective"][0]
    assert obj_row["delta_abs"] == 0.0
    assert obj_row["delta_rel_pct"] == 0.0

    diff_row = data["solution_diff"][0]
    assert diff_row["num_diffs"] == 0
    assert diff_row["max_diff"] == 0.0
    assert diff_row["objective_impact_linear"] == 0.0
    assert diff_row["objective_impact_quadratic"] == 0.0
    assert diff_row["objective_impact_total"] == 0.0


def test_compare_reports_objective_delta_between_solvers(client, cuopt_job, alglib_job):
    response = client.post(
        "/compare/jobs",
        json={"reference_job_id": cuopt_job["job_id"], "alt_job_ids": [alglib_job["job_id"]]},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    obj_row = data["objective"][0]
    assert obj_row["alt_job_id"] == alglib_job["job_id"]
    assert obj_row["alt_solver"] == "alglib"
    assert math.isclose(obj_row["reference_objective"], cuopt_job["objective"], rel_tol=1e-9)
    assert math.isclose(obj_row["alt_objective"], alglib_job["objective"], rel_tol=1e-9)
    # This file has integer variables — both solvers respect that (real
    # branch-and-bound, not a relaxation), so unlike a pure LP/QP they
    # aren't guaranteed to land on the exact same objective: two different
    # B&B implementations can each stop at a slightly different point
    # within their own gap tolerance and still both be genuinely optimal.
    # 1% matches the cross-solver tolerance already accepted for QP (see
    # test_qp_solvers_agree_on_objective) — the actual gap here is
    # ~0.00001%, nowhere near it.
    assert abs(obj_row["delta_rel_pct"]) < 1.0


def test_compare_reports_violations_for_every_job(client, cuopt_job, alglib_job):
    response = client.post(
        "/compare/jobs",
        json={"reference_job_id": cuopt_job["job_id"], "alt_job_ids": [alglib_job["job_id"]]},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    violation_job_ids = {row["job_id"] for row in data["violations"]}
    assert violation_job_ids == {cuopt_job["job_id"], alglib_job["job_id"]}
    for row in data["violations"]:
        assert row["max_violation"] is not None
        assert row["num_violations"] is not None
        assert row["within_tolerance"] is not None


def test_compare_reports_solution_vector_diff(client, cuopt_job, alglib_job):
    response = client.post(
        "/compare/jobs",
        json={"reference_job_id": cuopt_job["job_id"], "alt_job_ids": [alglib_job["job_id"]]},
    )
    assert response.status_code == 200, response.text
    diff_row = response.json()["solution_diff"][0]
    assert diff_row["alt_job_id"] == alglib_job["job_id"]
    assert diff_row["num_diffs"] > 0  # LP relaxation vs MILP — some variables genuinely differ
    assert diff_row["max_diff"] > 0
    assert diff_row["error"] is None


def test_compare_rejects_empty_alt_list(client, cuopt_job):
    response = client.post(
        "/compare/jobs", json={"reference_job_id": cuopt_job["job_id"], "alt_job_ids": []}
    )
    assert response.status_code == 400


def test_compare_unknown_reference_job_returns_404(client, cuopt_job):
    response = client.post(
        "/compare/jobs",
        json={"reference_job_id": "does-not-exist", "alt_job_ids": [cuopt_job["job_id"]]},
    )
    assert response.status_code == 404


def test_compare_unknown_alt_job_returns_404(client, cuopt_job):
    response = client.post(
        "/compare/jobs",
        json={"reference_job_id": cuopt_job["job_id"], "alt_job_ids": ["does-not-exist"]},
    )
    assert response.status_code == 404


# --- QP (QMATRIX section) coverage --------------------------------------
# The shared MPS parser used to IndexError on any QMATRIX-bearing file
# (mistaking the section header, and then its data lines, for BOUNDS
# entries) rather than actually reading the quadratic objective. These are
# a regression test for that, plus for the objective_impact_quadratic split.


@pytest.fixture(scope="session")
def cuopt_qp_job(client):
    with open(QP_MPS_FILE, "rb") as f:
        response = client.post(
            "/solve/cuopt",
            files={"mps_file": ("qp.mps", f, "text/plain")},
            data={"flags": json.dumps({"flags": {"time-limit": 30}})},
        )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture(scope="session")
def cplex_qp_job(client):
    with open(QP_MPS_FILE, "rb") as f:
        response = client.post(
            "/solve/cplex",
            files={"mps_file": ("qp.mps", f, "text/plain")},
            data={"flags": json.dumps({"flags": {}})},
        )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture(scope="session")
def alglib_qp_job(client):
    with open(QP_MPS_FILE, "rb") as f:
        response = client.post(
            "/solve/alglib",
            files={"mps_file": ("qp.mps", f, "text/plain")},
            data={"flags": json.dumps({"flags": {}})},
        )
    assert response.status_code == 200, response.text
    return response.json()


def test_qp_solvers_agree_on_objective(cuopt_qp_job, cplex_qp_job, alglib_qp_job):
    assert cuopt_qp_job["state"] == "done"
    assert cplex_qp_job["state"] == "done"
    assert alglib_qp_job["state"] == "done"
    assert math.isclose(cuopt_qp_job["objective"], cplex_qp_job["objective"], rel_tol=1e-2)
    # ALGLIB routes through minqp (not minlp) once a QMATRIX is detected —
    # this is the regression check that it actually engaged, not silently
    # solved the LP relaxation of the linear part alone
    assert math.isclose(cplex_qp_job["objective"], alglib_qp_job["objective"], rel_tol=1e-2)


def test_compare_qp_jobs_reads_qmatrix_without_crashing(client, cuopt_qp_job, cplex_qp_job):
    response = client.post(
        "/compare/jobs",
        json={"reference_job_id": cuopt_qp_job["job_id"], "alt_job_ids": [cplex_qp_job["job_id"]]},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    obj_row = data["objective"][0]
    assert obj_row["error"] is None
    assert abs(obj_row["delta_rel_pct"]) < 1  # both solvers land within ~1% of each other

    violation_row = next(r for r in data["violations"] if r["job_id"] == cuopt_qp_job["job_id"])
    assert violation_row["error"] is None
    assert violation_row["max_violation"] is not None

    diff_row = data["solution_diff"][0]
    assert diff_row["error"] is None
    # this problem genuinely has a nonzero Hessian — the quadratic part of
    # the objective impact split should not be silently zero
    assert diff_row["objective_impact_quadratic"] != 0.0
    assert math.isclose(
        diff_row["objective_impact_linear"] + diff_row["objective_impact_quadratic"],
        diff_row["objective_impact_total"],
        rel_tol=1e-9,
    )
