"""User registration / authentication against Postgres."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from aegis_shared.contracts import UserRole
from aegis_shared.db import User

from ..core.security import hash_password, verify_password


class DuplicateEmailError(Exception):
    pass


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(self, email: str, password: str, role: UserRole) -> User:
        user = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            role=role.value,
        )
        self._session.add(user)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise DuplicateEmailError(email)
        await self._session.refresh(user)
        return user

    async def authenticate(self, email: str, password: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.email == email.lower())
        )
        user = result.scalar_one_or_none()
        if user is None or not verify_password(password, user.hashed_password):
            return None
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self._session.get(User, user_id)
