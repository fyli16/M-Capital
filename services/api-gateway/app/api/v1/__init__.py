"""v1 API router aggregation."""

from fastapi import APIRouter

from . import auth, health, memory, performance, recommendations, research

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(research.router)
api_router.include_router(recommendations.router)
api_router.include_router(performance.router)
api_router.include_router(memory.router)

# health + metrics live at the root (no /auth-style prefix)
ops_router = health.router

__all__ = ["api_router", "ops_router"]
