import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import anyio
import numpy as np

from app.config import settings
from app.database import SessionLocal
from app.models.job import Job, JobFlag, JobLog
from app.schemas.common import JobState, SolveStatus
from app.schemas.jobs import JobResponse
from app.services.jobs.registry import job_registry
from app.services.logs.hub import log_hub
from app.services.logs.tailer import LogTailer, poll_log_file


class _SubprocessHandle:
    """Adapts asyncio.subprocess.Process to the small is_alive/terminate/kill
    interface JobRegistry expects, so cancellation works exactly like it
    does for the multiprocessing-based solvers.
    """

    def __init__(self, process: asyncio.subprocess.Process) -> None:
        self._process = process

    def is_alive(self) -> bool:
        return self._process.returncode is None

    def terminate(self) -> None:
        if self.is_alive():
            self._process.terminate()

    def kill(self) -> None:
        if self.is_alive():
            self._process.kill()


async def run(
    solver_name: str,
    python_executable: str,
    script_path: str,
    mps_bytes: bytes,
    spec_extra: dict,
    job_id: str | None = None,
    filename: str | None = None,
    created_by: str | None = None,
) -> JobResponse:
    """Like app.services.jobs.runner.run(), but for solvers whose
    Python bindings only load under a different interpreter than the app's
    own (see app/solvers/qore/qore_solve.py, the first solver needing this)
    — spawns a genuine OS process running python_executable directly rather
    than multiprocessing.Process, which would require the child to import
    back into this same (incompatible) package.

    The child script gets a single argument: the path to a JSON "spec"
    file (mps_path/log_path/solution_path/result_path plus spec_extra).
    It's expected to append plain-text lines to log_path as it runs, and on
    exit write a JSON object to result_path with keys state/solve_status/
    raw_status/objective/solve_time/error (state and solve_status as the
    plain string values of JobState/SolveStatus), and — only on success —
    a JSON array of solution values to solution_path.
    """
    job_id = job_id or str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)

    mps_path = settings.uploads_dir / f"{job_id}.mps"
    mps_path.write_bytes(mps_bytes)
    log_path = settings.logs_dir / f"{job_id}.log"
    log_path.touch()
    solution_path = settings.results_dir / f"{job_id}.npy"

    spec_path = settings.uploads_dir / f"{job_id}.spec.json"
    result_path = settings.uploads_dir / f"{job_id}.result.json"
    solution_json_path = settings.uploads_dir / f"{job_id}.solution.json"
    spec = {
        "mps_path": str(mps_path),
        "log_path": str(log_path),
        "solution_path": str(solution_json_path),
        "result_path": str(result_path),
        **spec_extra,
    }
    spec_path.write_text(json.dumps(spec))

    logging.info("job %s: starting %s solve (external interpreter)", job_id, solver_name)

    # The child's own stdout/stderr become log_path directly (rather than
    # DEVNULL, with the script writing to log_path itself in parallel) —
    # verified empirically against the real qore_opt_py .so that most of
    # QORE's own solve trace (simplex iterations, B&B node table, presolve
    # summary) is unconditional stdout output, not gated by its logger
    # config at all, so it never reaches a log file opened via its own
    # set_up_logger(). Piping the OS-level stream also sidesteps
    # set_up_logger() truncating log_path out from under a second writer.
    with open(log_path, "ab", buffering=0) as log_fd:
        process = await asyncio.create_subprocess_exec(
            python_executable,
            script_path,
            str(spec_path),
            env=os.environ.copy(),
            stdout=log_fd,
            stderr=log_fd,
        )
        job_registry.register(job_id, _SubprocessHandle(process))

        tailer = LogTailer()
        async with anyio.create_task_group() as tg:
            tg.start_soon(poll_log_file, job_id, log_path, tailer)
            await process.wait()
            tg.cancel_scope.cancel()

    for line in tailer.read_new(log_path):  # catch lines missed between last poll and cancel
        log_hub.publish(job_id, line)
    log_hub.finish(job_id)

    cancelled = job_registry.is_cancelled(job_id)
    job_registry.unregister(job_id)

    if result_path.exists():
        raw_result = json.loads(result_path.read_text())
        result = {
            "state": JobState(raw_result["state"]),
            "solve_status": SolveStatus(raw_result["solve_status"]) if raw_result.get("solve_status") else None,
            "raw_status": raw_result.get("raw_status"),
            "objective": raw_result.get("objective"),
            "solve_time": raw_result.get("solve_time"),
            "error": raw_result.get("error"),
        }
    elif cancelled:
        result = {
            "state": JobState.CANCELLED,
            "solve_status": None,
            "raw_status": process.returncode,
            "objective": None,
            "solve_time": None,
            "error": "cancelled by user",
        }
    else:
        result = {
            "state": JobState.FAILED,
            "solve_status": None,
            "raw_status": process.returncode,
            "objective": None,
            "solve_time": None,
            "error": f"solver process exited unexpectedly (exit code {process.returncode})",
        }

    solution_saved = False
    if solution_json_path.exists():
        values = json.loads(solution_json_path.read_text())
        np.save(solution_path, np.array(values, dtype=float))
        solution_saved = True

    for temp_path in (spec_path, result_path, solution_json_path):
        temp_path.unlink(missing_ok=True)

    job = Job(
        job_id=job_id,
        solver=solver_name,
        state=result["state"].value,
        solve_status=result["solve_status"].value if result["solve_status"] else None,
        raw_status=str(result["raw_status"]) if result["raw_status"] is not None else None,
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
        for name, value in spec_extra.items()
        if name not in ("license_file", "module_dir")
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
