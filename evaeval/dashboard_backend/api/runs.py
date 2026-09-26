"""Runs API endpoints."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from evaeval.dashboard_backend.auth import require_read_access
from evaeval.dashboard_backend.db.models import Run, get_db
from evaeval.dashboard_backend.rate_limiter import rate_limit

router = APIRouter(
    prefix="/runs",
    tags=["runs"],
    dependencies=[Depends(require_read_access), Depends(rate_limit(limit=60))],
)


@router.get("", response_model=List[Dict[str, Any]])
def list_runs(db: Session = Depends(get_db)):
    """Return all benchmark runs with summary KPIs."""
    runs = db.query(Run).order_by(Run.created_at.desc()).all()
    if not runs:
        # If DB not yet ingested, scan disk directly
        runs_dir = Path("experiments/runs")
        if runs_dir.exists():
            scanned = []
            for d in runs_dir.iterdir():
                if d.is_dir():
                    cfg_file = d / "config.json"
                    metrics_file = d / "results" / "cycle_metrics.json"
                    drift = 0.0
                    succ = 0.0
                    gap = 0.0
                    cost = 0.0
                    if metrics_file.exists():
                        try:
                            with open(metrics_file, "r", encoding="utf-8") as f:
                                ms = json.load(f)
                                if ms:
                                    drift = sum(m["safety_drift"] for m in ms) / len(ms)
                                    succ = sum(m["success_rate"] for m in ms) / len(ms)
                                    gap = sum(m["proxy_gap"] for m in ms) / len(ms)
                                    cost = sum(m["cost_usd"] for m in ms)
                        except Exception:
                            pass
                    scanned.append({
                        "id": d.name,
                        "name": d.name,
                        "created_at": "2026-09-23T21:00:00Z",
                        "status": "completed",
                        "total_cycles": 5,
                        "mean_drift": round(drift, 4),
                        "mean_success_rate": round(succ, 4),
                        "mean_proxy_gap": round(gap, 4),
                        "total_cost_usd": round(cost, 4),
                        "run_dir": str(d),
                    })
            return scanned
        return []

    return [
        {
            "id": r.id,
            "name": r.name,
            "created_at": r.created_at.isoformat(),
            "status": r.status,
            "total_cycles": r.total_cycles,
            "mean_drift": r.mean_drift,
            "mean_success_rate": r.mean_success_rate,
            "mean_proxy_gap": r.mean_proxy_gap,
            "total_cost_usd": r.total_cost_usd,
            "run_dir": r.run_dir,
        }
        for r in runs
    ]


@router.get("/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    """Return specific run metadata, configuration, and overview statistics."""
    run_dir = Path("experiments/runs") / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    cfg = {}
    cfg_file = run_dir / "config.json"
    if cfg_file.exists():
        with open(cfg_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    metrics = []
    metrics_file = run_dir / "results" / "cycle_metrics.json"
    if metrics_file.exists():
        with open(metrics_file, "r", encoding="utf-8") as f:
            metrics = json.load(f)

    return {
        "id": run_id,
        "name": run_id,
        "config": cfg,
        "metrics_count": len(metrics),
        "figures": [f.name for f in (run_dir / "figures").glob("*.png")] if (run_dir / "figures").exists() else [],
    }
