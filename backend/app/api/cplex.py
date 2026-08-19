from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.models.user import User
from app.schemas.cplex import CplexSolveRequest
from app.schemas.jobs import JobResponse
from app.services.auth.dependency import require_user
from app.solvers.cplex import service as cplex_service

router = APIRouter()


@router.post("/solve/cplex", response_model=JobResponse)
async def solve_cplex(
    mps_file: UploadFile = File(...),
    flags: str = Form("{}"),
    user: User = Depends(require_user),
) -> JobResponse:
    request = CplexSolveRequest.model_validate_json(flags)
    mps_bytes = await mps_file.read()
    return await cplex_service.solve(
        mps_bytes, request.flags, request.job_id, mps_file.filename, user.username
    )
