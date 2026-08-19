import logging
import multiprocessing as mp
from dataclasses import dataclass
from datetime import datetime, timezone

import anyio

from app import logging_setup
from app.config import settings
from app.logging_setup import configure_subprocess_logging
from app.solvers.registry import KNOWN_SOLVERS, CheckFn


@dataclass
class AvailabilityStatus:
    available: bool
    detail: str | None
    checked_at: datetime


class AvailabilityRegistry:
    """In-memory only — availability is point-in-time machine state
    (GPU present? license valid?), re-derivable any time by re-checking,
    not something worth persisting.
    """

    def __init__(self) -> None:
        self._status: dict[str, AvailabilityStatus] = {}

    def get(self, key: str) -> AvailabilityStatus | None:
        return self._status.get(key)

    def set(self, key: str, status: AvailabilityStatus) -> None:
        self._status[key] = status


availability_registry = AvailabilityRegistry()


def _run_check_in_subprocess(check_fn: CheckFn, log_queue: mp.Queue, result_queue: mp.Queue) -> None:
    configure_subprocess_logging(log_queue)
    try:
        result_queue.put(check_fn())
    except Exception as exc:
        logging.exception("availability check crashed")
        result_queue.put({"available": False, "detail": f"check crashed: {exc}"})


async def _check_one(key: str, check_fn: CheckFn) -> None:
    ctx = mp.get_context("spawn")
    result_queue: mp.Queue = ctx.Queue()
    process = ctx.Process(
        target=_run_check_in_subprocess,
        args=(check_fn, logging_setup.logging_manager.log_queue, result_queue),
    )
    process.start()

    with anyio.move_on_after(settings.availability_check_timeout_sec):
        await anyio.to_thread.run_sync(process.join)

    if process.is_alive():
        process.terminate()
        result = {"available": False, "detail": "availability check timed out"}
    elif not result_queue.empty():
        result = result_queue.get()
    else:
        result = {
            "available": False,
            "detail": f"check process exited unexpectedly (code {process.exitcode})",
        }

    availability_registry.set(
        key,
        AvailabilityStatus(
            available=result.get("available", False),
            detail=result.get("detail"),
            checked_at=datetime.now(timezone.utc),
        ),
    )


async def check_all_solvers() -> None:
    logging.info("checking availability for solvers: %s", [reg.key for reg in KNOWN_SOLVERS])
    async with anyio.create_task_group() as tg:
        for reg in KNOWN_SOLVERS:
            tg.start_soon(_check_one, reg.key, reg.check_availability)
    logging.info(
        "solver availability: %s",
        {reg.key: availability_registry.get(reg.key).available for reg in KNOWN_SOLVERS},
    )
