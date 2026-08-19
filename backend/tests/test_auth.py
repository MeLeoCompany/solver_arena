from fastapi.testclient import TestClient

from tests.conftest import TEST_PASSWORD, TEST_USERNAME


def test_protected_route_without_session_returns_401(fastapi_app):
    with TestClient(fastapi_app) as anon_client:
        response = anon_client.get("/jobs")
        assert response.status_code == 401


def test_login_with_wrong_password_returns_401(fastapi_app):
    with TestClient(fastapi_app) as anon_client:
        response = anon_client.post(
            "/auth/login", json={"username": TEST_USERNAME, "password": "wrong"}
        )
        assert response.status_code == 401


def test_login_then_me_returns_username(fastapi_app):
    with TestClient(fastapi_app) as anon_client:
        login = anon_client.post(
            "/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        assert login.status_code == 200

        me = anon_client.get("/auth/me")
        assert me.status_code == 200
        assert me.json() == {"username": TEST_USERNAME, "is_admin": True}


def test_logout_invalidates_session(fastapi_app):
    with TestClient(fastapi_app) as anon_client:
        anon_client.post(
            "/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        assert anon_client.get("/auth/me").status_code == 200

        logout = anon_client.post("/auth/logout")
        assert logout.status_code == 200

        assert anon_client.get("/auth/me").status_code == 401
