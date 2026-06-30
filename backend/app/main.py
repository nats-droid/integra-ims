# Integra Analytics Backend
# Python + FastAPI — separate service for analytical modules
# Based on PRD Section 2

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import health, auth, analytics, ai_config, remaining_life, dm_screener, rl_confidence

app = FastAPI(
    title="Integra Analytics API",
    description="Backend analitik — Remaining Life, Anomaly Detection, Fleet Risk, DM Validation",
    version="1.0.0",
)

# CORS — allow frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, tags=["Auth"])
app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])
app.include_router(ai_config.router, prefix="/api/v1", tags=["AI Config"])
app.include_router(remaining_life.router, tags=["Remaining Life"])
app.include_router(dm_screener.router, tags=["DM Screener"])
app.include_router(rl_confidence.router, tags=["RL Confidence"])
