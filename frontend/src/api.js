const API_URL = "http://127.0.0.1:8000";

let refreshInFlight = null;

function storage() {
  return globalThis.localStorage;
}

export function getToken() {
  return storage().getItem("access_token");
}

export function setTokens(access, refresh) {
  storage().setItem("access_token", access);
  if (refresh) {
    storage().setItem("refresh_token", refresh);
  }
}

export function clearTokens() {
  storage().removeItem("access_token");
  storage().removeItem("refresh_token");
}

function decodeJwtPayload(token) {
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const padded = part.replace(/-/g, "+").replace(/_/g, "/");
    const padLength = (4 - (padded.length % 4)) % 4;
    const json = atob(padded + "=".repeat(padLength));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

function isAccessTokenExpired(token) {
  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") return false;
  return payload.exp * 1000 <= Date.now();
}

function failAuth() {
  clearTokens();
  const location = globalThis.window?.location;
  if (location && location.pathname !== "/login") {
    location.href = "/login";
  }
  throw new Error("Unauthorized");
}

async function doRefresh() {
  const refresh = storage().getItem("refresh_token");
  if (!refresh) {
    throw new Error("No refresh token");
  }
  const res = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) {
    throw new Error("Refresh failed");
  }
  const data = await res.json();
  if (!data.access_token) {
    throw new Error("Refresh failed");
  }
  setTokens(data.access_token, data.refresh_token);
  return data.access_token;
}

function refreshTokens() {
  if (!refreshInFlight) {
    refreshInFlight = doRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

export async function apiFetch(url, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  let token = getToken();
  if (token && isAccessTokenExpired(token)) {
    try {
      token = await refreshTokens();
    } catch {
      failAuth();
    }
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let res = await fetch(`${API_URL}${url}`, {
    ...options,
    headers,
  });

  if (res.status !== 401) {
    return res;
  }

  try {
    token = await refreshTokens();
  } catch {
    failAuth();
  }

  headers.Authorization = `Bearer ${token}`;
  res = await fetch(`${API_URL}${url}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    failAuth();
  }

  return res;
}

export async function logout() {
  const refresh = storage().getItem("refresh_token");
  try {
    if (refresh) {
      await fetch(`${API_URL}/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
    }
  } catch {
    // Local tokens are dropped even when the network call fails.
  } finally {
    clearTokens();
  }
}
