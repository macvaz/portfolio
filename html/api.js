(function () {
  const API = "/api";
  const PORTFOLIO_API = "/api/portfolio";
  const PORTFOLIO_ID_KEY = "portfolio_id";

  let portfolioId = localStorage.getItem(PORTFOLIO_ID_KEY);

  function getPortfolioId() {
    return portfolioId ? Number(portfolioId) : null;
  }

  function setPortfolioId(value) {
    if (value === null || value === undefined || value === "") {
      portfolioId = null;
      localStorage.removeItem(PORTFOLIO_ID_KEY);
      return;
    }
    portfolioId = String(value);
    localStorage.setItem(PORTFOLIO_ID_KEY, portfolioId);
  }

  function withPortfolioId(path) {
    const id = getPortfolioId();
    if (id === null) {
      return path;
    }
    const separator = path.includes("?") ? "&" : "?";
    return `${path}${separator}portfolio_id=${encodeURIComponent(id)}`;
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
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
    PORTFOLIO_API,
    getPortfolioId,
    setPortfolioId,
    withPortfolioId,
    fetchJson,
  };
})();
