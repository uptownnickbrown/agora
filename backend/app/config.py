from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "agora"
    env: str = "dev"
    database_url: str = "postgresql+asyncpg://agora:agora@localhost:5432/agora"
    # Comma-separated browser origins allowed to call the API.
    cors_origins: str = "http://localhost:5173"

    @field_validator("database_url")
    @classmethod
    def _async_driver(cls, v: str) -> str:
        # Managed Postgres (Railway et al.) hands out bare postgres:// URLs;
        # the app needs the async driver spelled out.
        if v.startswith("postgres://"):
            v = "postgresql://" + v.removeprefix("postgres://")
        if v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v.removeprefix("postgresql://")
        return v
    redis_url: str = "redis://localhost:6379/0"
    anthropic_api_key: str = ""
    # Outbound email: "console" logs + stores to email_log (dev); "resend"
    # delivers via the Resend HTTPS API (no SMTP needed on Railway).
    email_provider: str = "console"  # console | resend
    resend_api_key: str = ""
    email_from: str = "Agora <brief@agora.dev>"
    # Frontend origin used to build links inside emails (magic links, dashboards).
    app_base_url: str = "http://localhost:5173"
    # Allows POST /demo/* to mint visitor sessions in the demo world.
    demo_enabled: bool = False
    # Shared secret for HTTPS-triggered ops actions (demo rotation). Empty =
    # those endpoints are disabled.
    ops_token: str = ""
    # Tutor model tiers (DECISIONS.md #7)
    model_classify: str = "claude-haiku-4-5"
    model_tutor: str = "claude-sonnet-4-6"
    # Grading a one-sentence answer against an explicit rubric is squarely
    # Haiku work, and the latency difference is felt on every single check.
    model_grader: str = "claude-haiku-4-5"
    model_playbook: str = "claude-opus-4-8"

    model_config = {"env_prefix": "AGORA_", "protected_namespaces": ()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
