import asyncio
import time

import httpx2
import pytest
from httpx2 import ASGITransport

from app.config import settings
from tests.conftest import EXAMPLES_DIR, TEST_PASSWORD, TEST_USERNAME

LONG_MPS_FILE = EXAMPLES_DIR / "qp_dv_iter_11.mps"
TIME_LIMIT_SEC = 30
CANCEL_AFTER_SEC = 1.0
MAX_WAIT_FOR_UPLOAD_SEC = 20


def test_cancel_unknown_job_returns_404(client):
    response = client.post("/jobs/does-not-exist/cancel")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_stops_a_running_solve(fastapi_app, client):
    transport = ASGITransport(app=fastapi_app)
    async with httpx2.AsyncClient(transport=transport, base_url="http://test", timeout=120) as async_client:
        login = await async_client.post(
            "/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        assert login.status_code == 200, login.text

        result_holder = {}

        async def do_solve():
            with open(LONG_MPS_FILE, "rb") as f:
                files = {"mps_file": ("m.mps", f.read(), "text/plain")}
            t0 = time.monotonic()
            response = await async_client.post(
                "/solve/cuopt",
                files=files,
                data={"flags": f'{{"flags": {{"time-limit": {TIME_LIMIT_SEC}}}}}'},
            )
            result_holder["elapsed"] = time.monotonic() - t0
            result_holder["response"] = response.json()

        solve_task = asyncio.create_task(do_solve())

        job_id = None
        for _ in range(int(MAX_WAIT_FOR_UPLOAD_SEC / 0.2)):
            await asyncio.sleep(0.2)
            uploads = sorted(
                settings.uploads_dir.glob("*.mps"), key=lambda p: p.stat().st_mtime
            )
            if uploads:
                job_id = uploads[-1].stem
                break
        assert job_id is not None, "solve never started uploading"
        assert not solve_task.done()

        await asyncio.sleep(CANCEL_AFTER_SEC)
        cancel_response = await async_client.post(f"/jobs/{job_id}/cancel")
        assert cancel_response.status_code == 200
        assert cancel_response.json() == {"job_id": job_id, "cancelling": True}

        await solve_task

    assert result_holder["elapsed"] < TIME_LIMIT_SEC / 2
    assert result_holder["response"]["state"] == "cancelled"
    assert result_holder["response"]["error"] == "cancelled by user"
