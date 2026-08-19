import ctypes

from app.solvers.cplex.execute import _load_library


def check() -> dict:
    """Runs inside a spawned subprocess — loads the native library there,
    not in the main process (see execute.py for why).

    Actually opens an environment (CPXopenCPLEX), not just dlopen — this
    also catches license problems, not only "wrong binary format for this
    platform".
    """
    try:
        lib = _load_library()
    except OSError as exc:
        return {"available": False, "detail": f"library failed to load: {exc}"}

    status = ctypes.c_int()
    env = lib.CPXopenCPLEX(ctypes.byref(status))
    if not env:
        return {"available": False, "detail": f"CPXopenCPLEX failed (code {status.value})"}

    lib.CPXcloseCPLEX(ctypes.byref(ctypes.c_void_p(env)))
    return {"available": True, "detail": None}
