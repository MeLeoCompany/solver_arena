from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import JobState, SolveStatus


class JobResponse(BaseModel):
    job_id: str
    solver: str
    state: JobState

    solve_status: SolveStatus | None = None  

    objective: float | None = None
    solve_time: float | None = None

    solution_url: str | None = None
    log_url: str | None = None

    error: str | None = None
    created_at: datetime | None = None

    original_filename: str | None = None
    created_by: str | None = None
    batch_id: str | None = None
    batch_index: int | None = None


class SolutionResponse(BaseModel):
    job_id: str
    variables: list[float] | dict[str, float]


class CancelResponse(BaseModel):
    job_id: str
    cancelling: bool
