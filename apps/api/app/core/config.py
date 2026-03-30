from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]
API_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_env: str = "development"
    app_url: str = "http://localhost:3000"
    auth_mode: str = "disabled"
    persistence_mode: str = "database"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:55432/tradenoc"
    redis_url: str = "redis://localhost:56379/0"
    llm_api_key: str = "replace-me"
    llm_model_name: str = "gpt-4.1-mini"
    llm_request_timeout_seconds: float = 30.0
    stripe_secret_key: str = "sk_test_placeholder"
    stripe_webhook_secret: str = "whsec_placeholder"
    stripe_price_id_pro: str = "price_pro_placeholder"
    stripe_price_id_elite: str = "price_elite_placeholder"
    stripe_checkout_success_path: str = "/app/settings?billing=success"
    stripe_checkout_cancel_path: str = "/pricing?billing=cancelled"
    stripe_billing_portal_return_path: str = "/app/settings?billing=manage"
    auth_internal_shared_secret: str = "replace-me"
    auth_request_ttl_seconds: int = 300
    port: int = 8000
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", API_ROOT / ".env", ".env"),
        extra="ignore",
    )

    @field_validator("app_url", "database_url", "redis_url", mode="before")
    @classmethod
    def strip_string_values(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if not isinstance(value, str):
            return value

        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)

        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)

        return value

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_placeholder_llm_key(self) -> bool:
        return not self.llm_api_key or self.llm_api_key == "replace-me"

    @property
    def is_placeholder_auth_secret(self) -> bool:
        return not self.auth_internal_shared_secret or self.auth_internal_shared_secret == "replace-me"

    @property
    def is_clerk_configured(self) -> bool:
        return self.auth_mode == "clerk" and not self.is_placeholder_auth_secret


settings = Settings()
