"""Trajectories API endpoints: paginated event stream reader."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from evaeval.trajectory.reader import TrajectoryReader

router = APIRouter(prefix="/runs/{run_id}/trajectories", tags=["trajectories"])


@router.get("", response_model=List[Dict[str, Any]])
def get_trajectories(
    run_id: str,
    task_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    group: Optional[str] = Query(None),
    cycle: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Retrieve filtered, paginated trajectory events for a run."""
    run_dir = Path("experiments/runs") / run_id
    jsonl_path = run_dir / "trajectory.jsonl"

    if not jsonl_path.exists():
        return []

    reader = TrajectoryReader(jsonl_path)
    events = []
    count = 0
    skipped = 0

    for ev in reader.stream(
        event_types=event_type,  # type: ignore
        task_id=task_id,
        cycle=cycle,
        group=group,
    ):
        if skipped < offset:
            skipped += 1
            continue
        events.append(ev.model_dump())
        count += 1
        if count >= limit:
            break

    return events
