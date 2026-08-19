from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.models.user import User
from app.schemas.jobs import JobResponse
from app.schemas.qore import QoreSolveRequest
from app.services.auth.dependency import require_user
from app.solvers.qore import service as qore_service

router = APIRouter()


@router.post("/solve/qore", response_model=JobResponse)
async def solve_qore(
    mps_file: UploadFile = File(...),
    flags: str = Form("{}"),
    user: User = Depends(require_user),
) -> JobResponse:
    request = QoreSolveRequest.model_validate_json(flags)
    mps_bytes = await mps_file.read()
    return await qore_service.solve(
        mps_bytes, request.flags, request.job_id, mps_file.filename, user.username
    )
