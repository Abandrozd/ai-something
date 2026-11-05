import pytest
from fastapi import HTTPException

from app.request_limits import (
    LOGIN_IP_LIMIT,
    LOGIN_IP_WINDOW_SECONDS,
    LOGIN_USERNAME_LIMIT,
    LOGIN_USERNAME_WINDOW_SECONDS,
    MAX_MESSAGE_LENGTH,
    MAX_PASSWORD_LENGTH,
    REFRESH_IP_LIMIT,
    REFRESH_IP_WINDOW_SECONDS,
    REGISTER_IP_LIMIT,
    REGISTER_IP_WINDOW_SECONDS,
    TOO_MANY_ATTEMPTS,
    enforce_login_limit,
    enforce_refresh_limit,
    enforce_register_limit,
    limiter,
)


class _Client:
    def __init__(self, host):
        self.host = host


class _Request:
    def __init__(self, host):
        self.client = _Client(host)


def test_documented_limits():
    assert MAX_PASSWORD_LENGTH == 256
    assert MAX_MESSAGE_LENGTH == 4000
    assert LOGIN_USERNAME_LIMIT == 10
    assert LOGIN_USERNAME_WINDOW_SECONDS == 15 * 60
    assert LOGIN_IP_LIMIT == 30
    assert LOGIN_IP_WINDOW_SECONDS == 15 * 60
    assert REGISTER_IP_LIMIT == 10
    assert REGISTER_IP_WINDOW_SECONDS == 15 * 60
    assert REFRESH_IP_LIMIT == 30
    assert REFRESH_IP_WINDOW_SECONDS == 15 * 60


def test_login_username_bucket_is_shared_across_addresses():
    home = _Request("198.51.100.10")
    cafe = _Request("198.51.100.11")
    for _ in range(LOGIN_USERNAME_LIMIT):
        enforce_login_limit(home, "alice")

    with pytest.raises(HTTPException) as blocked:
        enforce_login_limit(cafe, "alice")

    assert blocked.value.status_code == 429
    assert blocked.value.detail == TOO_MANY_ATTEMPTS
    assert blocked.value.headers["Retry-After"] == str(LOGIN_USERNAME_WINDOW_SECONDS)
    enforce_login_limit(home, "bob")


def test_blank_username_does_not_open_a_username_bucket():
    request = _Request("198.51.100.20")
    for _ in range(LOGIN_USERNAME_LIMIT + 1):
        enforce_login_limit(request, "   ")
    enforce_login_limit(request, None)
    enforce_login_limit(request, "alice")


def test_login_ip_bucket_is_separate_from_register_and_refresh():
    request = _Request("198.51.100.30")
    for _ in range(LOGIN_IP_LIMIT):
        enforce_login_limit(request, None)

    with pytest.raises(HTTPException) as blocked:
        enforce_login_limit(request, None)
    assert blocked.value.status_code == 429

    enforce_register_limit(request)
    enforce_refresh_limit(request)


def test_attempt_window_expires(monkeypatch):
    now = {"t": 1_000.0}
    monkeypatch.setattr(limiter, "_clock", lambda: now["t"])
    request = _Request("198.51.100.40")
    for _ in range(LOGIN_USERNAME_LIMIT):
        enforce_login_limit(request, "alice")

    with pytest.raises(HTTPException):
        enforce_login_limit(request, "alice")

    now["t"] += LOGIN_USERNAME_WINDOW_SECONDS
    enforce_login_limit(request, "alice")
