from fastapi.testclient import TestClient

from tests.conftest import EXAMPLES_DIR, TEST_USERNAME

MPS_FILE = EXAMPLES_DIR / "hour[0]_task[1].mps"


def _create_user(client, username: str) -> dict:
    response = client.post("/users", json={"username": username})
    assert response.status_code == 200, response.text
    return response.json()


def _login(fastapi_app, username: str, password: str) -> TestClient:
    logged_in = TestClient(fastapi_app)
    login = logged_in.post("/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200, login.text
    return logged_in


def test_admin_can_create_and_list_users(client):
    created = _create_user(client, "alice")
    assert created["username"] == "alice"
    assert "password" in created and len(created["password"]) > 0

    listed = client.get("/users")
    assert listed.status_code == 200
    usernames = [u["username"] for u in listed.json()]
    assert "alice" in usernames
    assert all("password" not in u for u in listed.json())  # raw password never re-exposed


def test_new_user_is_not_admin(client):
    created = _create_user(client, "bob")
    listed = client.get("/users").json()
    bob = next(u for u in listed if u["username"] == "bob")
    assert bob["is_admin"] is False


def test_non_admin_cannot_manage_users(client, fastapi_app):
    created = _create_user(client, "carol")
    carol_client = _login(fastapi_app, "carol", created["password"])

    assert carol_client.get("/users").status_code == 403
    assert carol_client.post("/users", json={"username": "dave"}).status_code == 403


def test_admin_cannot_delete_own_account(client):
    admin_id = next(u["id"] for u in client.get("/users").json() if u["username"] == TEST_USERNAME)
    resp = client.delete(f"/users/{admin_id}")
    assert resp.status_code == 400


def test_delete_user_revokes_their_session(client, fastapi_app):
    created = _create_user(client, "erin")
    erin_client = _login(fastapi_app, "erin", created["password"])
    assert erin_client.get("/auth/me").status_code == 200

    delete_resp = client.delete(f"/users/{created['id']}")
    assert delete_resp.status_code == 200

    assert erin_client.get("/auth/me").status_code == 401  # session was cascade-deleted


def test_duplicate_username_returns_400(client):
    _create_user(client, "frank")
    resp = client.post("/users", json={"username": "frank"})
    assert resp.status_code == 400


def test_delete_unknown_user_returns_404(client):
    assert client.delete("/users/999999").status_code == 404


def test_job_created_by_matches_solving_user(client, fastapi_app):
    created = _create_user(client, "grace")
    grace_client = _login(fastapi_app, "grace", created["password"])

    with open(MPS_FILE, "rb") as f:
        response = grace_client.post(
            "/solve/alglib",
            files={"mps_file": ("m.mps", f, "text/plain")},
            data={"flags": '{"flags": {}}'},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["created_by"] == "grace"

    job = client.get(f"/jobs/{body['job_id']}").json()
    assert job["created_by"] == "grace"
