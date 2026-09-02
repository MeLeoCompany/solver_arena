import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.api import alglib, auth, batches, comparison, cplex, cuopt, jobs, qore, qore_versions, solvers, status, users
from app.logging_setup import configure_logging
from app.migrate import run_migrations
from app.services.auth.bootstrap import seed_admin_user
from app.services.auth.dependency import require_admin, require_user
from app.services.availability.availability import check_all_solvers
from app.services.availability.catalog import seed_solvers
from app.storage import init_storage

TAGS_METADATA = [
    {
        "name": "Auth",
        "description": "Log in (session cookie) for browser use, or create a long-lived "
        "API token (`Authorization: Bearer <token>`) for non-browser clients.",
    },
    {
        "name": "Solve",
        "description": "Submit an MPS file to a specific solver — one endpoint per solver. "
        "See **Solvers** for which solvers are available right now and which "
        "parameters each one accepts.",
    },
    {
        "name": "Jobs",
        "description": "Look up a submitted job's status/result, download its solution "
        "vector or full log, stream its log live, or cancel it while it's running.",
    },
    {
        "name": "Batches",
        "description": "Upload a zip of .mps files to run sequentially against one solver "
        "(same flags for all). Returns immediately with a batch_id — track progress via "
        "the batch's own live log stream (which relays each child job's log in turn) or "
        "by polling the batch, whose child jobs are also visible individually under **Jobs**.",
    },
    {
        "name": "Solvers",
        "description": "Catalog of registered solvers: their tunable parameters and "
        "whether each is actually usable on this machine right now.",
    },
    {
        "name": "Compare",
        "description": "Compare a reference job against one or more alternative jobs solving "
        "the same problem: objective value delta, constraint violation check against each "
        "job's own saved solution, and a variable-by-variable solution vector diff.",
    },
    {
        "name": "System",
        "description": "Live server-wide status — how many solves are currently running, "
        "across all users.",
    },
    {
        "name": "Users",
        "description": "Admin-only user management — create, list, and remove accounts. "
        "No roles/permissions beyond admin-vs-not.",
    },
    {
        "name": "QORE versions",
        "description": "Admin-only: upload a replacement QORE .so, smoke-tested before it "
        "goes live, with history and manual rollback. QORE exposes no version string of "
        "its own, so each upload carries an admin-typed label instead.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_storage()
    run_migrations()  # alembic's fileConfig() resets logging, so configure after
    configure_logging()
    seed_admin_user()
    seed_solvers()
    await check_all_solvers()
    logging.info("solver arena ready")
    yield


app = FastAPI(title="Solver Arena", lifespan=lifespan, openapi_tags=TAGS_METADATA)

app.include_router(auth.router, tags=["Auth"])
app.include_router(cuopt.router, tags=["Solve"], dependencies=[Depends(require_user)])
app.include_router(cplex.router, tags=["Solve"], dependencies=[Depends(require_user)])
app.include_router(alglib.router, tags=["Solve"], dependencies=[Depends(require_user)])
app.include_router(qore.router, tags=["Solve"], dependencies=[Depends(require_user)])
app.include_router(jobs.router, tags=["Jobs"], dependencies=[Depends(require_user)])
app.include_router(batches.router, tags=["Batches"], dependencies=[Depends(require_user)])
app.include_router(solvers.router, tags=["Solvers"], dependencies=[Depends(require_user)])
app.include_router(comparison.router, tags=["Compare"], dependencies=[Depends(require_user)])
app.include_router(status.router, tags=["System"], dependencies=[Depends(require_user)])
app.include_router(users.router, tags=["Users"], dependencies=[Depends(require_admin)])
app.include_router(qore_versions.router, tags=["QORE versions"], dependencies=[Depends(require_admin)])
