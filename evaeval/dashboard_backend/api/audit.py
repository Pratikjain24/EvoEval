"""Audit Workbench API: queue retrieval and human labeling."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from evaeval.dashboard_backend.db.models import AuditLabel, get_db

router = APIRouter(prefix="/audit", tags=["audit"])


class LabelSubmission(BaseModel):
    audit_id: str
    run_id: str
    annotator_id: str
    is_violation: bool
    is_reward_hacked: bool
    failure_severity: str = "none"
    notes: Optional[str] = ""


@router.get("/queue", response_model=List[Dict[str, Any]])
def get_audit_queue(run_id: Optional[str] = None):
    """Retrieve stratified trajectory items waiting for human audit."""
    runs_dir = Path("experiments/runs")
    if not runs_dir.exists():
        return []

    target_dir = runs_dir / run_id if run_id else None
    if not target_dir:
        available = sorted([p for p in runs_dir.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime)
        if available:
            target_dir = available[-1]

    if not target_dir or not target_dir.exists():
        return []

    queue_file = target_dir / "audit_queue.json"
    if queue_file.exists():
        with open(queue_file, "r", encoding="utf-8") as f:
            return json.load(f)

    # If no queue pre-exported, export now
    from evaeval.runner.audit_export import AuditExporter
    exporter = AuditExporter(target_dir)
    return exporter.extract_audit_queue()


@router.post("/labels")
def submit_audit_label(label: LabelSubmission, db: Session = Depends(get_db)):
    """Save double-blind human judgment on trajectory trace."""
    existing = db.query(AuditLabel).filter(AuditLabel.audit_id == label.audit_id).first()
    if existing:
        existing.annotator_id = label.annotator_id
        existing.is_violation = label.is_violation
        existing.is_reward_hacked = label.is_reward_hacked
        existing.failure_severity = label.failure_severity
        existing.notes = label.notes or ""
    else:
        record = AuditLabel(
            audit_id=label.audit_id,
            run_id=label.run_id,
            annotator_id=label.annotator_id,
            is_violation=label.is_violation,
            is_reward_hacked=label.is_reward_hacked,
            failure_severity=label.failure_severity,
            notes=label.notes or "",
        )
        db.add(record)

    db.commit()
    return {"status": "success", "audit_id": label.audit_id}
