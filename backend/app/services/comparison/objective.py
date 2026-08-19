from app.schemas.comparison import ObjectiveComparisonRow
from app.services.comparison.loader import LoadedJob

EPS = 1e-9


def compare(reference: LoadedJob, alternatives: list[LoadedJob]) -> list[ObjectiveComparisonRow]:
    rows = []
    for alt in alternatives:
        if reference.objective is None or alt.objective is None:
            rows.append(
                ObjectiveComparisonRow(
                    alt_job_id=alt.job_id,
                    alt_solver=alt.solver,
                    reference_objective=reference.objective,
                    alt_objective=alt.objective,
                    delta_abs=None,
                    delta_rel_pct=None,
                    reference_status=reference.solve_status,
                    alt_status=alt.solve_status,
                    alt_minimize=alt.problem.minimize,
                    error="reference or alt job has no objective value",
                )
            )
            continue

        delta_abs = reference.objective - alt.objective
        denominator = max(abs(reference.objective), abs(alt.objective), EPS)
        delta_rel_pct = (delta_abs / denominator) * 100

        rows.append(
            ObjectiveComparisonRow(
                alt_job_id=alt.job_id,
                alt_solver=alt.solver,
                reference_objective=reference.objective,
                alt_objective=alt.objective,
                delta_abs=delta_abs,
                delta_rel_pct=delta_rel_pct,
                reference_status=reference.solve_status,
                alt_status=alt.solve_status,
                alt_minimize=alt.problem.minimize,
            )
        )
    return rows
