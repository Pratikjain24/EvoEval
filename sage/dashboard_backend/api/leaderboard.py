"""Leaderboard API: Agent group rankings across safety drift and capability gain."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sage.dashboard_backend.auth import require_read_access
from sage.dashboard_backend.rate_limiter import rate_limit

router = APIRouter(
    prefix="/leaderboard",
    tags=["leaderboard"],
    dependencies=[Depends(require_read_access), Depends(rate_limit(limit=120))],
)

DEFAULT_LEADERBOARD = [
    {
        "rank": 1,
        "group": "G6",
        "name": "Regression-Guarded Verifier",
        "capability_gain": 0.32,
        "safety_drift": 0.02,
        "retention_ratio": 0.98,
        "proxy_gap": 0.03,
        "tamper_incidents": 0,
        "cost_usd": 4.12,
        "status": "Optimal Pareto",
    },
    {
        "rank": 2,
        "group": "G5",
        "name": "Static Verifier Agent",
        "capability_gain": 0.28,
        "safety_drift": 0.08,
        "retention_ratio": 0.91,
        "proxy_gap": 0.06,
        "tamper_incidents": 0,
        "cost_usd": 3.85,
        "status": "Safe Gated",
    },
    {
        "rank": 3,
        "group": "G3",
        "name": "Memory Accumulator",
        "capability_gain": 0.24,
        "safety_drift": 0.16,
        "retention_ratio": 0.85,
        "proxy_gap": 0.12,
        "tamper_incidents": 1,
        "cost_usd": 3.10,
        "status": "Moderate Drift",
    },
    {
        "rank": 4,
        "group": "G1",
        "name": "Static Frozen Baseline",
        "capability_gain": 0.00,
        "safety_drift": 0.00,
        "retention_ratio": 1.00,
        "proxy_gap": 0.04,
        "tamper_incidents": 0,
        "cost_usd": 2.20,
        "status": "Frozen Control",
    },
    {
        "rank": 5,
        "group": "G2",
        "name": "Prompt Rewriter",
        "capability_gain": 0.18,
        "safety_drift": 0.22,
        "retention_ratio": 0.74,
        "proxy_gap": 0.21,
        "tamper_incidents": 3,
        "cost_usd": 3.45,
        "status": "High Drift",
    },
    {
        "rank": 6,
        "group": "G4",
        "name": "Reflection Agent",
        "capability_gain": 0.35,
        "safety_drift": 0.29,
        "retention_ratio": 0.68,
        "proxy_gap": 0.32,
        "tamper_incidents": 5,
        "cost_usd": 5.80,
        "status": "Severe Drift & Hacking",
    },
]


@router.get("", response_model=List[Dict[str, Any]])
def get_leaderboard(sort: Optional[str] = Query("safety_drift", description="Field to sort by")):
    """Return comparative leaderboard ranking G1-G6 across safety drift and capability."""
    reverse = False
    sort_key = "safety_drift"

    if sort == "capability_gain":
        sort_key = "capability_gain"
        reverse = True
    elif sort == "retention_ratio":
        sort_key = "retention_ratio"
        reverse = True
    elif sort == "proxy_gap":
        sort_key = "proxy_gap"
        reverse = False
    else:
        sort_key = "safety_drift"
        reverse = False

    sorted_list = sorted(DEFAULT_LEADERBOARD, key=lambda x: x.get(sort_key, 0.0), reverse=reverse)
    for idx, item in enumerate(sorted_list, start=1):
        item["rank"] = idx

    return sorted_list
