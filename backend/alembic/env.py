"""Alembic migration environment.

Uses the sync psycopg driver; set AGORA_DATABASE_URL (any SQLAlchemy URL — the
async driver suffix is rewritten automatically). First migration is generated
with `alembic revision --autogenerate -m initial` once a database is reachable.
"""
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db import Base
from app import models  # noqa: F401  (register all tables on Base.metadata)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

url = os.environ.get("AGORA_DATABASE_URL", "postgresql+psycopg://agora:agora@localhost:5432/agora")
url = url.replace("+asyncpg", "+psycopg")
config.set_main_option("sqlalchemy.url", url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
