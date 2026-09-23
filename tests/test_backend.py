"""Smoke test for FastAPI backend service endpoints."""

import pytest
from fastapi.testclient import TestClient
from evaeval.dashboard_backend.db.models import init_db
from evaeval.dashboard_backend.main import app

# Ensure tables are initialized
init_db()
client = TestClient(app)


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_runs_endpoint():
    res = client.get("/runs")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_leaderboard_endpoint():
    res = client.get("/leaderboard")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 6
    groups = [item["group"] for item in data]
    assert "G1" in groups
    assert "G6" in groups


def test_audit_queue_endpoint():
    res = client.get("/audit/queue")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_audit_submission():
    payload = {
        "audit_id": "test_audit_001",
        "run_id": "test_run",
        "annotator_id": "test_user",
        "is_violation": True,
        "is_reward_hacked": False,
        "failure_severity": "benign",
        "notes": "Test label notes",
    }
    res = client.post("/audit/labels", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "success"
