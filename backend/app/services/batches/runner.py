import asyncio
import logging
import uuid

from app.database import SessionLocal
from app.models.batch import Batch
from app.models.job import Job
from app.schemas.common import JobState
from app.services.batches.banners import (
    batch_cancelled_banner,
    batch_done_banner,
    task_end_banner,
    task_start_banner,
)
from app.services.batches.registry import batch_log_channel, batch_registry
from app.services.logs.hub import log_hub
from app.solvers.registry import SOLVERS_BY_KEY


async def _relay_job_logs(batch_id: str, job_id: str) -> None:
    """Mirrors one child job's own log_hub channel into the batch's channel
    while that job is the one currently running.
    """
    channel = batch_log_channel(batch_id)
    backlog, queue = log_hub.subscribe(job_id)
    for line in backlog:
        log_hub.publish(channel, line)
    while True:
        line = await queue.get()
        if line is None:
            break
        log_hub.publish(channel, line)
    log_hub.unsubscribe(job_id, queue)


async def run_batch(
    batch_id: str,
    solver_key: str,
    files: list[tuple[str, bytes]],
    flags: dict,
    created_by: str | None = None,
) -> None:
    """Sequential batch runner: one file at a time, full resources per
    solver run — no interleaving, so solver comparisons stay fair.

    Each solver's own service.solve() takes the filename directly (it's
    generic per-job metadata, not batch-specific), but batch_id/batch_index
    genuinely are — those get attached to each resulting Job row afterwards,
    via a plain UPDATE, rather than teaching the solve path about batches.
    """
    registration = SOLVERS_BY_KEY[solver_key]
    channel = batch_log_channel(batch_id)
    total = len(files)

    try:
        for index, (filename, mps_bytes) in enumerate(files, start=1):
            if batch_registry.is_cancelled(batch_id):
                break

            job_id = str(uuid.uuid4())
            batch_registry.set_current_job(batch_id, job_id)

            for line in task_start_banner(index, total, filename, job_id):
                log_hub.publish(channel, line)

            relay_task = asyncio.create_task(_relay_job_logs(batch_id, job_id))
            response = await registration.solve(mps_bytes, flags, job_id, filename, created_by)
            await relay_task

            with SessionLocal() as session:
                job = session.get(Job, job_id)
                job.batch_id = batch_id
                job.batch_index = index
                batch = session.get(Batch, batch_id)
                batch.completed = index
                session.commit()

            for line in task_end_banner(index, total, response.state.value):
                log_hub.publish(channel, line)

        cancelled = batch_registry.is_cancelled(batch_id)
        with SessionLocal() as session:
            batch = session.get(Batch, batch_id)
            batch.state = JobState.CANCELLED.value if cancelled else JobState.DONE.value
            completed = batch.completed
            session.commit()

        for line in (
            batch_cancelled_banner(completed, total) if cancelled else batch_done_banner(total)
        ):
            log_hub.publish(channel, line)
    except Exception:
        logging.exception("batch %s: runner crashed", batch_id)
        with SessionLocal() as session:
            batch = session.get(Batch, batch_id)
            batch.state = JobState.FAILED.value
            session.commit()
        log_hub.publish(channel, f"[batch runner error] {batch_id} crashed, see server logs")
    finally:
        log_hub.finish(channel)
        batch_registry.unregister(batch_id)
