def check() -> dict:
    """Runs inside a spawned subprocess — importing cuopt.linear_programming
    pulls in the full cudf/numba/CUDA stack, which the main API process
    deliberately never touches directly (see execute.py).
    """
    try:
        import cuopt.linear_programming  # noqa: F401
    except Exception as exc:
        return {"available": False, "detail": f"import failed: {exc}"}

    try:
        import numba.cuda

        if not numba.cuda.is_available():
            return {"available": False, "detail": "no CUDA GPU visible"}
    except Exception as exc:
        return {"available": False, "detail": f"GPU check failed: {exc}"}

    return {"available": True, "detail": None}
