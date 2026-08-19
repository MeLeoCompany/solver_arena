from fastapi.testclient import TestClient


def test_create_and_use_api_token(client, fastapi_app):
    create_resp = client.post("/auth/tokens", json={"name": "calc-module"})
    assert create_resp.status_code == 200
    body = create_resp.json()
    assert body["name"] == "calc-module"
    raw_token = body["token"]

    with TestClient(fastapi_app) as bare_client:  # no session cookie at all
        resp = bare_client.get("/jobs", headers={"Authorization": f"Bearer {raw_token}"})
        assert resp.status_code == 200


def test_bearer_token_without_cookie_rejected_when_bogus(fastapi_app):
    with TestClient(fastapi_app) as bare_client:
        resp = bare_client.get("/jobs", headers={"Authorization": "Bearer not-a-real-token"})
        assert resp.status_code == 401


def test_list_and_revoke_token(client, fastapi_app):
    create_resp = client.post("/auth/tokens", json={"name": "to-revoke"})
    token_id = create_resp.json()["id"]
    raw_token = create_resp.json()["token"]

    listed = client.get("/auth/tokens")
    assert listed.status_code == 200
    assert any(t["id"] == token_id for t in listed.json())
    assert "token" not in listed.json()[0]  # raw token never re-exposed

    delete_resp = client.delete(f"/auth/tokens/{token_id}")
    assert delete_resp.status_code == 200

    with TestClient(fastapi_app) as bare_client:
        resp = bare_client.get("/jobs", headers={"Authorization": f"Bearer {raw_token}"})
        assert resp.status_code == 401  # revoked token no longer works


def test_revoke_unknown_token_returns_404(client):
    assert client.delete("/auth/tokens/999999").status_code == 404
