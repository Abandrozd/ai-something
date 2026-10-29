const API_URL = "http://127.0.0.1:8000";

export function getToken() {
  return localStorage.getItem("access_token");
}

export function setTokens(access, refresh) {
  localStorage.setItem("access_token", access);
  if (refresh) {
    localStorage.setItem("refresh_token", refresh);
  }
}

export function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

export async function apiFetch(url, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${url}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    clearTokens();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  return res;
}