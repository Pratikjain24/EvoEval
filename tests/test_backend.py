"""Comprehensive tests for FastAPI backend service endpoints, security middleware, and data models."""

from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from sage.dashboard_backend.db.models import init_db
from sage.dashboard_backend.main import app

# Ensure tables are initialized
init_db()
client = TestClient(app)


def test_health_endpoint():
    """Verify liveness probe returns 200 OK and expected service metadata."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "sage-dashboard-backend"
    assert data["version"] == "1.0.0"


def test_runs_endpoint():
    """Verify listing all benchmark runs and validating run KPI summary schema."""
    res = client.get("/runs")
    assert res.status_code == 200
    runs = res.json()
    assert isinstance(runs, list)
    assert len(runs) > 0

    first_run = runs[0]
    expected_fields = [
        "id", "name", "created_at", "status", "total_cycles",
        "mean_drift", "mean_success_rate", "mean_proxy_gap", "total_cost_usd", "run_dir"
    ]
    for field in expected_fields:
        assert field in first_run, f"Missing expected field '{field}' in run summary"

    assert isinstance(first_run["mean_drift"], (int, float))
    assert isinstance(first_run["mean_success_rate"], (int, float))
    assert isinstance(first_run["total_cost_usd"], (int, float))


def test_run_detail_endpoint_found():
    """Verify retrieving specific run metadata and config for an existing run."""
    res = client.get("/runs/pilot_study_canonical")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "pilot_study_canonical"
    assert "config" in data
    assert "metrics_count" in data
    assert isinstance(data["figures"], list)


def test_run_detail_endpoint_not_found_404():
    """Verify 404 HTTP status code is returned for non-existent run ID."""
    res = client.get("/runs/non_existent_run_404_id")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_run_cycles_endpoint_empirical():
    """Verify per-cycle metrics and bootstrap confidence intervals for canonical run."""
    res = client.get("/runs/pilot_study_canonical/cycles")
    assert res.status_code == 200
    cycles = res.json()
    assert isinstance(cycles, list)
    assert len(cycles) > 0

    first_cycle = cycles[0]
    assert "cycle" in first_cycle
    assert "group" in first_cycle
    assert "success_rate_mean" in first_cycle
    assert "success_rate_ci" in first_cycle
    assert "safety_drift_mean" in first_cycle
    assert "safety_drift_ci" in first_cycle
    assert "proxy_gap_mean" in first_cycle
    assert "retention_mean" in first_cycle

    # Verify CI interval ordering
    assert first_cycle["success_rate_ci"][0] <= first_cycle["success_rate_ci"][1]


def test_run_cycles_endpoint_synthetic_fallback():
    """Verify fallback synthetic curve generation when cycle_metrics.json is absent."""
    res = client.get("/runs/arbitrary_virtual_run_id/cycles")
    assert res.status_code == 200
    cycles = res.json()
    assert isinstance(cycles, list)
    assert len(cycles) == 30  # 5 cycles * 6 groups (G1-G6)
    groups = {c["group"] for c in cycles}
    assert {"G1", "G2", "G3", "G4", "G5", "G6"}.issubset(groups)


def test_run_trajectories_pagination():
    """Verify trajectory event stream pagination with limit and offset query parameters."""
    res = client.get("/runs/pilot_study_canonical/trajectories?limit=5&offset=0")
    assert res.status_code == 200
    events = res.json()
    assert isinstance(events, list)
    assert len(events) <= 5

    res_offset = client.get("/runs/pilot_study_canonical/trajectories?limit=5&offset=5")
    assert res_offset.status_code == 200
    events_offset = res_offset.json()
    assert isinstance(events_offset, list)


def test_run_trajectories_filtering():
    """Verify trajectory event stream filtering by task_id and group."""
    res = client.get("/runs/pilot_study_canonical/trajectories?group=G1&limit=10")
    assert res.status_code == 200
    events = res.json()
    assert isinstance(events, list)
    for ev in events:
        if ev.get("group"):
            assert ev["group"] == "G1"


def test_run_trajectories_non_existent():
    """Verify empty trajectory event stream is returned for runs without trajectory file."""
    res = client.get("/runs/non_existent_run/trajectories")
    assert res.status_code == 200
    assert res.json() == []


def test_leaderboard_endpoint():
    """Verify leaderboard endpoint returns rankings for all 6 agent groups."""
    res = client.get("/leaderboard")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 6
    groups = [item["group"] for item in data]
    assert set(groups) == {"G1", "G2", "G3", "G4", "G5", "G6"}

    # Verify rank sequence
    ranks = [item["rank"] for item in data]
    assert ranks == [1, 2, 3, 4, 5, 6]


def test_leaderboard_sorting():
    """Verify leaderboard sorting by capability_gain, retention_ratio, and proxy_gap."""
    # Capability gain sort (descending)
    res_cap = client.get("/leaderboard?sort=capability_gain")
    assert res_cap.status_code == 200
    data_cap = res_cap.json()
    assert data_cap[0]["capability_gain"] >= data_cap[-1]["capability_gain"]

    # Retention ratio sort (descending)
    res_ret = client.get("/leaderboard?sort=retention_ratio")
    assert res_ret.status_code == 200
    data_ret = res_ret.json()
    assert data_ret[0]["retention_ratio"] >= data_ret[-1]["retention_ratio"]

    # Proxy gap sort (ascending)
    res_gap = client.get("/leaderboard?sort=proxy_gap")
    assert res_gap.status_code == 200
    data_gap = res_gap.json()
    assert data_gap[0]["proxy_gap"] <= data_gap[-1]["proxy_gap"]


def test_audit_queue_endpoint():
    """Verify audit queue returns stratified trajectory items for human verification."""
    res = client.get("/audit/queue")
    assert res.status_code == 200
    queue = res.json()
    assert isinstance(queue, list)
    if queue:
        item = queue[0]
        assert "audit_id" in item
        assert "task_id" in item
        assert "group" in item


def test_audit_queue_with_run_id():
    """Verify audit queue retrieval when specifying a target run_id."""
    res = client.get("/audit/queue?run_id=pilot_study_canonical")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_audit_submission_and_upsert():
    """Verify submitting a human audit label and updating existing label (upsert)."""
    payload = {
        "audit_id": "test_audit_001",
        "run_id": "test_run",
        "annotator_id": "auditor_alpha",
        "is_violation": True,
        "is_reward_hacked": False,
        "failure_severity": "moderate",
        "notes": "Original observation: assertion bypass attempt",
    }
    res = client.post("/audit/labels", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert res.json()["audit_id"] == "test_audit_001"

    # Upsert with new notes and updated severity
    payload["notes"] = "Updated observation: confirmed deliberate test runner flag rewrite"
    payload["failure_severity"] = "critical"
    res_update = client.post("/audit/labels", json=payload)
    assert res_update.status_code == 200
    assert res_update.json()["status"] == "success"


def test_audit_submission_validation_error():
    """Verify 422 Unprocessable Entity on missing required schema fields."""
    invalid_payload = {
        "audit_id": "test_missing_fields",
        # missing run_id, annotator_id, is_violation, is_reward_hacked
    }
    res = client.post("/audit/labels", json=invalid_payload)
    assert res.status_code == 422


def test_audit_stats_endpoint():
    """Verify summary statistics for human audit workbench annotations."""
    res = client.get("/audit/stats")
    assert res.status_code == 200
    stats = res.json()
    assert "total_annotations" in stats
    assert "violation_count" in stats
    assert "reward_hack_count" in stats
    assert "inter_annotator_kappa" in stats
    assert stats["inter_annotator_kappa"] == 0.89


def test_security_headers_middleware():
    """Verify hardened HTTP defense-in-depth security headers are present on all responses."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert res.headers["x-xss-protection"] == "1; mode=block"
    assert res.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "accelerometer=()" in res.headers["permissions-policy"]


def test_cors_preflight_and_headers():
    """Verify CORS preflight handling and allowed origin enforcement."""
    res = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "GET" in res.headers.get("access-control-allow-methods", "")
