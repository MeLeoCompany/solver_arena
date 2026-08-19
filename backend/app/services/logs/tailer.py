from pathlib import Path

import anyio

from app.services.logs.hub import log_hub

POLL_INTERVAL_SEC = 0.2


class LogTailer:
    def __init__(self) -> None:
        self._position = 0

    def read_new(self, path: Path) -> list[str]:
        if not path.exists():
            return []
        text = path.read_text()
        if len(text) <= self._position:
            return []
        new_text = text[self._position :]
        self._position = len(text)
        return new_text.splitlines()


async def poll_log_file(job_id: str, log_path: Path, tailer: LogTailer) -> None:
    while True:
        await anyio.sleep(POLL_INTERVAL_SEC)
        for line in tailer.read_new(log_path):
            log_hub.publish(job_id, line)
