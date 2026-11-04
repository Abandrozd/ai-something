from jose import jwt

from app.config import get_settings
from app.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)


def test_hash_password_not_equal_to_original():
    password = "mysecret"
    hashed = hash_password(password)
    assert hashed != password


def test_verify_correct_password():
    password = "mysecret"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_verify_wrong_password():
    hashed = hash_password("mysecret")
    assert verify_password("wrongpassword", hashed) is False


def _decode(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def test_access_token_is_marked_as_access():
    payload = _decode(create_access_token({"sub": "1", "role": "guest"}))
    assert payload["type"] == "access"
    assert payload["sub"] == "1"


def test_refresh_token_carries_type_and_version():
    payload = _decode(create_refresh_token({"sub": "1", "ver": 2}))
    assert payload["type"] == "refresh"
    assert payload["ver"] == 2