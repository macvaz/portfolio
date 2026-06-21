(function () {
  const api = window.PortfolioApi;

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
    const deleteBtn = document.getElementById("portfolio-delete-btn");
    const defaultBtn = document.getElementById("portfolio-default-btn");
    if (!label) {
      return;
    }
    const selectedId = api.getPortfolioId();
    const selected = portfolios?.find((portfolio) => portfolio.id === selectedId);
    label.textContent = selected?.name ?? "";
    if (deleteBtn) {
      deleteBtn.hidden = !selected;
    }
    if (defaultBtn) {
      const isDefault = selected?.is_default === true;
      defaultBtn.hidden = !selected;
      defaultBtn.disabled = isDefault;
      defaultBtn.classList.toggle("is-active", isDefault);
      defaultBtn.title = isDefault ? "Default portfolio" : "Set as default portfolio";
      defaultBtn.setAttribute(
        "aria-label",
        isDefault ? "Default portfolio" : "Set as default portfolio",
      );
    }
  }

  async function setActivePortfolioAsDefault() {
    const portfolioId = api.getPortfolioId();
    if (portfolioId === null) {
      return;
    }

    showError("");
    try {
      const portfolios = await window.PortfoliosView.setDefaultPortfolio(portfolioId);
      updateActivePortfolioName(portfolios);
      window.PortfoliosView.renderPortfolioSelect(portfolios);
    } catch (err) {
      showError(err.message);
    }
  }

  async function deleteActivePortfolio() {
    const portfolioId = api.getPortfolioId();
    if (portfolioId === null) {
      return;
    }

    showError("");
    try {
      await window.PortfoliosView.deletePortfolio(portfolioId);
      if (api.getPortfolioId() === null) {
        window.ManagementView?.resetManagement();
        showError("Create a portfolio to get started.");
        return;
      }
      await reloadActiveTab();
    } catch (err) {
      showError(err.message);
    }
  }

  function setLayoutHidden(element, hidden) {
    element.classList.toggle("is-layout-hidden", hidden);
    element.setAttribute("aria-hidden", hidden ? "true" : "false");
  }

  function updateToolbarForTab(tabName) {
    const isTactical = tabName === "tactical";
    setLayoutHidden(document.querySelector(".toolbar-right"), isTactical);
    setLayoutHidden(document.getElementById("add-fund-form"), isTactical);

    if (isTactical) {
      hidePortfolioCreateInput();
    }
  }

  function setActiveTab(tabName) {
    activeTab = tabName;

    document.querySelectorAll(".app-tab").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.tab === tabName);
    });

    document.getElementById("management-panel").hidden = tabName !== "management";
    document.getElementById("risk-panel").hidden = tabName !== "risk";
    document.getElementById("tactical-panel").hidden = tabName !== "tactical";
    updateToolbarForTab(tabName);
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

    if (tabName === "tactical") {
      showError("");
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
    }
  }

  const CREATE_BTN_REVEAL_MS = 1000;
  let createBtnHideTimer = null;

  function revealPortfolioCreateBtn() {
    const picker = document.querySelector(".portfolio-picker");
    if (!picker || picker.classList.contains("is-creating")) {
      return;
    }
    picker.classList.add("is-create-revealed");
    if (createBtnHideTimer !== null) {
      clearTimeout(createBtnHideTimer);
      createBtnHideTimer = null;
    }
  }

  function scheduleHidePortfolioCreateBtn() {
    const picker = document.querySelector(".portfolio-picker");
    if (!picker || picker.classList.contains("is-creating")) {
      return;
    }
    if (createBtnHideTimer !== null) {
      clearTimeout(createBtnHideTimer);
    }
    createBtnHideTimer = window.setTimeout(() => {
      createBtnHideTimer = null;
      picker.classList.remove("is-create-revealed");
    }, CREATE_BTN_REVEAL_MS);
  }

  function clearPortfolioCreateBtnReveal() {
    const picker = document.querySelector(".portfolio-picker");
    if (createBtnHideTimer !== null) {
      clearTimeout(createBtnHideTimer);
      createBtnHideTimer = null;
    }
    picker?.classList.remove("is-create-revealed");
  }

  function showPortfolioCreateInput() {
    const picker = document.querySelector(".portfolio-picker");
    const slot = document.querySelector(".portfolio-select-slot");
    const select = document.getElementById("portfolio-select");
    const input = document.getElementById("portfolio-create-input");
    const createBtn = document.getElementById("portfolio-create-btn");
    restorePortfolioSelectValue();

    clearPortfolioCreateBtnReveal();
    picker?.classList.add("is-creating");

    const { width, height } = select.getBoundingClientRect();
    slot.style.width = `${width}px`;
    slot.style.height = `${height}px`;

    createBtn.classList.add("is-invisible");
    select.hidden = true;
    input.hidden = false;
    input.value = "";
    input.focus();
  }

  function hidePortfolioCreateInput() {
    const picker = document.querySelector(".portfolio-picker");
    const slot = document.querySelector(".portfolio-select-slot");
    const select = document.getElementById("portfolio-select");
    const input = document.getElementById("portfolio-create-input");
    const createBtn = document.getElementById("portfolio-create-btn");

    picker?.classList.remove("is-creating");
    clearPortfolioCreateBtnReveal();

    slot.style.width = "";
    slot.style.height = "";
    input.hidden = true;
    createBtn.classList.remove("is-invisible");
    select.hidden = false;
    restorePortfolioSelectValue();
  }

  async function ensureSelectedPortfolio(portfolios) {
    if (!portfolios.length) {
      api.setPortfolioId(null);
      updateActivePortfolioName([]);
      return portfolios;
    }

    const selected = window.PortfoliosView.resolveDefaultPortfolio(portfolios);
    api.setPortfolioId(selected.id);
    updateActivePortfolioName(portfolios);
    window.PortfoliosView.renderPortfolioSelect(portfolios);
    return portfolios;
  }

  async function bootstrapApp() {
    document.getElementById("app-tabs").removeAttribute("hidden");

    const portfolios = await window.PortfoliosView.fetchPortfolios();
    await ensureSelectedPortfolio(portfolios);
    showError("");

    setActiveTab("management");
    if (api.getPortfolioId() !== null) {
      await window.ManagementView.loadManagement();
    } else {
      showError("Create a portfolio to get started.");
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
    const portfolioId = Number.parseInt(select.value, 10);
    if (!Number.isFinite(portfolioId)) {
      return;
    }

    showError("");
    await window.PortfoliosView.selectPortfolio(portfolioId);
    await reloadActiveTab();
  }

  document.getElementById("portfolio-create-btn").addEventListener("click", () => {
    showPortfolioCreateInput();
  });

  const portfolioSelectSlot = document.querySelector(".portfolio-select-slot");
  const portfolioCreateBtn = document.getElementById("portfolio-create-btn");

  portfolioSelectSlot.addEventListener("mouseenter", revealPortfolioCreateBtn);
  portfolioSelectSlot.addEventListener("mouseleave", scheduleHidePortfolioCreateBtn);
  portfolioCreateBtn.addEventListener("mouseenter", revealPortfolioCreateBtn);
  portfolioCreateBtn.addEventListener("mouseleave", scheduleHidePortfolioCreateBtn);

  document.getElementById("portfolio-default-btn").addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    setActivePortfolioAsDefault().catch((err) => showError(err.message));
  });

  document.getElementById("portfolio-delete-btn").addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    deleteActivePortfolio().catch((err) => showError(err.message));
  });

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
