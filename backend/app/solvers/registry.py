from dataclasses import dataclass
from typing import Awaitable, Callable

from app.schemas.jobs import JobResponse
from app.solvers.alglib import service as alglib_service
from app.solvers.alglib.availability import check as alglib_check
from app.solvers.alglib.parameters import ALGLIB_PARAMETERS
from app.solvers.cplex import service as cplex_service
from app.solvers.cplex.availability import check as cplex_check
from app.solvers.cplex.parameters import CPLEX_PARAMETERS
from app.solvers.cuopt import service as cuopt_service
from app.solvers.cuopt.availability import check as cuopt_check
from app.solvers.cuopt.parameters import CUOPT_PARAMETERS
from app.solvers.qore import service as qore_service
from app.solvers.qore.availability import check as qore_check
from app.solvers.qore.parameters import QORE_PARAMETERS

# Returns {"available": bool, "detail": str | None}. Runs inside a spawned
# subprocess — must be a plain module-level function (picklable by
# reference), not a closure/lambda.
CheckFn = Callable[[], dict]

# Each solver's own service.solve(mps_bytes, flags, job_id, filename,
# created_by) -> JobResponse — the one entry point every solver package
# exposes regardless of *how* it actually runs the solve
# (multiprocessing.Process for the in-process solvers, a plain OS subprocess
# under a different interpreter for QORE).
SolveFn = Callable[[bytes, dict, str | None, str | None, str | None], Awaitable[JobResponse]]


@dataclass(frozen=True)
class SolverRegistration:
    key: str
    label: str
    parameters: list[str]
    check_availability: CheckFn
    solve: SolveFn


# Add a new solver here once its app/solvers/<name>/ package (service.py,
# parameters.py, availability.py) exists. Both the DB catalog seed and the
# availability service read from this one list.
KNOWN_SOLVERS = [
    SolverRegistration("cuopt", "cuOpt", CUOPT_PARAMETERS, cuopt_check, cuopt_service.solve),
    SolverRegistration("cplex", "CPLEX", CPLEX_PARAMETERS, cplex_check, cplex_service.solve),
    SolverRegistration("alglib", "ALGLIB", ALGLIB_PARAMETERS, alglib_check, alglib_service.solve),
    SolverRegistration("qore", "QORE", QORE_PARAMETERS, qore_check, qore_service.solve),
]

SOLVERS_BY_KEY = {s.key: s for s in KNOWN_SOLVERS}
