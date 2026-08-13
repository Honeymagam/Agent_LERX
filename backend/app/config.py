from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./agent.db"
    workspace_root: Path = Path("./workspaces")
    max_debug_iterations: int = Field(default=3, ge=0, le=10)
    execution_timeout_seconds: int = Field(default=120, ge=5, le=900)
    llm_provider: str = "heuristic"
    llm_api_key: str | None = None
    github_token: str | None = None
    secret_key: str = "development-only-change-me"
    initial_admin_email: str = "admin@example.com"
    initial_admin_password: str = "change-this-before-production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
