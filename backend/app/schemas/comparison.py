from pydantic import BaseModel


class CompareJobsRequest(BaseModel):
    reference_job_id: str
    alt_job_ids: list[str]


class ObjectiveComparisonRow(BaseModel):
    alt_job_id: str
    alt_solver: str
    reference_objective: float | None
    alt_objective: float | None
    delta_abs: float | None
    delta_rel_pct: float | None
    reference_status: str | None
    alt_status: str | None
    # Whether the alt job's own MPS file was itself a minimize or maximize
    # problem — compared against CompareJobsResponse.reference_minimize so
    # the frontend can warn if they don't match (a min-vs-max mismatch
    # usually means the two jobs aren't actually the same model).
    alt_minimize: bool
    error: str | None = None
    # Only set for batch-vs-batch comparisons (app/services/comparison/batch.py)
    # — None in the plain job-vs-job path, where the reference job is already
    # known page-wide (CompareJobsResponse.reference_job_id) instead of
    # varying per row.
    batch_index: int | None = None
    reference_job_id: str | None = None
    reference_filename: str | None = None
    alt_filename: str | None = None


class ViolationRow(BaseModel):
    job_id: str
    solver: str
    max_violation: float | None
    num_violations: int | None
    within_tolerance: bool | None
    error: str | None = None
    # Only set for batch-vs-batch comparisons — one job per row here (not a
    # pair), hence a single filename rather than reference/alt.
    batch_index: int | None = None
    filename: str | None = None


class SolutionDiffRow(BaseModel):
    alt_job_id: str
    alt_solver: str
    num_diffs: int | None
    max_diff: float | None
    # Split rather than one opaque number: for a QP, the quadratic term
    # couples variables together and can swamp (or cancel out) the linear
    # part, so collapsing them would hide which one actually drove the
    # difference. objective_impact_quadratic is always 0 for a plain LP/MILP.
    objective_impact_linear: float | None
    objective_impact_quadratic: float | None
    objective_impact_total: float | None
    error: str | None = None
    # Only set for batch-vs-batch comparisons.
    batch_index: int | None = None
    reference_job_id: str | None = None
    reference_filename: str | None = None
    alt_filename: str | None = None


class CompareJobsResponse(BaseModel):
    reference_job_id: str
    reference_minimize: bool
    objective: list[ObjectiveComparisonRow]
    violations: list[ViolationRow]
    solution_diff: list[SolutionDiffRow]


class CompareBatchesRequest(BaseModel):
    reference_batch_id: str
    alt_batch_id: str


class CompareBatchesResponse(BaseModel):
    reference_batch_id: str
    alt_batch_id: str
    objective: list[ObjectiveComparisonRow]
    violations: list[ViolationRow]
    solution_diff: list[SolutionDiffRow]
