import ctypes
import platform
import time

from app.config import settings
from app.schemas.common import JobState, SolveStatus

# CPX_PARAMTYPE_* — stable across CPLEX versions.
_PARAMTYPE_INT = 1
_PARAMTYPE_DOUBLE = 2
_PARAMTYPE_STRING = 3
_PARAMTYPE_LONG = 4

_CPXPROB_LP = 0
# CPXPROB_QP — verified empirically against CPXgetprobtype() on a real
# QMATRIX-bearing MPS file (not in the vendored header, only declared in
# cplexdefs.h which isn't shipped with this build).
_CPXPROB_QP = 5

# Only the handful of raw CPXgetstat() codes we're confident about (these are
# long-standing, widely-documented constants). Anything else is left
# unmapped — solve_status=None, raw_status keeps the real code — rather than
# risk misclassifying a code we're not sure of.
_LP_STATUS_MAP = {
    1: SolveStatus.OPTIMAL,  # CPX_STAT_OPTIMAL
    2: SolveStatus.UNBOUNDED,  # CPX_STAT_UNBOUNDED
    3: SolveStatus.INFEASIBLE,  # CPX_STAT_INFEASIBLE
    11: SolveStatus.TIMEOUT,  # CPX_STAT_ABORT_TIME_LIM
}
_MIP_STATUS_MAP = {
    101: SolveStatus.OPTIMAL,  # CPXMIP_OPTIMAL
    103: SolveStatus.INFEASIBLE,  # CPXMIP_INFEASIBLE
    107: SolveStatus.FEASIBLE,  # CPXMIP_TIME_LIM_FEAS
    108: SolveStatus.TIMEOUT,  # CPXMIP_TIME_LIM_INFEAS
}

_lib = None


class CplexError(RuntimeError):
    pass


def _load_library() -> ctypes.CDLL:
    global _lib
    if _lib is not None:
        return _lib

    path = str(settings.cplex_library_path)
    loader = ctypes.WinDLL if platform.system() == "Windows" else ctypes.CDLL
    lib = loader(path)

    lib.CPXopenCPLEX.restype = ctypes.c_void_p
    lib.CPXopenCPLEX.argtypes = [ctypes.POINTER(ctypes.c_int)]
    lib.CPXcloseCPLEX.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    lib.CPXcreateprob.restype = ctypes.c_void_p
    lib.CPXcreateprob.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.c_char_p]
    lib.CPXfreeprob.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    lib.CPXreadcopyprob.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
    lib.CPXgetparamnum.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
    lib.CPXgetparamtype.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    lib.CPXsetintparam.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
    lib.CPXsetdblparam.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_double]
    lib.CPXsetstrparam.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
    lib.CPXsetlongparam.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_longlong]
    lib.CPXfopen.restype = ctypes.c_void_p
    lib.CPXfopen.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    lib.CPXsetlogfile.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.CPXfclose.argtypes = [ctypes.c_void_p]
    lib.CPXmipopt.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.CPXlpopt.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.CPXqpopt.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.CPXgetprobtype.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.CPXgetstat.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.CPXgetobjval.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_double)]
    lib.CPXgetnumcols.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.CPXgetx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_double), ctypes.c_int, ctypes.c_int]
    lib.CPXgeterrorstring.restype = ctypes.c_char_p
    lib.CPXgeterrorstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]

    _lib = lib
    return lib


def _error_string(lib: ctypes.CDLL, env: ctypes.c_void_p, code: int) -> str:
    buf = ctypes.create_string_buffer(1024)
    lib.CPXgeterrorstring(env, code, buf)
    return buf.value.decode("utf-8", errors="replace") or f"CPLEX error {code}"


def _check(lib: ctypes.CDLL, env: ctypes.c_void_p, status: int) -> None:
    if status != 0:
        raise CplexError(_error_string(lib, env, status))


def _set_parameter(lib: ctypes.CDLL, env: ctypes.c_void_p, name: str, value) -> None:
    whichparam = ctypes.c_int()
    _check(lib, env, lib.CPXgetparamnum(env, name.encode("utf-8"), ctypes.byref(whichparam)))

    paramtype = ctypes.c_int()
    _check(lib, env, lib.CPXgetparamtype(env, whichparam.value, ctypes.byref(paramtype)))

    if paramtype.value == _PARAMTYPE_INT:
        _check(lib, env, lib.CPXsetintparam(env, whichparam.value, int(value)))
    elif paramtype.value == _PARAMTYPE_DOUBLE:
        _check(lib, env, lib.CPXsetdblparam(env, whichparam.value, float(value)))
    elif paramtype.value == _PARAMTYPE_STRING:
        _check(lib, env, lib.CPXsetstrparam(env, whichparam.value, str(value).encode("utf-8")))
    elif paramtype.value == _PARAMTYPE_LONG:
        _check(lib, env, lib.CPXsetlongparam(env, whichparam.value, int(value)))
    else:
        raise CplexError(f"unknown parameter type for {name!r}")


def execute(mps_path: str, flags: dict, log_path: str, solution_path: str) -> dict:
    import numpy as np

    lib = _load_library()

    status = ctypes.c_int()
    env = lib.CPXopenCPLEX(ctypes.byref(status))
    if not env:
        return {
            "state": JobState.FAILED,
            "solve_status": None,
            "raw_status": status.value,
            "objective": None,
            "solve_time": None,
            "error": f"CPXopenCPLEX failed (code {status.value})",
        }

    logfile = lib.CPXfopen(log_path.encode("utf-8"), b"w")
    if logfile:
        lib.CPXsetlogfile(env, logfile)

    try:
        for name, value in flags.items():
            _set_parameter(lib, env, name, value)

        lp = lib.CPXcreateprob(env, ctypes.byref(status), b"problem")
        _check(lib, env, status.value)

        started = time.monotonic()
        _check(lib, env, lib.CPXreadcopyprob(env, lp, mps_path.encode("utf-8"), b"MPS"))

        probtype = lib.CPXgetprobtype(env, lp)
        if probtype == _CPXPROB_LP:
            _check(lib, env, lib.CPXlpopt(env, lp))
            status_map = _LP_STATUS_MAP
        elif probtype == _CPXPROB_QP:
            # continuous QP needs its own optimizer call — CPXmipopt refuses
            # it ("Not a mixed-integer problem", verified empirically)
            _check(lib, env, lib.CPXqpopt(env, lp))
            status_map = _LP_STATUS_MAP  # QP shares the LP CPX_STAT_* namespace
        else:
            _check(lib, env, lib.CPXmipopt(env, lp))
            status_map = _MIP_STATUS_MAP
        wall_time = time.monotonic() - started

        raw_status = lib.CPXgetstat(env, lp)

        objval = ctypes.c_double()
        objective = None
        if lib.CPXgetobjval(env, lp, ctypes.byref(objval)) == 0:
            objective = objval.value

        try:
            ncols = lib.CPXgetnumcols(env, lp)
            x = (ctypes.c_double * ncols)()
            if ncols > 0 and lib.CPXgetx(env, lp, x, 0, ncols - 1) == 0:
                np.save(solution_path, np.array(x[:]))
        except Exception:
            pass  # no meaningful primal solution for this outcome

        lib.CPXfreeprob(env, ctypes.byref(ctypes.c_void_p(lp)))

        return {
            "state": JobState.DONE,
            "solve_status": status_map.get(raw_status),
            "raw_status": raw_status,
            "objective": objective,
            "solve_time": wall_time,
            "error": None,
        }
    except CplexError as exc:
        return {
            "state": JobState.FAILED,
            "solve_status": None,
            "raw_status": None,
            "objective": None,
            "solve_time": None,
            "error": str(exc),
        }
    finally:
        if logfile:
            lib.CPXfclose(logfile)
        lib.CPXcloseCPLEX(ctypes.byref(ctypes.c_void_p(env)))
