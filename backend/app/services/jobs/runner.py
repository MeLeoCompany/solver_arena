import logging
import multiprocessing as mp
import uuid
from datetime import datetime, timezone
from typing import Callable

import anyio

from app import logging_setup
from app.config import settings
from app.database import SessionLocal
from app.logging_setup import configure_subprocess_logging
from app.models.job import Job, JobFlag, JobLog
from app.schemas.common import JobState
from app.schemas.jobs import JobResponse
from app.services.jobs.registry import job_registry
from app.services.logs.hub import log_hub
from app.services.logs.tailer import LogTailer, poll_log_file

# (mps_path, flags, log_path, solution_path) -> result dict. Runs inside the
# spawned subprocess — must be a plain module-level function (picklable by
# reference across spawn), not a closure/lambda.
ExecuteFn = Callable[[str, dict, str, str], dict]


def _run_in_subprocess(
    execute_fn: ExecuteFn,
    mps_path: str,
    flags: dict,
    log_path: str,
    solution_path: str,
    log_queue: mp.Queue,
    result_queue: mp.Queue,
) -> None:
    configure_subprocess_logging(log_queue)
    try:
        result_queue.put(execute_fn(mps_path, flags, log_path, solution_path))
    except Exception:
        logging.exception("solve subprocess crashed")
        raise


async def run(
    solver_name: str,
    execute_fn: ExecuteFn,
    mps_bytes: bytes,
    flags: dict,
    job_id: str | None = None,
    filename: str | None = None,
    created_by: str | None = None,
) -> JobResponse:
    """Solver-agnostic orchestration: spawn a subprocess running execute_fn,
    tail its log file live, track it for cancellation, persist the result.

    filename is the client's original upload name — not recoverable from
    mps_bytes itself (MPS's own NAME field is a problem name the file's
    author chose, not the filesystem name; most of this project's own
    example files just say "current_problem" there, unrelated to the
    actual filename). Purely metadata, so it's fine for run() to own it
    directly — unlike batch_id/batch_index, which stay a batch-runner
    post-hoc UPDATE since run() has no business knowing about batches.
    created_by (the requesting user's username) is the same kind of plain
    metadata as filename, not batch-specific, so it follows the same path.
    """
    job_id = job_id or str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)

    mps_path = settings.uploads_dir / f"{job_id}.mps"
    mps_path.write_bytes(mps_bytes)
    log_path = settings.logs_dir / f"{job_id}.log"
    solution_path = settings.results_dir / f"{job_id}.npy"

    logging.info("job %s: starting %s solve, flags=%s", job_id, solver_name, flags)

    ctx = mp.get_context("spawn")
    result_queue: mp.Queue = ctx.Queue()
    process = ctx.Process(
        target=_run_in_subprocess,
        args=(
            execute_fn, str(mps_path), flags, str(log_path), str(solution_path),
            logging_setup.logging_manager.log_queue, result_queue,
        ),
    )
    process.start()
    job_registry.register(job_id, process)

    tailer = LogTailer()
    async with anyio.create_task_group() as tg:
        tg.start_soon(poll_log_file, job_id, log_path, tailer)
        await anyio.to_thread.run_sync(process.join)
        tg.cancel_scope.cancel()

    for line in tailer.read_new(log_path):  # catch lines missed between last poll and cancel
        log_hub.publish(job_id, line)
    log_hub.finish(job_id)

    cancelled = job_registry.is_cancelled(job_id)
    job_registry.unregister(job_id)

    if not result_queue.empty():
        result = result_queue.get()
    elif cancelled:
        result = {
            "state": JobState.CANCELLED,
            "solve_status": None,
            "raw_status": process.exitcode,
            "objective": None,
            "solve_time": None,
            "error": "cancelled by user",
        }
    else:
        result = {
            "state": JobState.FAILED,
            "solve_status": None,
            "raw_status": process.exitcode,
            "objective": None,
            "solve_time": None,
            "error": f"solver process exited unexpectedly (exit code {process.exitcode})",
        }

    solution_saved = solution_path.exists()

    job = Job(
        job_id=job_id,
        solver=solver_name,
        state=result["state"].value,
        solve_status=result["solve_status"].value if result["solve_status"] else None,
        raw_status=str(result["raw_status"]),
        objective=result["objective"],
        solve_time=result["solve_time"],
        error=result["error"],
        solution_path=str(solution_path) if solution_saved else None,
        original_filename=filename,
        created_by=created_by,
        created_at=created_at,
    )
    job.flags = [
        JobFlag(job_id=job_id, name=name, value=str(value))
        for name, value in flags.items()
    ]
    if log_path.exists():
        job.logs = [
            JobLog(job_id=job_id, line_no=i, line=line, created_at=created_at)
            for i, line in enumerate(log_path.read_text().splitlines())
        ]

    with SessionLocal() as session:
        session.add(job)
        session.commit()

    logging.info(
        "job %s: finished, state=%s solve_status=%s objective=%s",
        job_id,
        result["state"].value,
        result["solve_status"].value if result["solve_status"] else None,
        result["objective"],
    )

    return JobResponse(
        job_id=job_id,
        solver=solver_name,
        state=result["state"],
        solve_status=result["solve_status"],
        objective=result["objective"],
        solve_time=result["solve_time"],
        error=result["error"],
        solution_url=f"/jobs/{job_id}/solution" if solution_saved else None,
        log_url=f"/jobs/{job_id}/log",
        created_at=created_at,
        original_filename=filename,
        created_by=created_by,
    )
