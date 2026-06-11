"""Auth: magic-link primary, optional password, opaque bearer sessions.

Email delivery is an interface — dev/test mode returns the link token directly;
production wires an SMTP/provider sender. (DECISIONS.md #2)
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuthSession, MagicToken, User
from .common import GameError

SESSION_TTL = timedelta(days=14)
MAGIC_TTL = timedelta(minutes=30)


def _hash_password(password: str) -> str:
    try:
        from argon2 import PasswordHasher

        return PasswordHasher().hash(password)
    except ImportError:  # test environments without argon2
        return "sha256$" + hashlib.sha256(password.encode()).hexdigest()


def _verify_password(password: str, stored: str) -> bool:
    if stored.startswith("sha256$"):
        return stored == "sha256$" + hashlib.sha256(password.encode()).hexdigest()
    try:
        from argon2 import PasswordHasher
        from argon2.exceptions import VerifyMismatchError

        try:
            PasswordHasher().verify(stored, password)
            return True
        except VerifyMismatchError:
            return False
    except ImportError:
        return False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def register(
    db: AsyncSession, email: str, display_name: str, password: str | None = None
) -> User:
    email = email.strip().lower()
    if await db.scalar(select(User).where(User.email == email)):
        raise GameError("an account with that email already exists")
    user = User(
        email=email,
        display_name=display_name.strip()[:120],
        password_hash=_hash_password(password) if password else None,
    )
    db.add(user)
    await db.flush()
    return user


async def request_magic_link(db: AsyncSession, email: str) -> str:
    """Returns the token (dev mode); production emails it and returns ''."""
    token = secrets.token_urlsafe(32)
    db.add(MagicToken(token=token, email=email.strip().lower(), expires_at=_now() + MAGIC_TTL))
    return token


async def redeem_magic_link(db: AsyncSession, token: str) -> AuthSession:
    row = await db.get(MagicToken, token)
    if row is None or row.used or _aware(row.expires_at) < _now():
        raise GameError("invalid or expired sign-in link")
    row.used = True
    user = await db.scalar(select(User).where(User.email == row.email))
    if user is None:
        raise GameError("no account for that email — register first")
    return await _create_session(db, user)


async def login_password(db: AsyncSession, email: str, password: str) -> AuthSession:
    user = await db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not user.password_hash or not _verify_password(password, user.password_hash):
        raise GameError("invalid email or password")
    return await _create_session(db, user)


async def _create_session(db: AsyncSession, user: User) -> AuthSession:
    session = AuthSession(
        token=secrets.token_urlsafe(32), user_id=user.id, expires_at=_now() + SESSION_TTL
    )
    db.add(session)
    await db.flush()
    return session


async def resolve_session(db: AsyncSession, token: str) -> User | None:
    row = await db.get(AuthSession, token)
    if row is None or _aware(row.expires_at) < _now():
        return None
    return await db.get(User, row.user_id)
