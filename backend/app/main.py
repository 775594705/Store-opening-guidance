from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.analysis import router as analysis_router
from app.api.routes.health import router as health_router
from app.api.routes.maps import router as maps_router
from app.api.routes.pois import router as pois_router

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
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(maps_router, prefix="/api")
app.include_router(pois_router, prefix="/api")
