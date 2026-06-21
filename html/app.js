(function () {
  const api = window.PortfolioApi;
  const CREATE_VALUE = window.PortfoliosView.CREATE_VALUE;

  let activeTab = "management";

  function showError(message) {
    const el = document.getElementById("error");
    if (!el) {
      return;
    }
    el.textContent = message;
    el.hidden = !message;
  }

  function updateActivePortfolioName(portfolios) {
    const label = document.getElementById("portfolio-table-name");
    if (!label) {
      return;
    }
    const selectedId = api.getPortfolioId();
    const selected = portfolios?.find((portfolio) => portfolio.id === selectedId);
    label.textContent = selected?.name ?? "";
  }

  function setActiveTab(tabName) {
    activeTab = tabName;

    document.querySelectorAll(".app-tab").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.tab === tabName);
    });

    document.getElementById("management-panel").hidden = tabName !== "management";
    document.getElementById("risk-panel").hidden = tabName !== "risk";
  }

  async function reloadActiveTab() {
    if (activeTab === "management") {
      await window.ManagementView.loadManagement();
      return;
    }

    if (activeTab === "risk") {
      window.RiskView.resetRiskAnalysis();
      await window.RiskView.loadRiskAnalysis({ force: true });
    }
  }

  async function showTab(tabName) {
    setActiveTab(tabName);

    if (tabName === "management") {
      if (api.getPortfolioId() === null) {
        showError("Select or create a portfolio first.");
        return;
      }
      await window.ManagementView.loadManagement();
      return;
    }

    if (api.getPortfolioId() === null) {
      showError("Select or create a portfolio first.");
      return;
    }
    await window.RiskView.loadRiskAnalysis();
  }

  function restorePortfolioSelectValue() {
    const select = document.getElementById("portfolio-select");
    const portfolioId = api.getPortfolioId();
    if (portfolioId !== null) {
      select.value = String(portfolioId);
      return;
    }
    if (select.options.length > 1) {
      select.selectedIndex = 0;
    }
  }

  function showPortfolioCreateInput() {
    const select = document.getElementById("portfolio-select");
    const input = document.getElementById("portfolio-create-input");
    restorePortfolioSelectValue();
    select.hidden = true;
    input.hidden = false;
    input.value = "";
    input.focus();
  }

  function hidePortfolioCreateInput() {
    const select = document.getElementById("portfolio-select");
    const input = document.getElementById("portfolio-create-input");
    input.hidden = true;
    select.hidden = false;
    restorePortfolioSelectValue();
  }

  async function ensureSelectedPortfolio(portfolios) {
    if (!portfolios.length) {
      api.setPortfolioId(null);
      updateActivePortfolioName([]);
      return portfolios;
    }

    const storedId = api.getPortfolioId();
    const selected =
      portfolios.find((portfolio) => portfolio.id === storedId) ?? portfolios[0];
    api.setPortfolioId(selected.id);
    updateActivePortfolioName(portfolios);
    return portfolios;
  }

  async function bootstrapApp() {
    document.getElementById("app-tabs").removeAttribute("hidden");

    const portfolios = await window.PortfoliosView.loadPortfolios();
    await ensureSelectedPortfolio(portfolios);
    showError("");

    setActiveTab("management");
    if (api.getPortfolioId() !== null) {
      await window.ManagementView.loadManagement();
    } else {
      showError("Create a portfolio to get started.");
      showPortfolioCreateInput();
    }
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
      if (activeTab === "management") {
        await window.ManagementView.loadManagement();
      } else if (activeTab === "risk") {
        window.RiskView.resetRiskAnalysis();
        await window.RiskView.loadRiskAnalysis({ force: true });
      }
    } catch (err) {
      showError(err.message);
    } finally {
      input.disabled = false;
      input.focus();
    }
  }

  async function submitNewPortfolioName() {
    const input = document.getElementById("portfolio-create-input");
    const name = input.value.trim();
    if (!name) {
      hidePortfolioCreateInput();
      return;
    }

    showError("");
    input.disabled = true;
    try {
      await window.PortfoliosView.createPortfolio(name);
      hidePortfolioCreateInput();
      setActiveTab("management");
      await window.ManagementView.loadManagement();
    } catch (err) {
      showError(err.message);
      input.focus();
    } finally {
      input.disabled = false;
    }
  }

  async function handlePortfolioDropdownChange() {
    const select = document.getElementById("portfolio-select");
    if (select.value === CREATE_VALUE) {
      showPortfolioCreateInput();
      return;
    }

    const portfolioId = Number.parseInt(select.value, 10);
    if (!Number.isFinite(portfolioId)) {
      return;
    }

    showError("");
    await window.PortfoliosView.selectPortfolio(portfolioId);
    await reloadActiveTab();
  }

  document.getElementById("portfolio-select").addEventListener("change", () => {
    handlePortfolioDropdownChange().catch((err) => showError(err.message));
  });

  const portfolioCreateInput = document.getElementById("portfolio-create-input");
  portfolioCreateInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      submitNewPortfolioName().catch((err) => showError(err.message));
      return;
    }
    if (event.key === "Escape") {
      hidePortfolioCreateInput();
      showError("");
    }
  });
  portfolioCreateInput.addEventListener("blur", () => {
    window.setTimeout(() => {
      if (portfolioCreateInput.hidden) {
        return;
      }
      if (!portfolioCreateInput.value.trim()) {
        hidePortfolioCreateInput();
      }
    }, 0);
  });

  document.getElementById("add-fund-form").addEventListener("submit", (event) => {
    addFund(event).catch((err) => showError(err.message));
  });
  document.querySelectorAll(".app-tab").forEach((button) => {
    button.addEventListener("click", () => {
      showTab(button.dataset.tab).catch((err) => showError(err.message));
    });
  });

  window.AppShell = {
    showError,
    updateActivePortfolioName,
  };

  bootstrapApp().catch((err) => showError(err.message));
})();
