from conftest import register_and_login


def test_register_returns_user(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "password": "supersecret", "role": "analyst"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@example.com"
    assert body["role"] == "analyst"
    assert "id" in body


def test_duplicate_registration_conflicts(client):
    payload = {"email": "dup@example.com", "password": "supersecret"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_login_returns_bearer_token(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "b@example.com", "password": "supersecret"},
    )
    resp = client.post(
        "/api/v1/auth/token", data={"username": "b@example.com", "password": "supersecret"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_rejects_bad_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "c@example.com", "password": "supersecret"},
    )
    resp = client.post(
        "/api/v1/auth/token", data={"username": "c@example.com", "password": "wrong"}
    )
    assert resp.status_code == 401


def test_protected_route_requires_token(client):
    assert client.get("/api/v1/recommendations").status_code == 401


def test_weak_password_rejected(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "d@example.com", "password": "short"},
    )
    assert resp.status_code == 422
