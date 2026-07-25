from conftest import register_and_login


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_submit_research_enqueues_and_returns_202(client, research_service):
    token = register_and_login(client, "analyst@example.com", "supersecret", "analyst")
    resp = client.post("/api/v1/research", json={"ticker": "NVDA"}, headers=_auth(token))
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    assert body["stream_url"].endswith("/stream")
    assert len(research_service.enqueued) == 1
    assert research_service.enqueued[0]["ticker"] == "NVDA"


def test_viewer_cannot_submit_research(client):
    token = register_and_login(client, "viewer@example.com", "supersecret", "viewer")
    resp = client.post("/api/v1/research", json={"ticker": "NVDA"}, headers=_auth(token))
    assert resp.status_code == 403


def test_invalid_ticker_rejected(client):
    token = register_and_login(client, "a2@example.com", "supersecret", "analyst")
    resp = client.post(
        "/api/v1/research", json={"ticker": "not a ticker"}, headers=_auth(token)
    )
    assert resp.status_code == 422


def test_get_research_result(client):
    token = register_and_login(client, "a3@example.com", "supersecret", "analyst")
    resp = client.get(f"/api/v1/research/{__import__('uuid').uuid4()}", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["ticker"] == "NVDA"


def test_get_research_404_when_missing(client, research_service):
    research_service.result = None
    token = register_and_login(client, "a4@example.com", "supersecret", "analyst")
    resp = client.get(f"/api/v1/research/{__import__('uuid').uuid4()}", headers=_auth(token))
    assert resp.status_code == 404


def test_sse_stream_emits_status_and_complete(client):
    token = register_and_login(client, "a5@example.com", "supersecret", "analyst")
    rid = __import__("uuid").uuid4()
    resp = client.get(f"/api/v1/research/{rid}/stream", headers=_auth(token))
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert "event: status" in resp.text
    assert "event: complete" in resp.text


def test_recommendations_requires_auth_then_ok(client):
    assert client.get("/api/v1/recommendations").status_code == 401
    token = register_and_login(client, "a6@example.com", "supersecret", "analyst")
    resp = client.get("/api/v1/recommendations", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


def test_agent_performance_ok(client):
    token = register_and_login(client, "a7@example.com", "supersecret", "analyst")
    resp = client.get("/api/v1/agent-performance", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["scorecards"] == []


def test_memory_search_ok(client):
    token = register_and_login(client, "a8@example.com", "supersecret", "analyst")
    resp = client.get("/api/v1/memory/search?query=nvidia", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["query"] == "nvidia"
