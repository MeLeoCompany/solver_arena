from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.models.user import User
from app.schemas.cuopt import CuOptSolveRequest
from app.schemas.jobs import JobResponse
from app.services.auth.dependency import require_user
from app.solvers.cuopt import service as cuopt_service

router = APIRouter()


@router.post("/solve/cuopt", response_model=JobResponse)
async def solve_cuopt(
    mps_file: UploadFile = File(...),
    flags: str = Form("{}"),
    user: User = Depends(require_user),
) -> JobResponse:
    request = CuOptSolveRequest.model_validate_json(flags)
    mps_bytes = await mps_file.read()
    return await cuopt_service.solve(
        mps_bytes, request.flags, request.job_id, mps_file.filename, user.username
    )
