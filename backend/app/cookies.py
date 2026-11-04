from fastapi import Request, Response

from app.config import get_settings

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"

settings = get_settings()


def request_is_https(request: Request) -> bool:
    """Secure cookies only when the request itself is HTTPS.

    localhost over HTTP stays non-Secure. The scheme of the request is the
    signal; we do not treat loopback as HTTPS.
    """
    return request.url.scheme == "https"


def _write(response: Response, key: str, value: str, max_age: int, secure: bool) -> None:
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age,
        path="/",
        secure=secure,
        httponly=True,
        samesite="lax",
    )


def set_auth_cookies(
    response: Response,
    request: Request,
    access_token: str,
    refresh_token: str,
) -> None:
    secure = request_is_https(request)
    _write(
        response,
        ACCESS_COOKIE,
        access_token,
        settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure,
    )
    _write(
        response,
        REFRESH_COOKIE,
        refresh_token,
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        secure,
    )


def clear_auth_cookies(response: Response, request: Request) -> None:
    secure = request_is_https(request)
    response.delete_cookie(
        ACCESS_COOKIE, path="/", secure=secure, httponly=True, samesite="lax",
    )
    response.delete_cookie(
        REFRESH_COOKIE, path="/", secure=secure, httponly=True, samesite="lax",
    )
