import asyncio


class StatusHub:
    """In-memory pub/sub broadcasting the count of currently-running solve
    jobs. Single-process only, same constraint as LogHub
    (app/services/logs/hub.py) — matches this app's single-uvicorn-worker
    architecture, no cross-process backing.
    """

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue] = []

    def publish(self, active_jobs: int) -> None:
        for queue in self._subscribers:
            queue.put_nowait(active_jobs)

    def subscribe(self) -> "asyncio.Queue":
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: "asyncio.Queue") -> None:
        self._subscribers.remove(queue)


status_hub = StatusHub()
