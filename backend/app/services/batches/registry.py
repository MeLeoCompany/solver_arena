import asyncio
from dataclasses import dataclass


def batch_log_channel(batch_id: str) -> str:
    """log_hub channel key used for the batch's own relayed/banner log
    stream, distinct from each child job's own job_id-keyed channel.
    """
    return f"batch:{batch_id}"


@dataclass
class RunningBatch:
    task: asyncio.Task
    cancelled: bool = False
    current_job_id: str | None = None


class BatchRegistry:
    """In-memory only, same reasoning as job_registry — tracks the batch
    runner's asyncio task and lets a cancel request reach it.
    """

    def __init__(self) -> None:
        self._batches: dict[str, RunningBatch] = {}

    def register(self, batch_id: str, task: asyncio.Task) -> None:
        self._batches[batch_id] = RunningBatch(task=task)

    def unregister(self, batch_id: str) -> None:
        self._batches.pop(batch_id, None)

    def set_current_job(self, batch_id: str, job_id: str | None) -> None:
        entry = self._batches.get(batch_id)
        if entry is not None:
            entry.current_job_id = job_id

    def is_cancelled(self, batch_id: str) -> bool:
        entry = self._batches.get(batch_id)
        return entry.cancelled if entry else False

    def request_cancel(self, batch_id: str) -> bool:
        entry = self._batches.get(batch_id)
        if entry is None:
            return False
        entry.cancelled = True
        return True

    def get_current_job(self, batch_id: str) -> str | None:
        entry = self._batches.get(batch_id)
        return entry.current_job_id if entry else None


batch_registry = BatchRegistry()
