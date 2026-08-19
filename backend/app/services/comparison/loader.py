from dataclasses import dataclass

import numpy as np

from app.config import settings
from app.database import SessionLocal
from app.models.job import Job
from app.services.mps.parser import MpsProblem, parse_mps


class ComparisonError(ValueError):
    pass


@dataclass
class LoadedJob:
    job_id: str
    solver: str
    state: str
    solve_status: str | None
    objective: float | None
    problem: MpsProblem
    solution: np.ndarray | None


def load_comparable_job(job_id: str) -> LoadedJob:
    with SessionLocal() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise ComparisonError(f"job not found: {job_id}")

        mps_path = settings.uploads_dir / f"{job_id}.mps"
        if not mps_path.exists():
            raise ComparisonError(f"job {job_id}: original MPS file is no longer on disk")
        problem = parse_mps(mps_path.read_text())

        solution = np.load(job.solution_path) if job.solution_path else None

        return LoadedJob(
            job_id=job.job_id,
            solver=job.solver,
            state=job.state,
            solve_status=job.solve_status,
            objective=job.objective,
            problem=problem,
            solution=solution,
        )
