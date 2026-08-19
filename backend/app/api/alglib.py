from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.models.user import User
from app.schemas.alglib import AlglibSolveRequest
from app.schemas.jobs import JobResponse
from app.services.auth.dependency import require_user
from app.solvers.alglib import service as alglib_service

router = APIRouter()


@router.post("/solve/alglib", response_model=JobResponse)
async def solve_alglib(
    mps_file: UploadFile = File(...),
    flags: str = Form("{}"),
    user: User = Depends(require_user),
) -> JobResponse:
    request = AlglibSolveRequest.model_validate_json(flags)
    mps_bytes = await mps_file.read()
    return await alglib_service.solve(
        mps_bytes, request.flags, request.job_id, mps_file.filename, user.username
    )
