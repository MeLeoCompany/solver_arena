import asyncio
import json
import uuid

import httpx2
import pytest
from httpx2 import ASGITransport

from tests.conftest import EXAMPLES_DIR, TEST_PASSWORD, TEST_USERNAME

MPS_FILE = EXAMPLES_DIR / "hour[0]_task[1].mps"


def test_solve_accepts_client_supplied_job_id(client):
    job_id = str(uuid.uuid4())
    with open(MPS_FILE, "rb") as f:
        response = client.post(
            "/solve/cuopt",
            files={"mps_file": ("m.mps", f, "text/plain")},
            data={"flags": json.dumps({"flags": {"time-limit": 5}, "job_id": job_id})},
        )
    assert response.status_code == 200
    assert response.json()["job_id"] == job_id

    assert client.get(f"/jobs/{job_id}").status_code == 200


@pytest.mark.asyncio
async def test_can_stream_logs_before_solve_request_resolves(fastapi_app, client):
    """The whole point of a client-supplied job_id: know it up front so the
    log stream can be opened while the POST /solve/cuopt is still pending.
    """
    job_id = str(uuid.uuid4())
    transport = ASGITransport(app=fastapi_app)
    async with httpx2.AsyncClient(transport=transport, base_url="http://test", timeout=60) as async_client:
        login = await async_client.post(
            "/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        assert login.status_code == 200

        async def do_solve():
            with open(MPS_FILE, "rb") as f:
                files = {"mps_file": ("m.mps", f.read(), "text/plain")}
            return await async_client.post(
                "/solve/cuopt",
                files=files,
                data={"flags": json.dumps({"flags": {"time-limit": 5}, "job_id": job_id})},
            )

        solve_task = asyncio.create_task(do_solve())

        got_a_line = False
        async with async_client.stream("GET", f"/jobs/{job_id}/logs") as stream_response:
            async for line in stream_response.aiter_lines():
                if line.startswith("data:"):
                    got_a_line = True
                    break

        solve_response = await solve_task
        assert solve_response.status_code == 200
        assert solve_response.json()["job_id"] == job_id
        assert got_a_line, "never received a log line via SSE while the solve was in flight"
