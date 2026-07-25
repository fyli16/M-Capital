"""End-to-end: submit research -> SQS -> worker -> Postgres -> read back result."""

from __future__ import annotations

import time

import httpx


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _wait_for_completion(client: httpx.Client, request_id: str, token: str, timeout=90):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        r = client.get(f"/api/v1/research/{request_id}", headers=_auth(token))
        assert r.status_code == 200, r.text
        last = r.json()
        if last["status"] in ("complete", "failed"):
            return last
        time.sleep(2)
    raise AssertionError(f"timed out; last status={last and last['status']}")


def test_full_research_lifecycle(client: httpx.Client, token: str):
    # 1. Submit
    submit = client.post(
        "/api/v1/research",
        json={"ticker": "NVDA", "enable_debate": True, "max_debate_rounds": 3},
        headers=_auth(token),
    )
    assert submit.status_code == 202, submit.text
    request_id = submit.json()["request_id"]

    # 2. Worker consumes from SQS and processes the graph
    result = _wait_for_completion(client, request_id, token)

    # 3. Verify the persisted result
    assert result["status"] == "complete"
    assert result["ticker"] == "NVDA"

    agent_types = {run["agent_type"] for run in result["agent_runs"]}
    assert {"news", "financial", "quant", "macro", "risk"}.issubset(agent_types)
    assert "portfolio_manager" in agent_types

    rec = result["recommendation"]
    assert rec is not None
    assert rec["action"] in ("strong_buy", "buy", "hold", "sell", "strong_sell")
    assert 0.0 <= rec["confidence"] <= 1.0


def test_recommendation_appears_in_list(client: httpx.Client, token: str):
    submit = client.post(
        "/api/v1/research",
        json={"ticker": "AAPL"},
        headers=_auth(token),
    )
    request_id = submit.json()["request_id"]
    _wait_for_completion(client, request_id, token)

    listing = client.get(
        "/api/v1/recommendations?ticker=AAPL", headers=_auth(token)
    )
    assert listing.status_code == 200
    tickers = {row["ticker"] for row in listing.json()}
    assert "AAPL" in tickers


def test_rbac_viewer_cannot_submit(client: httpx.Client):
    import uuid

    email = f"viewer_{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret-e2e", "role": "viewer"},
    )
    tok = client.post(
        "/api/v1/auth/token", data={"username": email, "password": "supersecret-e2e"}
    ).json()["access_token"]

    resp = client.post(
        "/api/v1/research",
        json={"ticker": "NVDA"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert resp.status_code == 403
