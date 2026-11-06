function apiBase() {
  // Vite replaces import.meta.env.VITE_API_URL at build time. Node tests
  // have no env object, and the page then talks to the same origin via /api.
  if (typeof import.meta.env === "object" && import.meta.env) {
    return import.meta.env.VITE_API_URL || "/api";
  }
  return "/api";
}

export const API_URL = apiBase();

const TOKEN_KEYS = ["access_token", "refresh_token"];

let refreshInFlight = null;

function storage() {
  return globalThis.localStorage;
}

export function clearStoredTokens() {
  const store = storage();
  if (!store) return;
  for (const key of TOKEN_KEYS) {
    store.removeItem(key);
  }
}

function failAuth() {
  clearStoredTokens();
  const location = globalThis.window?.location;
  if (location && location.pathname !== "/login") {
    location.href = "/login";
  }
  throw new Error("Unauthorized");
}

async function doRefresh() {
  const res = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  if (!res.ok) {
    throw new Error("Refresh failed");
  }
}

function refreshSession() {
  if (!refreshInFlight) {
    refreshInFlight = doRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

export async function apiFetch(url, options = {}) {
  clearStoredTokens();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const request = () =>
    fetch(`${API_URL}${url}`, {
      ...options,
      headers,
      credentials: "include",
    });

  let res = await request();
  if (res.status !== 401) {
    return res;
  }

  try {
    await refreshSession();
  } catch {
    failAuth();
  }

  res = await request();
  if (res.status === 401) {
    failAuth();
  }
  return res;
}

export async function logout() {
  try {
    await fetch(`${API_URL}/auth/logout`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
  } catch {
    // Leftover localStorage keys are dropped even when the network call fails.
  } finally {
    clearStoredTokens();
  }
}
