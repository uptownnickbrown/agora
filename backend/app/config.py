from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "agora"
    env: str = "dev"
    database_url: str = "postgresql+asyncpg://agora:agora@localhost:5432/agora"
    redis_url: str = "redis://localhost:6379/0"
    anthropic_api_key: str = ""
    # Allows POST /demo/* to mint visitor sessions in the demo world.
    demo_enabled: bool = False
    # Tutor model tiers (DECISIONS.md #7)
    model_classify: str = "claude-haiku-4-5"
    model_tutor: str = "claude-sonnet-4-6"
    model_playbook: str = "claude-opus-4-8"

    model_config = {"env_prefix": "AGORA_", "protected_namespaces": ()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
