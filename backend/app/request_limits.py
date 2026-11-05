"""Attempt limits and input caps that do not need Redis.

One process keeps the counters in memory. A second worker would not share
them, and a restart clears them. That is enough for this app: there is no
shared cache in the stack, and a new infrastructure service is not required.

Login is keyed by the direct client address and, when the form has a
username, by that username as well. Registration and refresh are keyed by
the direct client address only. The address is request.client, not a
forwarded header.

Every request that reaches the handler counts, including a later success.
The windows below still leave room for a person who mistypes a few times.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from fastapi import HTTPException, Request, status

from app.logger import get_logger

logger = get_logger(__name__)

# Argon2 runs on the whole password. Stop that work before it starts.
MAX_PASSWORD_LENGTH = 256
# A chat turn, not a document. Rejected before the model call.
MAX_MESSAGE_LENGTH = 4000

# 10 tries / 15 min per username: several mistypes, then a correct password.
LOGIN_USERNAME_LIMIT = 10
LOGIN_USERNAME_WINDOW_SECONDS = 15 * 60
# Wider than the username bucket so one shared address can still log in.
LOGIN_IP_LIMIT = 30
LOGIN_IP_WINDOW_SECONDS = 15 * 60

# One person registers once and may resubmit the form a few times.
REGISTER_IP_LIMIT = 10
REGISTER_IP_WINDOW_SECONDS = 15 * 60

# Access tokens last 30 minutes. Tabs and a retry fit under this.
REFRESH_IP_LIMIT = 30
REFRESH_IP_WINDOW_SECONDS = 15 * 60

TOO_MANY_ATTEMPTS = "Слишком много попыток. Повторите позже."

Clock = Callable[[], float]


def password_too_long_detail() -> str:
    return f"Пароль должен быть не длиннее {MAX_PASSWORD_LENGTH} символов"


class InProcessRateLimiter:
    def __init__(self, clock: Clock = time.monotonic) -> None:
        self._clock = clock
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def hit(self, key: str, limit: int, window_seconds: float) -> None:
        now = self._clock()
        limited = False
        with self._lock:
            recent = [
                stamp
                for stamp in self._hits.get(key, ())
                if now - stamp < window_seconds
            ]
            if len(recent) >= limit:
                self._hits[key] = recent
                limited = True
            else:
                recent.append(now)
                self._hits[key] = recent
        if limited:
            logger.warning("Превышен лимит попыток: %s", key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=TOO_MANY_ATTEMPTS,
                headers={"Retry-After": str(int(window_seconds))},
            )


limiter = InProcessRateLimiter()


def client_ip(request: Request) -> str:
    client = request.client
    if client is None or not client.host:
        return "unknown"
    return client.host


def _username_bucket(username: str | None) -> str | None:
    if username is None:
        return None
    stripped = username.strip()
    if not stripped:
        return None
    return stripped


def enforce_login_limit(request: Request, username: str | None) -> None:
    ip = client_ip(request)
    limiter.hit(f"login:ip:{ip}", LOGIN_IP_LIMIT, LOGIN_IP_WINDOW_SECONDS)
    bucket = _username_bucket(username)
    if bucket is not None:
        limiter.hit(
            f"login:user:{bucket}",
            LOGIN_USERNAME_LIMIT,
            LOGIN_USERNAME_WINDOW_SECONDS,
        )


def enforce_register_limit(request: Request) -> None:
    limiter.hit(
        f"register:ip:{client_ip(request)}",
        REGISTER_IP_LIMIT,
        REGISTER_IP_WINDOW_SECONDS,
    )


def enforce_refresh_limit(request: Request) -> None:
    limiter.hit(
        f"refresh:ip:{client_ip(request)}",
        REFRESH_IP_LIMIT,
        REFRESH_IP_WINDOW_SECONDS,
    )


def reject_long_password(password: str) -> None:
    if len(password) > MAX_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=password_too_long_detail(),
        )
