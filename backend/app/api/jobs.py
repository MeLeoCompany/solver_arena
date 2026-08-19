from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse

from app.schemas.jobs import CancelResponse, JobResponse, SolutionResponse
from app.services.jobs.cancel import escalate_after_grace_period, request_cancel
from app.services.jobs.query import (
    DEFAULT_LIST_LIMIT,
    get_full_log,
    get_job_response,
    get_solution_response,
    list_job_responses,
)
from app.services.logs.stream import stream_logs

router = APIRouter()


@router.get("/jobs", response_model=list[JobResponse])
async def list_jobs(
    limit: int = DEFAULT_LIST_LIMIT, offset: int = 0, include_batch_jobs: bool = False
) -> list[JobResponse]:
    return list_job_responses(limit=limit, offset=offset, include_batch_jobs=include_batch_jobs)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    response = get_job_response(job_id)
    if response is None:
        raise HTTPException(status_code=404, detail="job not found")
    return response


@router.get("/jobs/{job_id}/solution", response_model=SolutionResponse)
async def get_job_solution(job_id: str) -> SolutionResponse:
    response = get_solution_response(job_id)
    if response is None:
        raise HTTPException(status_code=404, detail="solution not found")
    return response


@router.get("/jobs/{job_id}/log")
async def get_job_log(job_id: str) -> PlainTextResponse:
    text = get_full_log(job_id)
    if text is None:
        raise HTTPException(status_code=404, detail="job not found")
    return PlainTextResponse(text)


@router.get("/jobs/{job_id}/logs")
async def stream_job_logs(job_id: str) -> StreamingResponse:
    return StreamingResponse(stream_logs(job_id), media_type="text/event-stream")


@router.post("/jobs/{job_id}/cancel", response_model=CancelResponse)
async def cancel_job(job_id: str, background_tasks: BackgroundTasks) -> CancelResponse:
    if not request_cancel(job_id):
        raise HTTPException(status_code=404, detail="job is not currently running")
    background_tasks.add_task(escalate_after_grace_period, job_id)
    return CancelResponse(job_id=job_id, cancelling=True)
