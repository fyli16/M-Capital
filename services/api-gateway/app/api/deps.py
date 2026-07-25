"""FastAPI dependency providers.

Routers depend on *services*, not raw sessions, so tests can override these with
in-memory fakes and exercise the full HTTP surface without a database.
"""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters import Queue
from ..core.db import get_session
from ..services import AuthService, ResearchService


def get_queue(request: Request) -> Queue:
    return request.app.state.queue


def get_auth_service(
    session: AsyncSession = Depends(get_session),
) -> AuthService:
    return AuthService(session)


def get_research_service(
    session: AsyncSession = Depends(get_session),
    queue: Queue = Depends(get_queue),
) -> ResearchService:
    return ResearchService(session, queue)
