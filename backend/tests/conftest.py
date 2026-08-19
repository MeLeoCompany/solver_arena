import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Must run before any test module (or app.config) is imported, so the
# Settings singleton picks these up on its first (and only) instantiation.
_TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="cvopt-test-data-"))
os.environ["SOLVER_SERVER_DATA_DIR"] = str(_TEST_DATA_DIR)
os.environ["SOLVER_SERVER_DATABASE_URL"] = f"sqlite:///{_TEST_DATA_DIR / 'jobs.db'}"
os.environ["SOLVER_SERVER_ADMIN_USERNAME"] = "test-admin"
os.environ["SOLVER_SERVER_ADMIN_PASSWORD"] = "test-password"

TEST_USERNAME = "test-admin"
TEST_PASSWORD = "test-password"

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture(scope="session")
def fastapi_app():
    from app.main import app

    return app


@pytest.fixture(scope="session")
def client(fastapi_app):
    with TestClient(fastapi_app) as test_client:
        login = test_client.post(
            "/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        assert login.status_code == 200, login.text
        yield test_client
