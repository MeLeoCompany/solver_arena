def test_list_solvers_includes_cuopt_with_parameters(client):
    response = client.get("/solvers")
    assert response.status_code == 200
    solvers = response.json()
    cuopt = next(s for s in solvers if s["key"] == "cuopt")
    assert cuopt["label"] == "cuOpt"
    assert "time_limit" in cuopt["parameters"]
    assert "relative_gap_tolerance" in cuopt["parameters"]
    assert len(cuopt["parameters"]) > 50


def test_list_solvers_includes_cplex_with_parameters(client):
    response = client.get("/solvers")
    assert response.status_code == 200
    solvers = response.json()
    cplex = next(s for s in solvers if s["key"] == "cplex")
    assert cplex["label"] == "CPLEX"
    assert "CPX_PARAM_TILIM" in cplex["parameters"]
    assert len(cplex["parameters"]) > 100


def test_list_solvers_includes_alglib_with_parameters(client):
    response = client.get("/solvers")
    assert response.status_code == 200
    solvers = response.json()
    alglib = next(s for s in solvers if s["key"] == "alglib")
    assert alglib["label"] == "ALGLIB"
    assert "algorithm" in alglib["parameters"]
    assert "eps" in alglib["parameters"]


def test_solvers_report_available_on_this_machine(client):
    """cuOpt, CPLEX and ALGLIB all genuinely work on this dev box (real
    GPU, real license, real library) — the startup check should have
    found that already.
    """
    response = client.get("/solvers")
    solvers = {s["key"]: s for s in response.json()}
    for key in ("cuopt", "cplex", "alglib"):
        assert solvers[key]["available"] is True, solvers[key]["availability_detail"]
        assert solvers[key]["availability_checked_at"] is not None


def test_refresh_solvers_rechecks_availability(client):
    response = client.post("/solvers/refresh")
    assert response.status_code == 200
    solvers = {s["key"]: s for s in response.json()}
    assert solvers["cuopt"]["available"] is True
    assert solvers["cplex"]["available"] is True
    assert solvers["alglib"]["available"] is True
