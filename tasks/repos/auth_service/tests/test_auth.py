from solution import generate_session_token, hash_password, verify_session_token


def test_password_hashing():
    h1 = hash_password("secret123")
    h2 = hash_password("secret123")
    assert h1 == h2
    assert len(h1) == 64


def test_session_token_valid():
    token = generate_session_token("usr_42", "admin", expires_in=100)
    data = verify_session_token(token)
    assert data is not None
    assert data["user_id"] == "usr_42"
    assert data["role"] == "admin"


def test_session_token_tampered():
    token = generate_session_token("usr_42", "user", expires_in=100)
    tampered = token.replace("user", "admin")
    assert verify_session_token(tampered) is None
