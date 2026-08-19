from app.database import SessionLocal
from app.models.solver import Solver, SolverParameter
from app.schemas.solvers import SolverResponse
from app.services.availability.availability import availability_registry
from app.solvers.registry import KNOWN_SOLVERS


def seed_solvers() -> None:
    with SessionLocal() as db:
        for reg in KNOWN_SOLVERS:
            if db.query(Solver).filter_by(key=reg.key).first() is not None:
                continue
            solver = Solver(key=reg.key, label=reg.label)
            solver.parameters = [SolverParameter(name=name) for name in reg.parameters]
            db.add(solver)
        db.commit()


def list_solvers() -> list[SolverResponse]:
    with SessionLocal() as db:
        solvers = db.query(Solver).order_by(Solver.key).all()
        result = []
        for s in solvers:
            status = availability_registry.get(s.key)
            result.append(
                SolverResponse(
                    key=s.key,
                    label=s.label,
                    parameters=sorted(p.name for p in s.parameters),
                    available=status.available if status else False,
                    availability_detail=status.detail if status else "not checked yet",
                    availability_checked_at=status.checked_at if status else None,
                )
            )
        return result
