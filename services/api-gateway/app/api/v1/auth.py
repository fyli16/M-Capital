"""Auth endpoints: register + token (OAuth2 password flow)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ...config import Settings, get_settings
from ...core.rate_limit import RateLimit
from ...core.security import create_access_token
from ...dtos.auth import RegisterRequest, TokenResponse, UserResponse
from ...services import AuthService, DuplicateEmailError
from ..deps import get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

# Stricter limit on auth endpoints to blunt credential stuffing / brute force.
_auth_limit = RateLimit(requests=10, window=60)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
    _: None = Depends(_auth_limit),
) -> UserResponse:
    try:
        user = await service.register(body.email, body.password, body.role)
    except DuplicateEmailError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    return UserResponse.model_validate(user)


@router.post("/token", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
    _: None = Depends(_auth_limit),
) -> TokenResponse:
    user = await service.authenticate(form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    from aegis_shared.contracts import UserRole

    token, ttl = create_access_token(
        user_id=user.id,
        email=user.email,
        role=UserRole(user.role),
        settings=settings,
    )
    return TokenResponse(access_token=token, expires_in=ttl)
