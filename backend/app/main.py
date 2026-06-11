from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.analysis import router as analysis_router
from app.api.routes.health import router as health_router
from app.api.routes.maps import router as maps_router
from app.api.routes.pois import router as pois_router
from app.core.config import get_settings
from app.core.security import RateLimitMiddleware

settings = get_settings()

app = FastAPI(
    title="Store Advisor API",
    version="0.1.0",
    description="Opening-site feasibility analysis and report generation API.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.security_rate_limit_enabled:
    app.add_middleware(
        RateLimitMiddleware,
        default_requests_per_minute=settings.security_rate_limit_requests_per_minute,
        expensive_requests_per_minute=settings.security_rate_limit_expensive_requests_per_minute,
    )

app.include_router(health_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(maps_router, prefix="/api")
app.include_router(pois_router, prefix="/api")
