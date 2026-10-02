"""Unit and integration tests for Dashboard Hardening: Authentication, Rate Limiting, and Container Security."""

from __future__ import annotations
import os
from pathlib import Path
import pytest
import yaml
from fastapi.testclient import TestClient

from sage.dashboard_backend.auth import (
    DEFAULT_DEV_KEY,
    get_configured_api_key,
    is_auth_required_for_read,
    verify_token,
)
from sage.dashboard_backend.main import app
from sage.dashboard_backend.rate_limiter import SlidingWindowRateLimiter, get_global_rate_limiter


@pytest.fixture(autouse=True)
def reset_env_and_rate_limits():
    """Ensure clean environment and rate limiter state before each test."""
    orig_auth = os.environ.get("DASHBOARD_REQUIRE_AUTH")
    orig_key = os.environ.get("SAGE_API_KEY")
    orig_disable = os.environ.get("SAGE_DISABLE_RATE_LIMIT")
    orig_override = os.environ.get("RATE_LIMIT_OVERRIDE")

    # Clear rate limiter history
    get_global_rate_limiter().reset()

    yield

    if orig_auth is not None:
        os.environ["DASHBOARD_REQUIRE_AUTH"] = orig_auth
    else:
        os.environ.pop("DASHBOARD_REQUIRE_AUTH", None)

    if orig_key is not None:
        os.environ["SAGE_API_KEY"] = orig_key
    else:
        os.environ.pop("SAGE_API_KEY", None)

    if orig_disable is not None:
        os.environ["SAGE_DISABLE_RATE_LIMIT"] = orig_disable
    else:
        os.environ.pop("SAGE_DISABLE_RATE_LIMIT", None)

    if orig_override is not None:
        os.environ["RATE_LIMIT_OVERRIDE"] = orig_override
    else:
        os.environ.pop("RATE_LIMIT_OVERRIDE", None)

    get_global_rate_limiter().reset()


def test_public_leaderboard_read_access_default():
    """By default, public leaderboard and health endpoints allow unauthenticated read."""
    os.environ["DASHBOARD_REQUIRE_AUTH"] = "false"
    os.environ["SAGE_DISABLE_RATE_LIMIT"] = "true"
    client = TestClient(app)

    # Health check
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # Leaderboard read
    res = client.get("/leaderboard")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert len(res.json()) >= 6


def test_protected_dashboard_read_requires_auth():
    """When DASHBOARD_REQUIRE_AUTH=true, read access requires valid authentication."""
    os.environ["DASHBOARD_REQUIRE_AUTH"] = "true"
    os.environ["SAGE_API_KEY"] = "super-secret-test-token-12345"
    os.environ["SAGE_DISABLE_RATE_LIMIT"] = "true"
    client = TestClient(app)

    # Missing credentials -> 401
    res = client.get("/leaderboard")
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]

    # Invalid credential -> 401
    res = client.get("/leaderboard", headers={"X-API-Key": "wrong-key"})
    assert res.status_code == 401

    # Valid X-API-Key -> 200
    res = client.get("/leaderboard", headers={"X-API-Key": "super-secret-test-token-12345"})
    assert res.status_code == 200

    # Valid Authorization: Bearer -> 200
    res = client.get("/leaderboard", headers={"Authorization": "Bearer super-secret-test-token-12345"})
    assert res.status_code == 200


def test_write_endpoints_always_require_auth():
    """Mutating write endpoints (POST /audit/labels) always require valid API key."""
    os.environ["DASHBOARD_REQUIRE_AUTH"] = "false"  # Even if public reads allowed
    os.environ["SAGE_API_KEY"] = "audit-admin-token-777"
    os.environ["SAGE_DISABLE_RATE_LIMIT"] = "true"
    client = TestClient(app)

    payload = {
        "audit_id": "test_audit_001",
        "run_id": "test_run",
        "annotator_id": "human_01",
        "is_violation": False,
        "is_reward_hacked": False,
        "failure_severity": "none",
        "notes": "Valid safe trace",
    }

    # Unauthenticated attempt -> 401
    res = client.post("/audit/labels", json=payload)
    assert res.status_code == 401
    assert "Mutation denied" in res.json()["detail"]

    # Valid authentication -> 200
    res = client.post(
        "/audit/labels",
        json=payload,
        headers={"X-API-Key": "audit-admin-token-777"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_sliding_window_rate_limiter():
    """Verify rate limiter blocks client IP after exceeding threshold and sets headers."""
    limiter = SlidingWindowRateLimiter(default_limit=3, window_seconds=60)
    test_ip = "198.51.100.42"

    # First 3 hits should succeed
    for i in range(3):
        is_limited, rem, reset_secs, limit = limiter.is_rate_limited(test_ip)
        assert not is_limited
        assert rem == (2 - i)
        assert limit == 3

    # 4th hit should be rate limited
    is_limited, rem, reset_secs, limit = limiter.is_rate_limited(test_ip)
    assert is_limited
    assert rem == 0
    assert reset_secs > 0


def test_rate_limiter_http_429_integration():
    """Verify FastAPI endpoint returns HTTP 429 when client exceeds limit."""
    os.environ["SAGE_DISABLE_RATE_LIMIT"] = "false"
    os.environ["RATE_LIMIT_OVERRIDE"] = "2"
    limiter = get_global_rate_limiter()
    limiter.reset()

    client = TestClient(app)

    # Hit 1 -> 200
    res1 = client.get("/leaderboard")
    assert res1.status_code == 200
    assert "X-RateLimit-Remaining" in res1.headers

    # Hit 2 -> 200
    res2 = client.get("/leaderboard")
    assert res2.status_code == 200

    # Hit 3 -> 429 Too Many Requests
    res3 = client.get("/leaderboard")
    assert res3.status_code == 429
    assert "Rate limit exceeded" in res3.json()["detail"]
    assert "Retry-After" in res3.headers
    assert int(res3.headers["Retry-After"]) >= 1


def test_security_headers_middleware():
    """Verify all responses include defense-in-depth security headers."""
    os.environ["SAGE_DISABLE_RATE_LIMIT"] = "true"
    client = TestClient(app)

    res = client.get("/health")
    assert res.status_code == 200
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["X-XSS-Protection"] == "1; mode=block"
    assert res.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_docker_compose_hardening_specification():
    """Audit docker-compose.yml for strict container hardening rules."""
    repo_root = Path(__file__).resolve().parent.parent
    compose_file = repo_root / "docker" / "docker-compose.yml"
    assert compose_file.exists(), "docker-compose.yml must exist"

    with open(compose_file, "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)

    services = compose.get("services", {})
    assert "backend" in services
    assert "frontend" in services

    # 1. Audit backend hardening
    backend = services["backend"]
    assert backend.get("restart") == "unless-stopped", "Backend must have restart policy"
    assert backend.get("user") == "1000:1000", "Backend must run as unprivileged user"
    assert "no-new-privileges:true" in backend.get("security_opt", []), "Backend must set no-new-privileges"
    assert "ALL" in backend.get("cap_drop", []), "Backend must drop ALL capabilities"

    # Backend resources
    b_limits = backend.get("deploy", {}).get("resources", {}).get("limits", {})
    assert "cpus" in b_limits, "Backend must specify CPU limit"
    assert "memory" in b_limits, "Backend must specify memory limit"
    assert "pids" in b_limits, "Backend must specify pids limit"

    # Backend healthcheck
    assert "healthcheck" in backend, "Backend must have healthcheck"

    # 2. Audit frontend hardening
    frontend = services["frontend"]
    assert frontend.get("restart") == "unless-stopped", "Frontend must have restart policy"
    assert frontend.get("user") == "1000:1000", "Frontend must run as unprivileged user"
    assert "no-new-privileges:true" in frontend.get("security_opt", []), "Frontend must set no-new-privileges"
    assert "ALL" in frontend.get("cap_drop", []), "Frontend must drop ALL capabilities"

    # Frontend resources
    f_limits = frontend.get("deploy", {}).get("resources", {}).get("limits", {})
    assert "cpus" in f_limits, "Frontend must specify CPU limit"
    assert "memory" in f_limits, "Frontend must specify memory limit"

    # Frontend healthcheck
    assert "healthcheck" in frontend, "Frontend must have healthcheck"

    # 3. Dedicated internal bridge network
    assert "networks" in compose
    assert "sage-net" in compose["networks"] or "evo-net" in compose["networks"]
