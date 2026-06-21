(function () {
  const api = window.PortfolioApi;

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function renderPortfolioSelect(portfolios) {
    const select = document.getElementById("portfolio-select");
    if (!select) {
      return;
    }

    const selectedId = api.getPortfolioId();

    if (!portfolios.length) {
      select.innerHTML = '<option value="">No portfolios</option>';
      select.disabled = true;
      return;
    }

    select.disabled = false;
    select.innerHTML = portfolios
      .map(
        (portfolio) =>
          `<option value="${portfolio.id}">${escapeHtml(portfolio.name)}</option>`,
      )
      .join("");

    const active =
      portfolios.find((portfolio) => portfolio.id === selectedId) ?? portfolios[0];
    select.value = String(active.id);
  }

  async function fetchPortfolios() {
    return api.fetchJson(`${api.API}/portfolios`);
  }

  async function loadPortfolios() {
    const portfolios = await fetchPortfolios();
    renderPortfolioSelect(portfolios);
    return portfolios;
  }

  async function selectPortfolio(portfolioId) {
    api.setPortfolioId(portfolioId);
    const portfolios = await fetchPortfolios();
    renderPortfolioSelect(portfolios);
    window.AppShell?.updateActivePortfolioName(portfolios);
    window.RiskView?.resetRiskAnalysis();
    return portfolios;
  }

  async function createPortfolio(name) {
    const portfolio = await api.fetchJson(`${api.API}/portfolios`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    await selectPortfolio(portfolio.id);
    return portfolio;
  }

  async function deletePortfolio(portfolioId) {
    await api.fetchJson(`${api.API}/portfolios/${portfolioId}`, {
      method: "DELETE",
    });

    const portfolios = await fetchPortfolios();
    if (!portfolios.length) {
      api.setPortfolioId(null);
      renderPortfolioSelect(portfolios);
      window.AppShell?.updateActivePortfolioName([]);
      return portfolios;
    }

    const activeId = api.getPortfolioId();
    const nextId =
      portfolios.find((portfolio) => portfolio.id === activeId)?.id ?? portfolios[0].id;
    await selectPortfolio(nextId);
    return portfolios;
  }

  window.PortfoliosView = {
    loadPortfolios,
    selectPortfolio,
    createPortfolio,
    deletePortfolio,
    renderPortfolioSelect,
  };
})();
