(function () {
  const API = "/api";
  const TOKEN_KEY = "portfolio_token";

  let token = localStorage.getItem(TOKEN_KEY);

  function getToken() {
    return token;
  }

  function setToken(value) {
    token = value;
    if (value) {
      localStorage.setItem(TOKEN_KEY, value);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  }

  function authHeaders(extra = {}) {
    const headers = { ...extra };
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    return headers;
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: authHeaders(options.headers || {}),
    });
    if (response.status === 401) {
      setToken(null);
      throw new Error("SESSION_EXPIRED");
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const detail = body.detail;
      const message = Array.isArray(detail)
        ? detail.map((item) => item.msg).join(", ")
        : detail || response.statusText;
      throw new Error(message);
    }
    if (response.status === 204) {
      return null;
    }
    return response.json();
  }

  window.PortfolioApi = {
    API,
    getToken,
    setToken,
    authHeaders,
    fetchJson,
  };
})();
