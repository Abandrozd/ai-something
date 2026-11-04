import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";

const memory = new Map();

globalThis.localStorage = {
  getItem: (key) => (memory.has(key) ? memory.get(key) : null),
  setItem: (key, value) => memory.set(key, String(value)),
  removeItem: (key) => memory.delete(key),
};
globalThis.window = { location: { href: "", pathname: "/profile" } };

const { apiFetch, clearStoredTokens, logout } = await import("./api.js");

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
});

test("sends cookies and does not attach a leftover localStorage token", async () => {
  memory.set("access_token", "stolen-access");
  memory.set("refresh_token", "stolen-refresh");
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return jsonResponse(200, { username: "ada" });
  };

  const res = await apiFetch("/users/me");
  assert.equal(res.status, 200);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "/api/users/me");
  assert.equal(calls[0].options.credentials, "include");
  assert.equal(calls[0].options.headers.Authorization, undefined);
  assert.equal(memory.has("access_token"), false);
  assert.equal(memory.has("refresh_token"), false);
});

test("chat error statuses are not treated as an expired session", async () => {
  for (const status of [400, 404, 502]) {
    const calls = [];
    globalThis.fetch = async (url, options) => {
      calls.push({ url, options });
      return jsonResponse(status, { detail: "nope" });
    };

    const res = await apiFetch("/chat", { method: "POST", body: "{\"message\":\"hi\"}" });
    assert.equal(res.status, status);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].options.credentials, "include");
    assert.equal(calls[0].options.headers.Authorization, undefined);
  }
});

test("retries a rejected request once after a cookie refresh", async () => {
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({
      url,
      credentials: options.credentials,
      authorization: options.headers?.Authorization,
      body: options.body,
    });
    if (url.endsWith("/auth/refresh")) {
      return jsonResponse(200, { token_type: "bearer" });
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
    ["/api/users/me", "/api/auth/refresh", "/api/users/me"],
  );
  assert.equal(calls[1].credentials, "include");
  assert.equal(calls[1].body, "{}");
  assert.equal(calls[1].body.includes("refresh_token"), false);
  assert.equal(calls[2].authorization, undefined);
  assert.equal(calls[2].credentials, "include");
});

test("sends the user to login when refresh fails", async () => {
  memory.set("access_token", "leftover");
  const calls = [];
  globalThis.fetch = async (url) => {
    calls.push(url);
    return jsonResponse(401, { detail: "nope" });
  };

  await assert.rejects(apiFetch("/users/me"), /Unauthorized/);
  assert.deepEqual(calls, ["/api/users/me", "/api/auth/refresh"]);
  assert.equal(memory.has("access_token"), false);
  assert.equal(globalThis.window.location.href, "/login");
});

test("does not retry forever when the new session is also rejected", async () => {
  let refreshCalls = 0;
  let meCalls = 0;
  globalThis.fetch = async (url) => {
    if (url.endsWith("/auth/refresh")) {
      refreshCalls += 1;
      return jsonResponse(200, { token_type: "bearer" });
    }
    meCalls += 1;
    return jsonResponse(401, { detail: "nope" });
  };

  await assert.rejects(apiFetch("/users/me"), /Unauthorized/);
  assert.equal(meCalls, 2);
  assert.equal(refreshCalls, 1);
  assert.equal(globalThis.window.location.href, "/login");
});

test("one refresh serves concurrent 401s", async () => {
  let refreshCalls = 0;
  let phase = "stale";
  globalThis.fetch = async (url) => {
    if (url.endsWith("/auth/refresh")) {
      refreshCalls += 1;
      phase = "fresh";
      return jsonResponse(200, { token_type: "bearer" });
    }
    if (phase === "stale") {
      return jsonResponse(401, { detail: "nope" });
    }
    return jsonResponse(200, { ok: true });
  };

  const [first, second] = await Promise.all([
    apiFetch("/users/me"),
    apiFetch("/conversations"),
  ]);
  assert.equal(first.status, 200);
  assert.equal(second.status, 200);
  assert.equal(refreshCalls, 1);
});

test("logout posts the cookie session and drops leftover token keys", async () => {
  memory.set("access_token", "leftover-access");
  memory.set("refresh_token", "leftover-refresh");
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({
      url,
      body: options.body,
      authorization: options.headers.Authorization,
      credentials: options.credentials,
    });
    return jsonResponse(200, { message: "Вы успешно вышли из системы" });
  };

  await logout();
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "/api/auth/logout");
  assert.equal(calls[0].credentials, "include");
  assert.equal(calls[0].body, "{}");
  assert.equal(calls[0].body.includes("refresh_token"), false);
  assert.equal(calls[0].authorization, undefined);
  assert.equal(memory.has("access_token"), false);
  assert.equal(memory.has("refresh_token"), false);
});

test("logout drops leftover keys when the revoke request fails", async () => {
  memory.set("access_token", "leftover-access");
  memory.set("refresh_token", "leftover-refresh");
  globalThis.fetch = async () => {
    throw new Error("offline");
  };

  await logout();
  assert.equal(memory.has("access_token"), false);
  assert.equal(memory.has("refresh_token"), false);
});

test("clearStoredTokens removes both leftover keys", () => {
  memory.set("access_token", "a");
  memory.set("refresh_token", "r");
  memory.set("other", "keep");
  clearStoredTokens();
  assert.equal(memory.has("access_token"), false);
  assert.equal(memory.has("refresh_token"), false);
  assert.equal(memory.get("other"), "keep");
});
