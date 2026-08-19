from app.schemas.comparison import (
    CompareBatchesResponse,
    ObjectiveComparisonRow,
    SolutionDiffRow,
    ViolationRow,
)
from app.schemas.jobs import JobResponse
from app.services.batches.query import get_batch_response
from app.services.comparison import objective, solution_diff, violations
from app.services.comparison.loader import ComparisonError, load_comparable_job


class BatchComparisonError(ValueError):
    pass


def _missing_pair_rows(
    idx: int, ref_job: JobResponse | None, alt_job: JobResponse | None
) -> tuple[ObjectiveComparisonRow, list[ViolationRow], SolutionDiffRow]:
    missing_side = "reference" if ref_job is None else "alt"
    error = f"no matching file at position {idx} in the {missing_side} batch"

    objective_row = ObjectiveComparisonRow(
        alt_job_id=alt_job.job_id if alt_job else "",
        alt_solver=alt_job.solver if alt_job else "",
        reference_objective=None,
        alt_objective=None,
        delta_abs=None,
        delta_rel_pct=None,
        reference_status=None,
        alt_status=None,
        alt_minimize=False,
        error=error,
        batch_index=idx,
        reference_job_id=ref_job.job_id if ref_job else None,
        reference_filename=ref_job.original_filename if ref_job else None,
        alt_filename=alt_job.original_filename if alt_job else None,
    )
    violation_rows = [
        ViolationRow(
            job_id=job.job_id,
            solver=job.solver,
            max_violation=None,
            num_violations=None,
            within_tolerance=None,
            error=error,
            batch_index=idx,
            filename=job.original_filename,
        )
        for job in (ref_job, alt_job)
        if job is not None
    ]
    diff_row = SolutionDiffRow(
        alt_job_id=alt_job.job_id if alt_job else "",
        alt_solver=alt_job.solver if alt_job else "",
        num_diffs=None,
        max_diff=None,
        objective_impact_linear=None,
        objective_impact_quadratic=None,
        objective_impact_total=None,
        error=error,
        batch_index=idx,
        reference_job_id=ref_job.job_id if ref_job else None,
        reference_filename=ref_job.original_filename if ref_job else None,
        alt_filename=alt_job.original_filename if alt_job else None,
    )
    return objective_row, violation_rows, diff_row


def _load_failure_rows(
    idx: int, ref_job: JobResponse, alt_job: JobResponse, error: str
) -> tuple[ObjectiveComparisonRow, list[ViolationRow], SolutionDiffRow]:
    objective_row = ObjectiveComparisonRow(
        alt_job_id=alt_job.job_id,
        alt_solver=alt_job.solver,
        reference_objective=None,
        alt_objective=None,
        delta_abs=None,
        delta_rel_pct=None,
        reference_status=None,
        alt_status=None,
        alt_minimize=False,
        error=error,
        batch_index=idx,
        reference_filename=ref_job.original_filename,
        alt_filename=alt_job.original_filename,
    )
    violation_rows = [
        ViolationRow(
            job_id=job.job_id,
            solver=job.solver,
            max_violation=None,
            num_violations=None,
            within_tolerance=None,
            error=error,
            batch_index=idx,
            filename=job.original_filename,
        )
        for job in (ref_job, alt_job)
    ]
    diff_row = SolutionDiffRow(
        alt_job_id=alt_job.job_id,
        alt_solver=alt_job.solver,
        num_diffs=None,
        max_diff=None,
        objective_impact_linear=None,
        objective_impact_quadratic=None,
        objective_impact_total=None,
        error=error,
        batch_index=idx,
        reference_filename=ref_job.original_filename,
        alt_filename=alt_job.original_filename,
    )
    return objective_row, violation_rows, diff_row


def compare_batches(reference_batch_id: str, alt_batch_id: str) -> CompareBatchesResponse:
    """batch vs batch — the same three metric services as job vs job
    (app/services/comparison/{objective,violations,solution_diff}.py),
    just called once per matched batch_index pair instead of once for the
    whole request. No new metric math here, purely orchestration.
    """
    reference_batch = get_batch_response(reference_batch_id)
    if reference_batch is None:
        raise BatchComparisonError(f"batch not found: {reference_batch_id}")
    alt_batch = get_batch_response(alt_batch_id)
    if alt_batch is None:
        raise BatchComparisonError(f"batch not found: {alt_batch_id}")

    ref_by_index = {job.batch_index: job for job in reference_batch.jobs if job.batch_index is not None}
    alt_by_index = {job.batch_index: job for job in alt_batch.jobs if job.batch_index is not None}
    all_indices = sorted(set(ref_by_index) | set(alt_by_index))

    objective_rows: list[ObjectiveComparisonRow] = []
    violation_rows: list[ViolationRow] = []
    diff_rows: list[SolutionDiffRow] = []

    for idx in all_indices:
        ref_job = ref_by_index.get(idx)
        alt_job = alt_by_index.get(idx)

        if ref_job is None or alt_job is None:
            obj_row, viol_rows, diff_row = _missing_pair_rows(idx, ref_job, alt_job)
            objective_rows.append(obj_row)
            violation_rows.extend(viol_rows)
            diff_rows.append(diff_row)
            continue

        try:
            reference = load_comparable_job(ref_job.job_id)
            alt = load_comparable_job(alt_job.job_id)
        except ComparisonError as exc:
            obj_row, viol_rows, diff_row = _load_failure_rows(idx, ref_job, alt_job, str(exc))
            objective_rows.append(obj_row)
            violation_rows.extend(viol_rows)
            diff_rows.append(diff_row)
            continue

        obj_row = objective.compare(reference, [alt])[0]
        obj_row.batch_index = idx
        obj_row.reference_job_id = ref_job.job_id
        obj_row.reference_filename = ref_job.original_filename
        obj_row.alt_filename = alt_job.original_filename
        objective_rows.append(obj_row)

        for viol_row, job in zip(violations.analyze([reference, alt]), (ref_job, alt_job)):
            viol_row.batch_index = idx
            viol_row.filename = job.original_filename
            violation_rows.append(viol_row)

        diff_row = solution_diff.compare(reference, [alt])[0]
        diff_row.batch_index = idx
        diff_row.reference_job_id = ref_job.job_id
        diff_row.reference_filename = ref_job.original_filename
        diff_row.alt_filename = alt_job.original_filename
        diff_rows.append(diff_row)

    return CompareBatchesResponse(
        reference_batch_id=reference_batch_id,
        alt_batch_id=alt_batch_id,
        objective=objective_rows,
        violations=violation_rows,
        solution_diff=diff_rows,
    )
