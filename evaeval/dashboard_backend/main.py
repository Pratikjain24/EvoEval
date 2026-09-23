"""FastAPI Dashboard Backend Service for EvoEval."""

from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from evaeval.dashboard_backend.api.audit import router as audit_router
from evaeval.dashboard_backend.api.cycles import router as cycles_router
from evaeval.dashboard_backend.api.leaderboard import router as leaderboard_router
from evaeval.dashboard_backend.api.runs import router as runs_router
from evaeval.dashboard_backend.api.trajectories import router as trajectories_router
from evaeval.dashboard_backend.db.models import init_db
from evaeval.dashboard_backend.ingest.watcher import RunWatcher


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
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for Next.js frontend on localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(runs_router)
app.include_router(cycles_router)
app.include_router(trajectories_router)
app.include_router(audit_router)
app.include_router(leaderboard_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "evoeval-dashboard-backend"}
