"""Authentication & authorization: password hashing, JWTs, current-user, RBAC.

Password hashing uses PBKDF2-HMAC-SHA256 from the standard library (no native build
dependencies), stored as ``pbkdf2_sha256$iterations$salt_hex$hash_hex``.

Auth is **stateless**: the bearer token carries the user id and role, so the
current-user dependency needs no database round-trip. (Revocation would add a
denylist check; noted as a future enhancement.)
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from aegis_shared.contracts import UserRole

from ..config import Settings, get_settings

_PBKDF2_ITERATIONS = 600_000
_ALGO = "pbkdf2_sha256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=True)


# ---- Password hashing -------------------------------------------------------

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"{_ALGO}${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        if algo != _ALGO:
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iters)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


# ---- JWT --------------------------------------------------------------------

def create_access_token(
    *, user_id: UUID, email: str, role: UserRole, settings: Settings
) -> tuple[str, int]:
    now = int(time.time())
    ttl = settings.jwt_access_ttl_seconds
    claims = {
        "sub": str(user_id),
        "email": email,
        "role": role.value,
        "iat": now,
        "exp": now + ttl,
        "type": "access",
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, ttl


@dataclass
class CurrentUser:
    id: UUID
    email: str
    role: UserRole


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        claims = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError:
        raise credentials_error
    try:
        user = CurrentUser(
            id=UUID(claims["sub"]),
            email=claims.get("email", ""),
            role=UserRole(claims["role"]),
        )
    except (KeyError, ValueError):
        raise credentials_error
    request.state.user_id = str(user.id)  # for audit logging + rate-limit keying
    return user


def require_roles(*roles: UserRole):
    """Dependency factory enforcing that the caller holds one of ``roles``."""

    async def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges",
            )
        return user

    return dependency
