import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _register(client, username="cookieuser"):
    created = await client.post("/users/", json={
        "username": username,
        "email": f"{username}@example.com",
        "password": "password123",
    })
    assert created.status_code == 201, created.text


def _set_cookie_blob(response) -> str:
    return "\n".join(response.headers.get_list("set-cookie"))


def _assert_browser_cookies(response, *, secure: bool):
    blob = _set_cookie_blob(response)
    lowered = blob.lower()
    assert "access_token=" in blob
    assert "refresh_token=" in blob
    assert lowered.count("httponly") >= 2
    assert lowered.count("samesite=lax") >= 2
    assert "samesite=none" not in lowered
    if secure:
        assert lowered.count("secure") >= 2
    else:
        assert "secure" not in lowered
    access = response.cookies["access_token"]
    refresh = response.cookies["refresh_token"]
    assert access not in response.text
    assert refresh not in response.text
    assert response.json() == {"token_type": "bearer"}


@pytest.mark.asyncio
async def test_login_hides_tokens_from_javascript(client):
    await _register(client)
    response = await client.post("/auth/login", data={
        "username": "cookieuser",
        "password": "password123",
    })
    assert response.status_code == 200
    _assert_browser_cookies(response, secure=False)

    me = await client.get("/users/me")
    assert me.status_code == 200
    assert me.json()["username"] == "cookieuser"
    assert me.request.headers.get("authorization") is None


@pytest.mark.asyncio
async def test_failed_login_does_not_set_cookies(client):
    response = await client.post("/auth/login", data={
        "username": "missing",
        "password": "password123",
    })
    assert response.status_code == 401
    assert response.headers.get_list("set-cookie") == []


@pytest.mark.asyncio
async def test_refresh_and_logout_use_cookies(client):
    await _register(client, "cookierefresh")
    login = await client.post("/auth/login", data={
        "username": "cookierefresh",
        "password": "password123",
    })
    previous_refresh = login.cookies["refresh_token"]
    previous_access = login.cookies["access_token"]

    refreshed = await client.post("/auth/refresh")
    assert refreshed.status_code == 200
    _assert_browser_cookies(refreshed, secure=False)
    assert refreshed.cookies["refresh_token"] != previous_refresh

    me = await client.get("/users/me")
    assert me.status_code == 200

    stale = await client.get("/users/me", headers={
        "Authorization": f"Bearer {previous_access}",
    })
    assert stale.status_code == 401

    logout = await client.post("/auth/logout")
    assert logout.status_code == 200
    assert logout.json()["message"] == "Вы успешно вышли из системы"
    cleared = _set_cookie_blob(logout).lower()
    assert "max-age=0" in cleared
    assert client.cookies.get("access_token") in (None, "")
    assert client.cookies.get("refresh_token") in (None, "")

    after = await client.get("/users/me")
    assert after.status_code == 401
    reused = await client.post("/auth/refresh", json={"refresh_token": previous_refresh})
    assert reused.status_code == 401
    current = await client.post(
        "/auth/refresh",
        json={"refresh_token": refreshed.cookies["refresh_token"]},
    )
    assert current.status_code == 401


@pytest.mark.asyncio
async def test_refresh_cookie_is_not_accepted_as_access(client):
    await _register(client, "cookiereject")
    login = await client.post("/auth/login", data={
        "username": "cookiereject",
        "password": "password123",
    })
    assert login.status_code == 200
    client.cookies.delete("access_token")

    me = await client.get("/users/me")
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_https_login_marks_cookies_secure(client):
    await _register(client, "securecookie")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://localhost") as https:
        response = await https.post("/auth/login", data={
            "username": "securecookie",
            "password": "password123",
        })
    assert response.status_code == 200
    _assert_browser_cookies(response, secure=True)


@pytest.mark.asyncio
async def test_cors_allows_only_the_frontend_origin(client):
    allowed = await client.get("/", headers={"Origin": "http://localhost:5173"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert allowed.headers["access-control-allow-credentials"] == "true"

    preflight = await client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert preflight.headers["access-control-allow-credentials"] == "true"

    blocked = await client.get("/", headers={"Origin": "https://evil.example"})
    assert blocked.headers.get("access-control-allow-origin") in (None, "")

    evil_preflight = await client.options(
        "/auth/login",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    echoed = evil_preflight.headers.get("access-control-allow-origin")
    assert echoed in (None, "")
    assert echoed != "*"
