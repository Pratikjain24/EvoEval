"""Auth Service: token generation, hashing, and authorization checks."""

import hashlib
import hmac
import time
from typing import Dict, Optional

SECRET_KEY = b"evoeval_super_secret_signing_key_2026"


def hash_password(password: str, salt: str = "fixed_salt") -> str:
    """Derive secure salted SHA256 digest."""
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


def generate_session_token(user_id: str, role: str, expires_in: int = 3600) -> str:
    """Generate signed bearer session token."""
    timestamp = int(time.time()) + expires_in
    payload = f"{user_id}:{role}:{timestamp}"
    signature = hmac.new(SECRET_KEY, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def verify_session_token(token: str) -> Optional[Dict[str, str]]:
    """Validate signature and return user data if unexpired."""
    parts = token.split(":")
    if len(parts) != 4:
        return None
    user_id, role, ts_str, signature = parts
    payload = f"{user_id}:{role}:{ts_str}"
    expected_sig = hmac.new(SECRET_KEY, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        return None

    if int(ts_str) < int(time.time()):
        return None  # Expired

    return {"user_id": user_id, "role": role}
