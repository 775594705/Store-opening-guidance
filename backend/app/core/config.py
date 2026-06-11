from functools import lru_cache
from os import getenv
from pathlib import Path
from typing import List

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = BACKEND_ROOT.parent

load_dotenv(WORKSPACE_ROOT / ".env")
load_dotenv(BACKEND_ROOT / ".env", override=False)


class Settings:
    app_env: str = getenv("APP_ENV", "local")
    app_name: str = getenv("APP_NAME", "store-advisor")
    amap_api_key: str = getenv("AMAP_API_KEY", "")
    default_search_radius_meters: int = int(getenv("DEFAULT_SEARCH_RADIUS_METERS", "1000"))
    cors_allow_origins: str = getenv("CORS_ALLOW_ORIGINS", "")
    security_rate_limit_enabled: bool = getenv(
        "SECURITY_RATE_LIMIT_ENABLED",
        "1" if getenv("APP_ENV", "local") == "production" else "0",
    ).lower() in {"1", "true", "yes", "on"}
    security_rate_limit_requests_per_minute: int = int(getenv("SECURITY_RATE_LIMIT_REQUESTS_PER_MINUTE", "120"))
    security_rate_limit_expensive_requests_per_minute: int = int(
        getenv("SECURITY_RATE_LIMIT_EXPENSIVE_REQUESTS_PER_MINUTE", "30")
    )
    llm_provider: str = getenv("LLM_PROVIDER", "qwen")
    llm_api_key: str = getenv("LLM_API_KEY", "")
    llm_model: str = getenv("LLM_MODEL", "qwen-plus")
    database_url: str = getenv("DATABASE_URL", "sqlite:///./store_advisor.db")

    def allowed_cors_origins(self) -> List[str]:
        if self.cors_allow_origins:
            return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]
        if self.app_env == "production":
            return [
                "http://guidance.csgozbt.com",
                "https://guidance.csgozbt.com",
            ]
        return [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "null",
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
