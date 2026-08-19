import logging

import anyio

from app.config import settings
from app.services.jobs.registry import job_registry


def request_cancel(job_id: str) -> bool:
    ok = job_registry.request_cancel(job_id)
    if ok:
        logging.info("job %s: cancel requested", job_id)
    return ok


async def escalate_after_grace_period(job_id: str) -> None:
    await anyio.sleep(settings.cancel_grace_period_sec)
    job_registry.escalate_if_alive(job_id)
