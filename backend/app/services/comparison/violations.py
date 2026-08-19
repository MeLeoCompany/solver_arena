import numpy as np

from app.schemas.comparison import ViolationRow
from app.services.comparison.loader import LoadedJob

DEFAULT_TOLERANCE = 1e-6


def analyze(jobs: list[LoadedJob], tolerance: float = DEFAULT_TOLERANCE) -> list[ViolationRow]:
    rows = []
    for job in jobs:
        if job.solution is None:
            rows.append(
                ViolationRow(
                    job_id=job.job_id,
                    solver=job.solver,
                    max_violation=None,
                    num_violations=None,
                    within_tolerance=None,
                    error="job has no saved solution vector",
                )
            )
            continue

        x = np.asarray(job.solution, dtype=float)
        if len(x) < job.problem.var_count:
            rows.append(
                ViolationRow(
                    job_id=job.job_id,
                    solver=job.solver,
                    max_violation=None,
                    num_violations=None,
                    within_tolerance=None,
                    error="solution vector shorter than the problem's variable count",
                )
            )
            continue
        x = x[: job.problem.var_count]

        lhs = job.problem.compute_lhs(x)
        below = np.maximum(job.problem.row_lo - lhs, 0.0)
        above = np.maximum(lhs - job.problem.row_hi, 0.0)
        row_violations = np.maximum(below, above)

        max_violation = float(row_violations.max()) if len(row_violations) else 0.0
        num_violations = int((row_violations > tolerance).sum())

        rows.append(
            ViolationRow(
                job_id=job.job_id,
                solver=job.solver,
                max_violation=max_violation,
                num_violations=num_violations,
                within_tolerance=max_violation <= tolerance,
            )
        )
    return rows
