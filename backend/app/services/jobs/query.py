import numpy as np

from app.database import SessionLocal
from app.models.job import Job, JobLog
from app.schemas.jobs import JobResponse, SolutionResponse

DEFAULT_LIST_LIMIT = 50


def _to_job_response(job: Job) -> JobResponse:
    return JobResponse(
        job_id=job.job_id,
        solver=job.solver,
        state=job.state,
        solve_status=job.solve_status,
        objective=job.objective,
        solve_time=job.solve_time,
        error=job.error,
        solution_url=f"/jobs/{job.job_id}/solution" if job.solution_path else None,
        log_url=f"/jobs/{job.job_id}/log",
        created_at=job.created_at,
        original_filename=job.original_filename,
        created_by=job.created_by,
        batch_id=job.batch_id,
        batch_index=job.batch_index,
    )


def get_job_response(job_id: str) -> JobResponse | None:
    with SessionLocal() as session:
        job = session.get(Job, job_id)
        return _to_job_response(job) if job is not None else None


def list_job_responses(
    limit: int = DEFAULT_LIST_LIMIT, offset: int = 0, include_batch_jobs: bool = False
) -> list[JobResponse]:
    """Top-level job history — batch children are excluded by default since
    they surface nested under their batch instead (see /batches/{id}).

    include_batch_jobs=True lifts that filter — used by the job-comparison
    picker (app/api/comparison.py's callers), which needs to offer any job
    as a candidate, batch child or not.
    """
    with SessionLocal() as session:
        query = session.query(Job)
        if not include_batch_jobs:
            query = query.filter(Job.batch_id.is_(None))
        jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()
        return [_to_job_response(job) for job in jobs]


def get_solution_response(job_id: str) -> SolutionResponse | None:
    with SessionLocal() as session:
        job = session.get(Job, job_id)
        if job is None or not job.solution_path:
            return None
        variables = np.load(job.solution_path).tolist()
        return SolutionResponse(job_id=job_id, variables=variables)


def get_full_log(job_id: str) -> str | None:
    with SessionLocal() as session:
        job = session.get(Job, job_id)
        if job is None:
            return None
        lines = (
            session.query(JobLog)
            .filter_by(job_id=job_id)
            .order_by(JobLog.line_no)
            .all()
        )
        return "\n".join(line.line for line in lines)
