from collections.abc import AsyncIterator

from app.services.logs.hub import log_hub


async def stream_logs(job_id: str) -> AsyncIterator[str]:
    backlog, queue = log_hub.subscribe(job_id)
    try:
        for line in backlog:
            yield f"data: {line}\n\n"
        while True:
            line = await queue.get()
            if line is None:
                break
            yield f"data: {line}\n\n"
    finally:
        log_hub.unsubscribe(job_id, queue)
