"""Auth DTOs (gateway-local; the shared contracts cover research/domain types)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from aegis_shared.contracts import UserRole

_EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., pattern=_EMAIL, max_length=320)
    password: str = Field(..., min_length=8, max_length=200)
    role: UserRole = UserRole.ANALYST


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
