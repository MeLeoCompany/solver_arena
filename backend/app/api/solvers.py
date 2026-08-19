from fastapi import APIRouter

from app.schemas.solvers import SolverResponse
from app.services.availability.availability import check_all_solvers
from app.services.availability.catalog import list_solvers

router = APIRouter()


@router.get("/solvers", response_model=list[SolverResponse])
async def get_solvers() -> list[SolverResponse]:
    return list_solvers()


@router.post("/solvers/refresh", response_model=list[SolverResponse])
async def refresh_solvers() -> list[SolverResponse]:
    await check_all_solvers()
    return list_solvers()
