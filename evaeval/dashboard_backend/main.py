"""FastAPI Dashboard Backend Service for EvoEval (Hardened Production Release)."""

from __future__ import annotations
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from evaeval.dashboard_backend.api.audit import router as audit_router
from evaeval.dashboard_backend.api.cycles import router as cycles_router
from evaeval.dashboard_backend.api.leaderboard import router as leaderboard_router
from evaeval.dashboard_backend.api.runs import router as runs_router
from evaeval.dashboard_backend.api.trajectories import router as trajectories_router
from evaeval.dashboard_backend.db.models import init_db
from evaeval.dashboard_backend.ingest.watcher import RunWatcher


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforce defense-in-depth HTTP security headers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "accelerometer=(), camera=(), geolocation=(), microphone=()"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database and sync runs
    init_db()
    watcher = RunWatcher()
    watcher.sync_all_runs()
    yield


app = FastAPI(
    title="EvoEval Dashboard Backend",
    description="Evaluation and monitoring API for self-evolving agent safety drift and capability retention.",
    version="1.0.0",
    lifespan=lifespan,
)

# Hardened CORS policy: restrict to explicit origins in production
raw_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    max_age=86400,
)

# Add security headers
app.add_middleware(SecurityHeadersMiddleware)

# Mount API routers
app.include_router(runs_router)
app.include_router(cycles_router)
app.include_router(trajectories_router)
app.include_router(audit_router)
app.include_router(leaderboard_router)


@app.get("/health")
def health_check():
    """Liveness probe for container orchestrator."""
    return {"status": "ok", "service": "evoeval-dashboard-backend", "version": "1.0.0"}
