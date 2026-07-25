"""E2E fixtures. The whole module is skipped unless the stack is reachable, so it
never fails a normal unit-test run.

Bring the stack up first:
    docker compose -f tests/e2e/docker-compose.e2e.yml up --build -d
"""

from __future__ import annotations

import os
import time
import uuid

import httpx
import pytest

API_BASE = os.getenv("E2E_API_URL", "http://localhost:8000").rstrip("/")


def _health_ok() -> bool:
    try:
        r = httpx.get(f"{API_BASE}/health", timeout=3)
        return r.status_code == 200 and r.json().get("database") is True
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def require_stack():
    deadline = time.time() + 30
    while time.time() < deadline:
        if _health_ok():
            return
        time.sleep(2)
    pytest.skip("e2e stack not reachable (start docker-compose.e2e.yml)")


@pytest.fixture(scope="session")
def client() -> httpx.Client:
    with httpx.Client(base_url=API_BASE, timeout=15) as c:
        yield c


@pytest.fixture(scope="session")
def token(client: httpx.Client) -> str:
    email = f"e2e_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret-e2e"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": "analyst"},
    )
    resp = client.post(
        "/api/v1/auth/token", data={"username": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]
