from dataclasses import dataclass
from multiprocessing.process import BaseProcess

from app.services.status.hub import status_hub


@dataclass
class RunningJob:
    process: BaseProcess
    cancelled: bool = False


class JobRegistry:
    """Tracks solve subprocesses currently in flight, keyed by job_id.

    A process, not a thread — cuOpt's synchronous Python API has no
    interrupt hook, so the only reliable way to stop a hung solve is to
    kill the OS process running it.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, RunningJob] = {}

    def count(self) -> int:
        return len(self._jobs)

    def register(self, job_id: str, process: BaseProcess) -> None:
        self._jobs[job_id] = RunningJob(process=process)
        status_hub.publish(len(self._jobs))

    def unregister(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)
        status_hub.publish(len(self._jobs))

    def is_cancelled(self, job_id: str) -> bool:
        entry = self._jobs.get(job_id)
        return entry.cancelled if entry else False

    def request_cancel(self, job_id: str) -> bool:
        entry = self._jobs.get(job_id)
        if entry is None or not entry.process.is_alive():
            return False
        entry.cancelled = True
        entry.process.terminate()
        return True

    def escalate_if_alive(self, job_id: str) -> None:
        entry = self._jobs.get(job_id)
        if entry is not None and entry.process.is_alive():
            entry.process.kill()


job_registry = JobRegistry()
