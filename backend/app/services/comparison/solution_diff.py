import numpy as np

from app.schemas.comparison import SolutionDiffRow
from app.services.comparison.loader import LoadedJob

DEFAULT_EPS = 1e-6


def _error_row(alt: LoadedJob, message: str) -> SolutionDiffRow:
    return SolutionDiffRow(
        alt_job_id=alt.job_id,
        alt_solver=alt.solver,
        num_diffs=None,
        max_diff=None,
        objective_impact_linear=None,
        objective_impact_quadratic=None,
        objective_impact_total=None,
        error=message,
    )


def compare(
    reference: LoadedJob, alternatives: list[LoadedJob], eps: float = DEFAULT_EPS
) -> list[SolutionDiffRow]:
    if reference.solution is None:
        return [_error_row(alt, "reference job has no saved solution vector") for alt in alternatives]

    n = reference.problem.var_count
    f = reference.problem.obj
    ref_x = np.asarray(reference.solution, dtype=float)

    rows = []
    for alt in alternatives:
        if alt.solution is None:
            rows.append(_error_row(alt, "alt job has no saved solution vector"))
            continue

        alt_x = np.asarray(alt.solution, dtype=float)
        if len(ref_x) < n or len(alt_x) < n:
            rows.append(_error_row(alt, "solution vector shorter than the reference problem's variable count"))
            continue

        ref_x_n = ref_x[:n]
        alt_x_n = alt_x[:n]
        delta_x = ref_x_n - alt_x_n
        abs_delta = np.abs(delta_x)
        large_diff_idx = np.where((abs_delta > eps) & (f != 0))[0]

        # Linear part still restricted to the "large diff" subset, matching
        # num_diffs/max_diff — a per-variable heuristic that's only valid
        # because the linear objective doesn't couple variables together.
        # The quadratic part can't be attributed the same way (Q_ij mixes i
        # and j), so it's the exact difference over the full vectors:
        # 0.5 x^T Q x is 0 for a plain LP/MILP, so that term is just 0 there.
        impact_linear = float(f[large_diff_idx] @ delta_x[large_diff_idx]) if len(large_diff_idx) else 0.0
        impact_quadratic = reference.problem.compute_quadratic_term(
            ref_x_n
        ) - reference.problem.compute_quadratic_term(alt_x_n)

        rows.append(
            SolutionDiffRow(
                alt_job_id=alt.job_id,
                alt_solver=alt.solver,
                num_diffs=int(len(large_diff_idx)),
                max_diff=float(abs_delta.max()) if len(abs_delta) else 0.0,
                objective_impact_linear=impact_linear,
                objective_impact_quadratic=impact_quadratic,
                objective_impact_total=impact_linear + impact_quadratic,
            )
        )
    return rows
