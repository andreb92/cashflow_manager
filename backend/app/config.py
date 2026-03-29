import logging as _logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    db_path: str = "/app/data/cashflow.db"
    secret_key: str = "dev-secret-key"
    session_encryption_key: str = "0" * 64
    jwt_expire_days: int = 30
    basic_auth_enabled: bool = True
    oidc_enabled: bool = False
    oidc_issuer_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = ""
    allowed_origins: str = "http://localhost:3000"
    tz: str = "Europe/Rome"
    development_mode: bool = False

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    def warn_insecure_defaults(self) -> None:
        if self.development_mode:
            return
        log = _logging.getLogger("cashflow.config")
        if self.secret_key == "dev-secret-key":
            log.warning("SECURITY: SECRET_KEY is using the insecure default — set SECRET_KEY in .env")
        if self.session_encryption_key == "0" * 64:
            log.warning("SECURITY: SESSION_ENCRYPTION_KEY is using the insecure default — set SESSION_ENCRYPTION_KEY in .env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
