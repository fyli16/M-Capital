"""Test harness: builds the app with in-memory fakes so the full HTTP surface is
exercised without a database, Redis, or SQS."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from aegis_shared.contracts import (
    MemorySearchResponse,
    PerformanceLeaderboard,
    RequestStatus,
    ResearchResultView,
    UserRole,
)

from app.api.deps import get_auth_service, get_research_service
from app.config import Settings, get_settings
from app.main import create_app
from app.services import DuplicateEmailError


class FakeAuthService:
    def __init__(self) -> None:
        self._by_email: dict[str, tuple[SimpleNamespace, str]] = {}

    async def register(self, email: str, password: str, role: UserRole):
        email = email.lower()
        if email in self._by_email:
            raise DuplicateEmailError(email)
        user = SimpleNamespace(id=uuid4(), email=email, role=role)
        self._by_email[email] = (user, password)
        return user

    async def authenticate(self, email: str, password: str):
        entry = self._by_email.get(email.lower())
        if entry is None or entry[1] != password:
            return None
        return entry[0]


class FakeResearchService:
    def __init__(self) -> None:
        self.enqueued: list = []
        self.status: RequestStatus | None = RequestStatus.COMPLETE
        self.result: ResearchResultView | None = None

    async def create_request(self, user_id, ticker, enable_debate, max_debate_rounds):
        req = SimpleNamespace(id=uuid4(), ticker=ticker.upper())
        self.enqueued.append(
            {"ticker": req.ticker, "enable_debate": enable_debate, "rounds": max_debate_rounds}
        )
        return req

    async def get_status(self, request_id):
        return self.status

    async def get_result(self, request_id):
        return self.result

    async def list_recommendations(self, ticker, limit, offset):
        return []

    async def agent_leaderboard(self):
        return PerformanceLeaderboard(scorecards=[])

    async def search_memory(self, query, ticker, limit):
        return MemorySearchResponse(query=query, hits=[])


@pytest.fixture
def settings() -> Settings:
    return Settings(
        jwt_secret="test-secret-that-is-at-least-32-bytes-long!!",
        database_url=None,
        redis_url=None,
        environment="dev",
    )


@pytest.fixture
def auth_service() -> FakeAuthService:
    return FakeAuthService()


@pytest.fixture
def research_service() -> FakeResearchService:
    svc = FakeResearchService()
    svc.result = ResearchResultView(
        request_id=uuid4(),
        ticker="NVDA",
        status=RequestStatus.COMPLETE,
        created_at=datetime.now(timezone.utc),
    )
    return svc


@pytest.fixture
def client(settings, auth_service, research_service) -> TestClient:
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_research_service] = lambda: research_service
    with TestClient(app) as c:
        yield c


def register_and_login(client: TestClient, email: str, password: str, role: str = "analyst") -> str:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": role},
    )
    resp = client.post(
        "/api/v1/auth/token", data={"username": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]
