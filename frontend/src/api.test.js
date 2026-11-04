import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";

const memory = new Map();

globalThis.localStorage = {
  getItem: (key) => (memory.has(key) ? memory.get(key) : null),
  setItem: (key, value) => memory.set(key, String(value)),
  removeItem: (key) => memory.delete(key),
};
globalThis.window = { location: { href: "", pathname: "/profile" } };

const { apiFetch, clearTokens, getToken, logout, setTokens } = await import("./api.js");

function b64url(value) {
  const json = typeof value === "string" ? value : JSON.stringify(value);
  return btoa(json).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function makeJwt(payload) {
  return `${b64url({ alg: "HS256", typ: "JWT" })}.${b64url(payload)}.sig`;
}

function accessToken(expired) {
  const exp = Math.floor(Date.now() / 1000) + (expired ? -60 : 3600);
  return makeJwt({ sub: "1", type: "access", exp });
}

function jsonResponse(status, body) {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => body,
  };
}

beforeEach(() => {
  memory.clear();
  globalThis.window.location.href = "";
  globalThis.window.location.pathname = "/profile";
  clearTokens();
});

test("returns a successful response without calling refresh", async () => {
  setTokens(accessToken(false), "refresh-1");
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return jsonResponse(200, { username: "ada" });
  };

  const res = await apiFetch("/users/me");
  assert.equal(res.status, 200);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "http://127.0.0.1:8000/users/me");
  assert.equal(calls[0].options.headers.Authorization, `Bearer ${getToken()}`);
});

test("chat error statuses are not treated as an expired session", async () => {
  for (const status of [400, 404, 502]) {
    memory.clear();
    setTokens(accessToken(false), "refresh-1");
    const calls = [];
    globalThis.fetch = async (url, options) => {
      calls.push({ url, options });
      return jsonResponse(status, { detail: "nope" });
    };

    const res = await apiFetch("/chat", { method: "POST", body: "{\"message\":\"hi\"}" });
    assert.equal(res.status, status);
    assert.equal(calls.length, 1);
    assert.equal(getToken() !== null, true);
    assert.equal(globalThis.localStorage.getItem("refresh_token"), "refresh-1");
  }
});

test("refreshes an expired access token before the request", async () => {
  const expired = accessToken(true);
  setTokens(expired, "refresh-1");
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, body: options.body, authorization: options.headers.Authorization });
    if (url.endsWith("/auth/refresh")) {
      return jsonResponse(200, { access_token: "new-access", refresh_token: "refresh-2" });
    }
    return jsonResponse(200, { ok: true });
  };

  const res = await apiFetch("/users/me");
  assert.equal(res.status, 200);
  assert.equal(calls.length, 2);
  assert.equal(calls[0].url.endsWith("/auth/refresh"), true);
  assert.equal(JSON.parse(calls[0].body).refresh_token, "refresh-1");
  assert.equal(calls[1].authorization, "Bearer new-access");
  assert.equal(getToken(), "new-access");
  assert.equal(globalThis.localStorage.getItem("refresh_token"), "refresh-2");
});

test("retries a rejected request once after refresh", async () => {
  setTokens(accessToken(false), "refresh-1");
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, authorization: options.headers?.Authorization });
    if (url.endsWith("/auth/refresh")) {
      return jsonResponse(200, { access_token: "new-access", refresh_token: "refresh-2" });
    }
    if (calls.filter((call) => call.url.endsWith("/users/me")).length === 1) {
      return jsonResponse(401, { detail: "nope" });
    }
    return jsonResponse(200, { username: "ada" });
  };

  const res = await apiFetch("/users/me");
  assert.equal(res.status, 200);
  assert.deepEqual(
    calls.map((call) => call.url),
    [
      "http://127.0.0.1:8000/users/me",
      "http://127.0.0.1:8000/auth/refresh",
      "http://127.0.0.1:8000/users/me",
    ],
  );
  assert.equal(calls[2].authorization, "Bearer new-access");
});

test("sends the user to login when refresh fails", async () => {
  setTokens(accessToken(false), "refresh-1");
  const calls = [];
  globalThis.fetch = async (url) => {
    calls.push(url);
    return jsonResponse(401, { detail: "nope" });
  };

  await assert.rejects(apiFetch("/users/me"), /Unauthorized/);
  assert.deepEqual(calls, [
    "http://127.0.0.1:8000/users/me",
    "http://127.0.0.1:8000/auth/refresh",
  ]);
  assert.equal(getToken(), null);
  assert.equal(globalThis.localStorage.getItem("refresh_token"), null);
  assert.equal(globalThis.window.location.href, "/login");
});

test("does not retry forever when the new access token is also rejected", async () => {
  setTokens(accessToken(false), "refresh-1");
  let refreshCalls = 0;
  let meCalls = 0;
  globalThis.fetch = async (url) => {
    if (url.endsWith("/auth/refresh")) {
      refreshCalls += 1;
      return jsonResponse(200, { access_token: "new-access", refresh_token: "refresh-2" });
    }
    meCalls += 1;
    return jsonResponse(401, { detail: "nope" });
  };

  await assert.rejects(apiFetch("/users/me"), /Unauthorized/);
  assert.equal(meCalls, 2);
  assert.equal(refreshCalls, 1);
  assert.equal(globalThis.window.location.href, "/login");
  assert.equal(getToken(), null);
});

test("one refresh serves concurrent 401s", async () => {
  setTokens(accessToken(false), "refresh-1");
  let refreshCalls = 0;
  globalThis.fetch = async (url) => {
    if (url.endsWith("/auth/refresh")) {
      refreshCalls += 1;
      return jsonResponse(200, { access_token: "new-access", refresh_token: "refresh-2" });
    }
    const token = globalThis.localStorage.getItem("access_token");
    if (token === "new-access") {
      return jsonResponse(200, { ok: true });
    }
    return jsonResponse(401, { detail: "nope" });
  };

  const [first, second] = await Promise.all([
    apiFetch("/users/me"),
    apiFetch("/conversations"),
  ]);
  assert.equal(first.status, 200);
  assert.equal(second.status, 200);
  assert.equal(refreshCalls, 1);
});

test("logout posts the refresh token and drops both tokens", async () => {
  setTokens(accessToken(true), "refresh-1");
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, body: options.body, authorization: options.headers.Authorization });
    return jsonResponse(200, { message: "Вы успешно вышли из системы" });
  };

  await logout();
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "http://127.0.0.1:8000/auth/logout");
  assert.equal(JSON.parse(calls[0].body).refresh_token, "refresh-1");
  assert.equal(calls[0].authorization, undefined);
  assert.equal(getToken(), null);
  assert.equal(globalThis.localStorage.getItem("refresh_token"), null);
});

test("logout drops tokens when the revoke request fails", async () => {
  setTokens(accessToken(false), "refresh-1");
  globalThis.fetch = async () => {
    throw new Error("offline");
  };

  await logout();
  assert.equal(getToken(), null);
  assert.equal(globalThis.localStorage.getItem("refresh_token"), null);
});
