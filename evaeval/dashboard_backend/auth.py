"""Authentication and Access Control for EvoEval Dashboard & Public Leaderboard.

Provides:
1. Public Read vs. Protected Read Access (configurable via DASHBOARD_REQUIRE_AUTH).
2. Strict Write & Mutation Authentication (X-API-Key or Bearer token for labels, runs).
3. Constant-time token verification against timing attacks.
"""

from __future__ import annotations
import hmac
import os
from typing import Optional
from fastapi import Header, HTTPException, Query, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security_bearer = HTTPBearer(auto_error=False)

DEFAULT_DEV_KEY = "evoeval-dev-key-change-in-production"


def get_configured_api_key() -> str:
    """Retrieve configured admin API key from environment."""
    return os.environ.get("EVOEVAL_API_KEY", DEFAULT_DEV_KEY)


def is_auth_required_for_read() -> bool:
    """Check if all endpoints (including public leaderboard) require authentication."""
    val = os.environ.get("DASHBOARD_REQUIRE_AUTH", "false").lower()
    return val in ("true", "1", "yes")


def extract_credential(
    request: Request,
    x_api_key: Optional[str] = None,
    bearer: Optional[HTTPAuthorizationCredentials] = None,
    api_key_query: Optional[str] = None,
) -> Optional[str]:
    """Extract API key from header, bearer token, or query parameter."""
    if x_api_key:
        return x_api_key.strip()
    if bearer and bearer.credentials:
        return bearer.credentials.strip()
    # Check headers directly
    header_key = request.headers.get("X-API-Key")
    if header_key:
        return header_key.strip()
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    if api_key_query:
        return api_key_query.strip()
    q_key = request.query_params.get("api_key")
    if q_key:
        return q_key.strip()
    return None


def verify_token(provided_token: Optional[str]) -> bool:
    """Constant-time token verification to mitigate timing analysis attacks."""
    if not provided_token:
        return False
    expected_token = get_configured_api_key()
    return hmac.compare_digest(provided_token.encode("utf-8"), expected_token.encode("utf-8"))


async def require_read_access(request: Request) -> bool:
    """Dependency for read-only endpoints (e.g. leaderboard, runs, cycles).

    If DASHBOARD_REQUIRE_AUTH=false (default for public leaderboard), access is permitted.
    If DASHBOARD_REQUIRE_AUTH=true, valid API key or Bearer token is strictly required.
    """
    if not is_auth_required_for_read():
        return True

    token = extract_credential(request)
    if not verify_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Provide valid X-API-Key or Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True


def is_write_auth_enforced() -> bool:
    """Check if mutating endpoints strictly enforce authentication.

    True when in production/public release:
    - DASHBOARD_REQUIRE_AUTH is true, or
    - DASHBOARD_REQUIRE_WRITE_AUTH is true, or
    - EVOEVAL_API_KEY is explicitly configured in environment.
    """
    if is_auth_required_for_read():
        return True
    if os.environ.get("DASHBOARD_REQUIRE_WRITE_AUTH", "false").lower() in ("true", "1", "yes"):
        return True
    if "EVOEVAL_API_KEY" in os.environ and os.environ["EVOEVAL_API_KEY"]:
        return True
    return False


async def require_write_access(request: Request) -> bool:
    """Dependency for mutating endpoints (e.g. audit label submission, run ingestion).

    Always enforces authentication in hardened/public mode.
    """
    if not is_write_auth_enforced():
        return True

    token = extract_credential(request)
    if not verify_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mutation denied: Valid administrative X-API-Key or Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True
