(function () {
  const api = window.PortfolioApi;

  function showError(message) {
    const targets = [document.getElementById("auth-error"), document.getElementById("error")];
    for (const el of targets) {
      if (!el) continue;
      el.textContent = message;
      el.hidden = !message;
    }
  }

  function setAuthenticated(isAuthenticated) {
    document.getElementById("auth-section").hidden = isAuthenticated;
    document.getElementById("app-section").hidden = !isAuthenticated;
    const actionsEl = document.getElementById("top-bar-actions");
    if (isAuthenticated) {
      actionsEl.removeAttribute("hidden");
    } else {
      actionsEl.setAttribute("hidden", "");
    }
  }

  function logout() {
    api.setToken(null);
    setAuthenticated(false);
    window.ManagementView.resetManagement();
  }

  async function login(event) {
    event.preventDefault();
    showError("");
    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-password").value;
    const body = new URLSearchParams({ username: email, password });

    const response = await fetch(`${api.API}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || "Login failed");
    }

    const data = await response.json();
    api.setToken(data.access_token);
    await bootstrapApp();
  }

  async function register(event) {
    event.preventDefault();
    showError("");
    const email = document.getElementById("register-email").value.trim();
    const password = document.getElementById("register-password").value;

    await api.fetchJson(`${api.API}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    document.getElementById("login-email").value = email;
    document.getElementById("login-password").value = password;
    await login(new Event("submit"));
  }

  async function bootstrapApp() {
    await api.fetchJson(`${api.API}/auth/me`);
    setAuthenticated(true);
    await window.ManagementView.loadManagement();
  }

  async function addFund(event) {
    event.preventDefault();
    showError("");
    const input = document.getElementById("isin-input");
    const isin = input.value.trim().toUpperCase();
    if (!isin) {
      return;
    }

    input.disabled = true;
    try {
      await api.fetchJson(`${api.API}/funds`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ isin }),
      });
      input.value = "";
      await window.ManagementView.loadManagement();
    } catch (err) {
      showError(err.message);
    } finally {
      input.disabled = false;
      input.focus();
    }
  }

  document.getElementById("login-form").addEventListener("submit", (event) => {
    login(event).catch((err) => showError(err.message));
  });
  document.getElementById("register-form").addEventListener("submit", (event) => {
    register(event).catch((err) => showError(err.message));
  });
  document.getElementById("logout").addEventListener("click", (event) => {
    event.preventDefault();
    logout();
  });
  document.getElementById("add-fund-form").addEventListener("submit", (event) => {
    addFund(event).catch((err) => showError(err.message));
  });

  if (api.getToken()) {
    bootstrapApp().catch((err) => {
      if (err.message === "SESSION_EXPIRED") {
        logout();
        showError("Session expired. Please log in again.");
        return;
      }
      logout();
      showError(err.message);
    });
  }
})();
