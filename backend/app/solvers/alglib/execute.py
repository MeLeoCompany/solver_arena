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
    """Uses ALGLIB's newer minlpsolver* API (reverse-communication,
    objective/jacobian callback) rather than the older minlp* one —
    verified empirically against real problems before switching (not
    guessed): terminationtype codes 1 (optimal) and -3 (infeasible) match
    the same convention as minlp*/minqp*, and minlpsolversetintkth() was
    confirmed to genuinely branch-and-bound to an integer solution (not a
    no-op) on a small hand-built test, not just accept the flag silently.
    """
    import numpy as np

    n = problem.var_count

    # This solver wants a starting point (it's used to warm-start the
    # subsolver, not just as an initial-feasibility guess) — 0 clipped into
    # each variable's own bounds is a safe default when 0 itself may be
    # outside [lb, ub].
    lb = problem.var_lb
    ub = problem.var_ub
    x0 = np.clip(0.0, lb, ub).tolist()

    state = xalglib.minlpsolvercreate(n, x0)
    xalglib.minlpsolversetbc(state, lb.tolist(), ub.tolist())

    if problem.row_count:
        sparse = _build_sparse_matrix(
            xalglib, n, problem.row_count, problem.constraint_rows, problem.constraint_cols, problem.constraint_values
        )
        xalglib.minlpsolversetlc2(state, sparse, problem.row_lo.tolist(), problem.row_hi.tolist(), problem.row_count)

    # minlpsolver only minimizes — negate for MAX, then negate the result back.
    cost = (problem.obj if problem.minimize else -problem.obj).tolist()

    def calc_func(x, fi, jac, param):
        fi[0] = sum(cost[i] * x[i] for i in range(n))
        for i in range(n):
            jac[0][i] = cost[i]

    # Tuning as validated empirically against real problems, not a reference
    # implementation's defaults taken on faith:
    # - algobbsync/bbsyncprofilesmalltree (present in an earlier draft) were
    #   dropped — on a 36-integer-variable problem they made the search both
    #   slower (527 vs 57 tree nodes) and no more accurate, so there's
    #   nothing they're actually buying here.
    # - subsolverepsf/epsx at eps=1e-2 make the per-node LP subsolver
    #   imprecise enough that branch-and-bound reports a real, feasible MIP
    #   as infeasible (reproduced: with them set, terminationtype=-3 after 3
    #   nodes on that same problem; without, terminationtype=1 with the
    #   correct objective after 57 nodes) — so they're only applied when
    #   there's no branching to do.
    eps = float(flags.get("eps", 1e-2))
    log(f"eps={eps}")
    xalglib.minlpsolversetpdgap(state, eps)

    if problem.integer_vars:
        log(f"{len(problem.integer_vars)} integer/binary variables — branch-and-bound")
        for k in problem.integer_vars:
            xalglib.minlpsolversetintkth(state, int(k))
    else:
        xalglib.minlpsolversetsubsolverepsf(state, eps)
        xalglib.minlpsolversetsubsolverepsx(state, eps)

    log("optimizing...")
    started = time.monotonic()
    xalglib.minlpsolveroptimize_j(state, calc_func)
    wall_time = time.monotonic() - started

    x, rep = xalglib.minlpsolverresults(state)
    log(
        f"terminationtype={rep.terminationtype} nfev={rep.nfev} "
        f"nsubproblems={rep.nsubproblems} ntreenodes={rep.ntreenodes} pdgap={rep.pdgap}"
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
        if problem.is_qp and problem.integer_vars:
            # _solve_qp still goes through the older minqp* API, which has
            # no integer-marking equivalent — unlike the LP path below
            # (minlpsolver*), this one really is relaxation-only for now.
            log(
                f"WARNING: {len(problem.integer_vars)} integer/binary variables present in a QP — "
                "no MIQP support here, solving as a continuous relaxation"
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
