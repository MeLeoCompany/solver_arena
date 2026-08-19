import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.database import SessionLocal
from app.models.batch import Batch
from app.models.user import User
from app.schemas.batches import BatchCancelResponse, BatchFlagsRequest, BatchResponse
from app.schemas.common import JobState
from app.services.auth.dependency import require_user
from app.services.batches.cancel import request_batch_cancel
from app.services.batches.query import DEFAULT_LIST_LIMIT, get_batch_response, list_batch_responses
from app.services.batches.registry import batch_log_channel, batch_registry
from app.services.batches.runner import run_batch
from app.services.batches.zip_reader import BatchZipError, read_mps_files
from app.services.jobs.cancel import escalate_after_grace_period
from app.services.logs.stream import stream_logs
from app.solvers.registry import SOLVERS_BY_KEY

router = APIRouter()


@router.post("/batches", response_model=BatchResponse)
async def create_batch(
    zip_file: UploadFile = File(...),
    solver: str = Form(...),
    flags: str = Form("{}"),
    user: User = Depends(require_user),
) -> BatchResponse:
    if solver not in SOLVERS_BY_KEY:
        raise HTTPException(status_code=400, detail=f"unknown solver: {solver}")

    request = BatchFlagsRequest.model_validate_json(flags)

    zip_bytes = await zip_file.read()
    try:
        files = read_mps_files(zip_bytes)
    except BatchZipError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    batch_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)
    with SessionLocal() as session:
        session.add(
            Batch(
                id=batch_id,
                solver=solver,
                state=JobState.RUNNING.value,
                total=len(files),
                completed=0,
                created_by=user.username,
                created_at=created_at,
            )
        )
        session.commit()

    task = asyncio.create_task(run_batch(batch_id, solver, files, request.flags, user.username))
    batch_registry.register(batch_id, task)

    return BatchResponse(
        batch_id=batch_id,
        solver=solver,
        state=JobState.RUNNING,
        total=len(files),
        completed=0,
        created_by=user.username,
        created_at=created_at,
        jobs=[],
    )


@router.get("/batches", response_model=list[BatchResponse])
async def list_batches(limit: int = DEFAULT_LIST_LIMIT, offset: int = 0) -> list[BatchResponse]:
    return list_batch_responses(limit=limit, offset=offset)


@router.get("/batches/{batch_id}", response_model=BatchResponse)
async def get_batch(batch_id: str) -> BatchResponse:
    response = get_batch_response(batch_id)
    if response is None:
        raise HTTPException(status_code=404, detail="batch not found")
    return response


@router.get("/batches/{batch_id}/logs")
async def stream_batch_logs(batch_id: str) -> StreamingResponse:
    return StreamingResponse(stream_logs(batch_log_channel(batch_id)), media_type="text/event-stream")


@router.post("/batches/{batch_id}/cancel", response_model=BatchCancelResponse)
async def cancel_batch(batch_id: str, background_tasks: BackgroundTasks) -> BatchCancelResponse:
    current_job_id = batch_registry.get_current_job(batch_id)
    if not request_batch_cancel(batch_id):
        raise HTTPException(status_code=404, detail="batch is not currently running")
    if current_job_id is not None:
        background_tasks.add_task(escalate_after_grace_period, current_job_id)
    return BatchCancelResponse(batch_id=batch_id, cancelling=True)
