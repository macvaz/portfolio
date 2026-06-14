const API = "/api";
const TOKEN_KEY = "portfolio_token";

let funds = [];
let weights = {};
let token = localStorage.getItem(TOKEN_KEY);

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
    logout();
    throw new Error("Session expired. Please log in again.");
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

function showError(message) {
  const el = document.getElementById("error");
  el.textContent = message;
  el.hidden = !message;
}

function setAuthenticated(isAuthenticated, email = "") {
  document.getElementById("auth-section").hidden = isAuthenticated;
  document.getElementById("app-section").hidden = !isAuthenticated;
  document.getElementById("user-email").textContent = email;
}

function logout() {
  token = null;
  localStorage.removeItem(TOKEN_KEY);
  setAuthenticated(false);
  funds = [];
  weights = {};
}

function getPositionsFromWeights() {
  return Object.entries(weights)
    .filter(([, weight]) => weight > 0)
    .map(([isin, weighted_assets]) => ({ isin, weighted_assets }));
}

function updateWeightTotal() {
  const total = Object.values(weights).reduce((sum, weight) => sum + weight, 0);
  const totalEl = document.getElementById("weight-total");
  const positions = getPositionsFromWeights();
  totalEl.textContent = `Total weight: ${total.toFixed(2)}`;
  totalEl.classList.toggle("weight-invalid", Math.abs(total - 1) > 0.01);
  document.getElementById("generate-report").disabled =
    funds.length === 0 || positions.length === 0 || Math.abs(total - 1) > 0.01;
}

function renderFunds() {
  const list = document.getElementById("fund-list");
  const empty = document.getElementById("funds-empty");

  if (funds.length === 0) {
    list.innerHTML = "";
    empty.hidden = false;
    updateWeightTotal();
    return;
  }

  empty.hidden = true;
  list.innerHTML = funds
    .map((fund) => {
      const weight = weights[fund.isin] ?? "";
      return `
      <li class="fund-row" data-isin="${fund.isin}">
        <div class="fund-meta">
          <strong>${fund.isin}</strong>
          <span>${fund.name}</span>
          <span>MS ID: ${fund.fund_id}</span>
        </div>
        <div class="fund-actions">
          <label class="weight-label">
            <span>Weight</span>
            <input
              type="number"
              class="weight-input"
              min="0"
              max="1"
              step="0.01"
              placeholder="0.00"
              value="${weight === "" ? "" : weight}"
            />
          </label>
          <button type="button" class="danger remove-fund">Remove</button>
        </div>
      </li>`;
    })
    .join("");

  list.querySelectorAll(".fund-row").forEach((row) => {
    const isin = row.dataset.isin;
    const input = row.querySelector(".weight-input");
    input.addEventListener("input", () => {
      const value = input.value.trim();
      if (value === "") {
        delete weights[isin];
      } else {
        weights[isin] = Number(value);
      }
      updateWeightTotal();
    });
    row.querySelector(".remove-fund").addEventListener("click", () => {
      deleteFund(isin);
    });
  });

  updateWeightTotal();
}

async function loadFundsAndPortfolio() {
  const [fundsData, portfolioData] = await Promise.all([
    fetchJson(`${API}/funds`),
    fetchJson(`${API}/portfolio`),
  ]);
  funds = fundsData;
  weights = {};
  for (const position of portfolioData) {
    weights[position.isin] = position.weighted_assets;
  }
  renderFunds();
}

async function login(event) {
  event.preventDefault();
  showError("");
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  const body = new URLSearchParams({ username: email, password });

  const response = await fetch(`${API}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || "Login failed");
  }

  const data = await response.json();
  token = data.access_token;
  localStorage.setItem(TOKEN_KEY, token);
  await bootstrapApp();
}

async function register(event) {
  event.preventDefault();
  showError("");
  const email = document.getElementById("register-email").value.trim();
  const password = document.getElementById("register-password").value;

  await fetchJson(`${API}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  document.getElementById("login-email").value = email;
  document.getElementById("login-password").value = password;
  await login(new Event("submit"));
}

async function addFund(event) {
  event.preventDefault();
  showError("");
  const input = document.getElementById("isin-input");
  const button = document.getElementById("add-fund");
  button.disabled = true;
  button.textContent = "Looking up…";

  try {
    await fetchJson(`${API}/funds`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ isin: input.value.trim().toUpperCase() }),
    });
    input.value = "";
    await loadFundsAndPortfolio();
  } catch (err) {
    showError(err.message);
  } finally {
    button.disabled = false;
    button.textContent = "Add ISIN";
  }
}

async function deleteFund(isin) {
  showError("");
  try {
    await fetchJson(`${API}/funds/${isin}`, { method: "DELETE" });
    delete weights[isin];
    await loadFundsAndPortfolio();
  } catch (err) {
    showError(err.message);
  }
}

async function generateReport(event) {
  event.preventDefault();
  showError("");
  const button = document.getElementById("generate-report");
  const positions = getPositionsFromWeights();
  button.disabled = true;
  button.textContent = "Generating…";

  try {
    const response = await fetch(`${API}/report`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ positions }),
    });
    if (response.status === 401) {
      logout();
      throw new Error("Session expired. Please log in again.");
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || response.statusText);
    }
    const html = await response.text();
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
    URL.revokeObjectURL(url);
  } catch (err) {
    showError(err.message);
  } finally {
    button.disabled = false;
    button.textContent = "Generate report";
    updateWeightTotal();
  }
}

async function bootstrapApp() {
  const user = await fetchJson(`${API}/auth/me`);
  setAuthenticated(true, user.email);
  await loadFundsAndPortfolio();
}

document.getElementById("login-form").addEventListener("submit", (event) => {
  login(event).catch((err) => showError(err.message));
});
document.getElementById("register-form").addEventListener("submit", (event) => {
  register(event).catch((err) => showError(err.message));
});
document.getElementById("logout").addEventListener("click", logout);
document.getElementById("add-fund-form").addEventListener("submit", addFund);
document.getElementById("report-form").addEventListener("submit", generateReport);

if (token) {
  bootstrapApp().catch(() => logout());
}
