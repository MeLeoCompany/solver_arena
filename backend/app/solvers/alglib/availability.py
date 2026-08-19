def check() -> dict:
    """Runs inside a spawned subprocess, same reasoning as the other
    solvers: keep the native library out of the main process.
    """
    try:
        from app.solvers.alglib._lib import import_xalglib

        xalglib = import_xalglib()
    except Exception as exc:
        return {"available": False, "detail": f"import failed: {exc}"}

    try:
        state = xalglib.minlpcreate(1)
        xalglib.minlpsetcost(state, [1.0])
        xalglib.minlpsetbc(state, [0.0], [1.0])
        xalglib.minlpoptimize(state)
        xalglib.minlpresults(state)
    except Exception as exc:
        return {"available": False, "detail": f"smoke test failed: {exc}"}

    return {"available": True, "detail": None}
