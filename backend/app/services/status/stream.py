from collections.abc import AsyncIterator

from app.services.jobs.registry import job_registry
from app.services.status.hub import status_hub


async def stream_status() -> AsyncIterator[str]:
    queue = status_hub.subscribe()
    try:
        yield f"data: {job_registry.count()}\n\n"
        while True:
            active_jobs = await queue.get()
            yield f"data: {active_jobs}\n\n"
    finally:
        status_hub.unsubscribe(queue)
