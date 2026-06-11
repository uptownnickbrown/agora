from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine():
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)


def make_session_factory(engine=None):
    return async_sessionmaker(engine or make_engine(), expire_on_commit=False)
