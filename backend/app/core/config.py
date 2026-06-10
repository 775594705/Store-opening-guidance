from functools import lru_cache
from os import getenv
from pathlib import Path

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
    llm_provider: str = getenv("LLM_PROVIDER", "qwen")
    llm_api_key: str = getenv("LLM_API_KEY", "")
    llm_model: str = getenv("LLM_MODEL", "qwen-plus")
    database_url: str = getenv("DATABASE_URL", "sqlite:///./store_advisor.db")


@lru_cache
def get_settings() -> Settings:
    return Settings()
