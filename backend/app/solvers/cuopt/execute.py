import time

from app.schemas.common import JobState, SolveStatus

LP_CATEGORY = 0

_LP_STATUS_MAP = {
    1: SolveStatus.OPTIMAL,   # Optimal
    2: SolveStatus.INFEASIBLE,  # PrimalInfeasible
    3: SolveStatus.UNBOUNDED,  # DualInfeasible
    4: SolveStatus.TIMEOUT,   # IterationLimit
    5: SolveStatus.TIMEOUT,   # TimeLimit
    7: SolveStatus.FEASIBLE,  # PrimalFeasible
    11: SolveStatus.INFEASIBLE,  # UnboundedOrInfeasible
}

_MILP_STATUS_MAP = {
    1: SolveStatus.OPTIMAL,   # Optimal
    2: SolveStatus.INFEASIBLE,  # Infeasible
    3: SolveStatus.UNBOUNDED,  # Unbounded
    5: SolveStatus.TIMEOUT,   # TimeLimit
    8: SolveStatus.FEASIBLE,  # FeasibleFound
    11: SolveStatus.INFEASIBLE,  # UnboundedOrInfeasible
}


def execute(mps_path: str, flags: dict, log_path: str, solution_path: str) -> dict:
    import cuopt.linear_programming as lp
    import numpy as np

    settings = lp.SolverSettings()
    for name, value in flags.items():
        settings.set_parameter(name.replace("-", "_"), value)
    settings.set_parameter("log_to_console", False)
    settings.set_parameter("log_file", log_path)

    started = time.monotonic()
    data_model = lp.Read(mps_path)
    solution = lp.Solve(data_model, settings)
    wall_time = time.monotonic() - started

    if solution.get_error_status() != 0:
        return {
            "state": JobState.FAILED,
            "solve_status": None,
            "raw_status": solution.get_error_status(),
            "objective": None,
            "solve_time": wall_time,
            "error": solution.get_error_message(),
        }

    status_map = _LP_STATUS_MAP if solution.get_problem_category() == LP_CATEGORY else _MILP_STATUS_MAP
    raw_status = solution.get_termination_status()

    try:
        np.save(solution_path, solution.get_primal_solution())
    except Exception:
        pass  # no meaningful primal solution for this outcome (e.g. infeasible)

    return {
        "state": JobState.DONE,
        "solve_status": status_map.get(raw_status),
        "raw_status": raw_status,
        "objective": solution.get_primal_objective(),
        "solve_time": solution.get_solve_time(),
        "error": None,
    }
