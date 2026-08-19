from app.schemas.jobs import JobResponse
from app.services.jobs import runner
from app.solvers.alglib import execute


async def solve(
    mps_bytes: bytes,
    flags: dict,
    job_id: str | None = None,
    filename: str | None = None,
    created_by: str | None = None,
) -> JobResponse:
    return await runner.run("alglib", execute.execute, mps_bytes, flags, job_id, filename, created_by)
