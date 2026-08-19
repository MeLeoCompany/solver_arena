import time

from app.schemas.common import JobState, SolveStatus
from app.services.mps.parser import MpsProblem, parse_mps

# From the ALGLIB manual's minlpreport/minqpreport documentation (COMPLETION
# CODES) — ground truth, not guessed (see the CPLEX parameter-name lesson).
# minlp and minqp share the same terminationtype convention (verified
# empirically: a known-optimal minqp solve also returns 1).
_TERMINATION_MAP = {
    1: SolveStatus.OPTIMAL,
    2: SolveStatus.OPTIMAL,
    3: SolveStatus.OPTIMAL,
    4: SolveStatus.OPTIMAL,
    5: SolveStatus.TIMEOUT,  # MaxIts steps was taken
    7: SolveStatus.FEASIBLE,  # stopping conditions too stringent, best point so far
    -3: SolveStatus.INFEASIBLE,  # primal infeasible (dual unbounded)
    -4: SolveStatus.UNBOUNDED,  # primal unbounded (dual infeasible)
}


def _build_sparse_matrix(xalglib, n_cols: int, n_rows: int, rows, cols, values):
    """Build an ALGLIB CRS sparse matrix from COO triplets — both
    minlpsetlc2 and minqpsetlc2/minqpsetquadratictermsparse want the same
    row-by-row-append shape, so this is shared between them.
    """
    grouped: dict[int, list[tuple[int, float]]] = {}
    for r, c, v in zip(rows, cols, values):
        grouped.setdefault(int(r), []).append((int(c), float(v)))
    sparse = xalglib.sparsecreatecrsempty(n_cols)
    for row_idx in range(n_rows):
        entries = sorted(grouped.get(row_idx, []))
        colidx = [c for c, _ in entries]
        vals = [v for _, v in entries]
        xalglib.sparseappendcompressedrow(sparse, colidx, vals, len(entries))
    return sparse


def _solve_milp(xalglib, problem: MpsProblem, flags: dict, log) -> tuple:
    n = problem.var_count
    state = xalglib.minlpcreate(n)

    # minlp only minimizes — negate for MAX, then negate the result back
    cost = (problem.obj if problem.minimize else -problem.obj).tolist()
    xalglib.minlpsetcost(state, cost)
    xalglib.minlpsetbc(state, problem.var_lb.tolist(), problem.var_ub.tolist())

    if problem.row_count:
        sparse = _build_sparse_matrix(
            xalglib, n, problem.row_count, problem.constraint_rows, problem.constraint_cols, problem.constraint_values
        )
        xalglib.minlpsetlc2(state, sparse, problem.row_lo.tolist(), problem.row_hi.tolist(), problem.row_count)

    algorithm = str(flags.get("algorithm", "dss")).lower()
    eps = float(flags.get("eps", 0.0))
    log(f"algorithm={algorithm} eps={eps}")
    if algorithm == "ipm":
        xalglib.minlpsetalgoipm(state, eps)
    else:
        xalglib.minlpsetalgodss(state, eps)

    log("optimizing...")
    started = time.monotonic()
    xalglib.minlpoptimize(state)
    wall_time = time.monotonic() - started

    x, rep = xalglib.minlpresults(state)
    log(
        f"terminationtype={rep.terminationtype} iterations={rep.iterationscount} "
        f"primalerror={rep.primalerror} dualerror={rep.dualerror}"
    )
    return x, rep.terminationtype, rep.f, wall_time


def _solve_qp(xalglib, problem: MpsProblem, flags: dict, log) -> tuple:
    n = problem.var_count
    state = xalglib.minqpcreate(n)

    sign = 1.0 if problem.minimize else -1.0  # minqp only minimizes too
    cost = (sign * problem.obj).tolist()
    xalglib.minqpsetlinearterm(state, cost)

    # minqpsetquadratictermsparse wants only one triangle (isupper=True
    # here) — the MPS QMATRIX section gives the full symmetric matrix.
    upper = problem.quad_rows <= problem.quad_cols
    quad_sparse = _build_sparse_matrix(
        xalglib, n, n,
        problem.quad_rows[upper], problem.quad_cols[upper], sign * problem.quad_values[upper],
    )
    xalglib.minqpsetquadratictermsparse(state, quad_sparse, True)
    xalglib.minqpsetbc(state, problem.var_lb.tolist(), problem.var_ub.tolist())

    if problem.row_count:
        sparse = _build_sparse_matrix(
            xalglib, n, problem.row_count, problem.constraint_rows, problem.constraint_cols, problem.constraint_values
        )
        xalglib.minqpsetlc2(state, sparse, problem.row_lo.tolist(), problem.row_hi.tolist(), problem.row_count)

    eps = float(flags.get("eps", 0.0))
    log(f"algorithm=sparseipm eps={eps}")  # ALGLIB Free Edition's practical default for sparse QP
    xalglib.minqpsetalgosparseipm(state, eps)

    log("optimizing (QP)...")
    started = time.monotonic()
    xalglib.minqpoptimize(state)
    wall_time = time.monotonic() - started

    x, rep = xalglib.minqpresults(state)
    log(
        f"terminationtype={rep.terminationtype} inner_iterations={rep.inneriterationscount} "
        f"outer_iterations={rep.outeriterationscount}"
    )
    return x, rep.terminationtype, rep.f, wall_time


def execute(mps_path: str, flags: dict, log_path: str, solution_path: str) -> dict:
    import numpy as np

    from app.solvers.alglib._lib import import_xalglib

    xalglib = import_xalglib()

    log_file = open(log_path, "w")

    def log(message: str) -> None:
        log_file.write(message + "\n")
        log_file.flush()

    try:
        with open(mps_path) as f:
            problem = parse_mps(f.read())

        log(
            f"parsed MPS: {problem.var_count} variables, {problem.row_count} constraints"
            + (f", {len(problem.quad_rows)} quadratic objective terms (QP)" if problem.is_qp else "")
        )
        if problem.integer_vars:
            log(
                f"WARNING: {len(problem.integer_vars)} integer/binary variables present — "
                "ALGLIB Free Edition has no MIP support, solving as a continuous relaxation"
            )

        if problem.is_qp:
            x, termination_type, f_value, wall_time = _solve_qp(xalglib, problem, flags, log)
        else:
            x, termination_type, f_value, wall_time = _solve_milp(xalglib, problem, flags, log)

        objective = f_value if problem.minimize else -f_value

        try:
            np.save(solution_path, np.array(x))
        except Exception:
            pass  # no meaningful primal solution for this outcome

        return {
            "state": JobState.DONE,
            "solve_status": _TERMINATION_MAP.get(termination_type),
            "raw_status": termination_type,
            "objective": objective,
            "solve_time": wall_time,
            "error": None,
        }
    except Exception as exc:
        log(f"ERROR: {exc}")
        return {
            "state": JobState.FAILED,
            "solve_status": None,
            "raw_status": None,
            "objective": None,
            "solve_time": None,
            "error": str(exc),
        }
    finally:
        log_file.close()
