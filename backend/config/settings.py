from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://dsa:dsa_dev_password@localhost:5432/dead_simple_analytics"
    )
    test_database_url: str = (
        "postgresql+psycopg://dsa:dsa_dev_password@localhost:5434/dead_simple_analytics_test"
    )

    admin_username: str = "admin"
    admin_password: str = "changeme123456"
    jwt_secret: str = "dev-secret"
    jwt_expire_minutes: int = 1440

    session_cookie_name: str = "session"
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"

    ip_hash_salt: str = "dev-salt"
    collect_rate_limit_per_min: int = 120
    collect_site_rate_limit_per_min: int = 600
    collect_replay_ttl_sec: int = 600
    login_rate_limit_attempts: int = 10
    login_rate_limit_window_sec: int = 900
    csrf_cookie_name: str = "dsa_csrf"
    public_base_url: str = "http://localhost:8082"
    components_cdn_url: str = "/components"
    app_env: str = "production"
    geolite2_db_path: str = ""

    cors_origins: str = "http://localhost:8082,http://localhost"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
