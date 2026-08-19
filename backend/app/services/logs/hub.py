import asyncio
import time
from collections import defaultdict

from app.config import settings


class LogHub:
    """In-memory pub/sub for job logs.

    A running solve publishes lines as they appear; GET /jobs/{id}/logs
    subscribes to watch them live. Single-process only — no Redis, matches
    the "минимум инфраструктуры" call for this stage.

    Finished jobs are kept for settings.log_hub_finished_ttl_sec (so a late
    subscriber can still replay them), then evicted — the durable copy
    already lives in the job_logs table, this is just the live-view buffer.
    """

    def __init__(self) -> None:
        self._lines: dict[str, list[str]] = defaultdict(list)
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._finished_at: dict[str, float] = {}

    def publish(self, job_id: str, line: str) -> None:
        self._lines[job_id].append(line)
        for queue in self._subscribers[job_id]:
            queue.put_nowait(line)

    def finish(self, job_id: str) -> None:
        self._finished_at[job_id] = time.monotonic()
        for queue in self._subscribers[job_id]:
            queue.put_nowait(None)
        self._evict_expired()

    def subscribe(self, job_id: str) -> tuple[list[str], "asyncio.Queue"]:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[job_id].append(queue)
        if job_id in self._finished_at:
            queue.put_nowait(None)
        return list(self._lines[job_id]), queue

    def unsubscribe(self, job_id: str, queue: "asyncio.Queue") -> None:
        self._subscribers[job_id].remove(queue)
        if not self._subscribers[job_id]:
            del self._subscribers[job_id]

    def _evict_expired(self) -> None:
        cutoff = time.monotonic() - settings.log_hub_finished_ttl_sec
        expired = [job_id for job_id, ts in self._finished_at.items() if ts < cutoff]
        for job_id in expired:
            self._finished_at.pop(job_id, None)
            self._lines.pop(job_id, None)
            self._subscribers.pop(job_id, None)


log_hub = LogHub()
