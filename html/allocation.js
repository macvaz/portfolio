(function () {
  const api = window.PortfolioApi;
  const screen = document.getElementById("allocation-screen");
  const titleEl = document.getElementById("allocation-title");
  const totalInput = document.getElementById("allocation-total");
  const moneyPanel = document.getElementById("allocation-panel-money");
  const returnsPanel = document.getElementById("allocation-panel-returns");
  const moneyBodyEl = document.getElementById("allocation-money-body");
  const returnsHeadRowEl = document.getElementById("allocation-returns-head-row");
  const returnsBodyEl = document.getElementById("allocation-returns-body");
  const returnsPortfolioRowEl = document.getElementById("allocation-returns-portfolio-row");
  const weightTotalEl = document.getElementById("allocation-weight-total");
  const amountTotalEl = document.getElementById("allocation-amount-total");
  const moneyEmptyEl = document.getElementById("allocation-money-empty");
  const returnsEmptyEl = document.getElementById("allocation-returns-empty");
  const returnsLoadingEl = document.getElementById("allocation-returns-loading");
  const closeBtn = document.getElementById("allocation-close");
  const openBtn = document.getElementById("portfolio-allocation-btn");
  const modeTabs = Array.from(document.querySelectorAll(".allocation-mode-tab"));
  const modeTabsEl = document.querySelector(".allocation-mode-tabs");
  const returnsAvailableMq = window.matchMedia(
    "(orientation: landscape), (min-width: 901px)",
  );

  const DEFAULT_TOTAL = 500000;

  const amountFormatter = new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  let activeMode = "money";
  let recentReturns = { dates: [], byIsin: new Map() };
  let recentReturnsRequest = 0;
  let recentReturnsLoaded = false;

  function returnsModeAvailable() {
    return returnsAvailableMq.matches;
  }

  function updateOpenButtonLabel() {
    if (!openBtn) {
      return;
    }
    const label = returnsModeAvailable()
      ? "Money allocation and daily returns"
      : "Money allocation";
    openBtn.setAttribute("aria-label", label);
    openBtn.title = label;
  }

  function syncReturnsAvailability() {
    const available = returnsModeAvailable();
    if (modeTabsEl) {
      modeTabsEl.hidden = !available;
    }
    updateOpenButtonLabel();
    if (!available && activeMode === "returns" && !screen.hidden) {
      setMode("money");
    }
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function formatWeight(value) {
    if (!Number.isFinite(value)) {
      return "—";
    }
    if (Math.abs(value - Math.round(value)) < 1e-9) {
      return String(Math.round(value));
    }
    return value.toFixed(2);
  }

  function formatDailyReturn(value) {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return "—";
    }
    const sign = value > 0 ? "+" : "";
    return `${sign}${Number(value).toFixed(2)}`;
  }

  function dailyReturnClass(value) {
    if (value === null || value === undefined || Number.isNaN(value) || value === 0) {
      return "";
    }
    return value > 0 ? "metric-positive" : "metric-negative";
  }

  function formatDateHeader(isoDate) {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(isoDate));
    if (!match) {
      return escapeHtml(isoDate);
    }
    return `${match[2]}/${match[3]}`;
  }

  function parseTotal(value) {
    const total = Number.parseFloat(String(value).trim().replace(",", "."));
    if (!Number.isFinite(total) || total < 0) {
      return null;
    }
    return total;
  }

  function portfolioFunds() {
    return window.ManagementView?.getPortfolioAllocationFunds?.() ?? [];
  }

  function renderFundName(fund) {
    const name = escapeHtml(fund.name);
    if (fund.morningstar_url) {
      return `<a href="${fund.morningstar_url}" class="fund-link" target="_blank" rel="noopener noreferrer" title="${name}">${name}</a>`;
    }
    return `<span class="fund-name" title="${name}">${name}</span>`;
  }

  function updateTitle() {
    const portfolioName = document.getElementById("portfolio-table-name")?.textContent?.trim();
    const base = activeMode === "returns" ? "Daily returns" : "Money allocation";
    titleEl.textContent = portfolioName ? `${base} — ${portfolioName}` : base;
  }

  function renderMoneyRows(funds, total) {
    if (!funds.length) {
      moneyBodyEl.innerHTML = "";
      weightTotalEl.textContent = "—";
      amountTotalEl.textContent = "—";
      moneyEmptyEl.hidden = false;
      return;
    }

    moneyEmptyEl.hidden = true;
    let weightSum = 0;
    let amountSum = 0;

    moneyBodyEl.innerHTML = funds
      .map((fund) => {
        const weight = fund.weight;
        const amount = total === null ? null : (total * weight) / 100;
        weightSum += weight;
        if (amount !== null) {
          amountSum += amount;
        }
        const amountText = amount === null ? "—" : amountFormatter.format(amount);
        return `
          <tr>
            <td class="allocation-col-name">${renderFundName(fund)}</td>
            <td class="allocation-col-weight">${formatWeight(weight)}</td>
            <td class="allocation-col-amount">${amountText}</td>
          </tr>`;
      })
      .join("");

    weightTotalEl.textContent = `${formatWeight(weightSum)}`;
    amountTotalEl.textContent = total === null ? "—" : amountFormatter.format(amountSum);
  }

  function computePortfolioDailyReturns(funds, dateCount) {
    const weightSum = funds.reduce((sum, fund) => sum + Number(fund.weight || 0), 0);
    if (!(weightSum > 0) || dateCount <= 0) {
      return Array.from({ length: dateCount }, () => null);
    }

    return Array.from({ length: dateCount }, (_, index) => {
      let contribution = 0;
      let anyValue = false;
      for (const fund of funds) {
        const values = recentReturns.byIsin.get(fund.isin) || [];
        const value = index < values.length ? values[index] : null;
        if (value === null || value === undefined || Number.isNaN(value)) {
          continue;
        }
        anyValue = true;
        contribution += (Number(fund.weight) / weightSum) * Number(value);
      }
      // Missing fund days count as 0% for that weight; only — if nothing published.
      return anyValue ? contribution : null;
    });
  }

  function renderReturnsRows(funds) {
    const dates = recentReturns.dates || [];
    const dateCount = dates.length;

    returnsHeadRowEl.innerHTML = `
      <th scope="col">Name</th>
      ${dates
        .map(
          (date) =>
            `<th scope="col" class="allocation-col-day" title="${escapeHtml(date)}">${formatDateHeader(date)}</th>`,
        )
        .join("")}`;

    if (!funds.length) {
      returnsBodyEl.innerHTML = "";
      if (returnsPortfolioRowEl) {
        returnsPortfolioRowEl.hidden = true;
        returnsPortfolioRowEl.innerHTML = `<th scope="row">Portfolio</th>`;
      }
      returnsEmptyEl.hidden = false;
      return;
    }

    returnsEmptyEl.hidden = true;
    returnsBodyEl.innerHTML = funds
      .map((fund) => {
        const values = recentReturns.byIsin.get(fund.isin) || [];
        const cells = [];
        for (let index = 0; index < dateCount; index += 1) {
          const value = index < values.length ? values[index] : null;
          const cls = dailyReturnClass(value);
          cells.push(
            `<td class="allocation-col-day ${cls}">${formatDailyReturn(value)}</td>`,
          );
        }
        return `
          <tr>
            <td class="allocation-col-name">${renderFundName(fund)}</td>
            ${cells.join("")}
          </tr>`;
      })
      .join("");

    const portfolioReturns = computePortfolioDailyReturns(funds, dateCount);
    if (returnsPortfolioRowEl) {
      returnsPortfolioRowEl.hidden = false;
      returnsPortfolioRowEl.innerHTML = `
        <th scope="row">Portfolio</th>
        ${portfolioReturns
          .map((value) => {
            const cls = dailyReturnClass(value);
            return `<td class="allocation-col-day ${cls}">${formatDailyReturn(value)}</td>`;
          })
          .join("")}`;
    }
  }

  function refreshMoney() {
    renderMoneyRows(portfolioFunds(), parseTotal(totalInput.value));
  }

  function refreshReturns() {
    renderReturnsRows(portfolioFunds());
  }

  function refresh() {
    updateTitle();
    if (activeMode === "returns") {
      refreshReturns();
      return;
    }
    refreshMoney();
  }

  async function loadRecentReturns({ force = false } = {}) {
    if (recentReturnsLoaded && !force) {
      return;
    }

    const requestId = ++recentReturnsRequest;
    returnsLoadingEl.hidden = false;
    returnsEmptyEl.hidden = true;

    if (api.getPortfolioId() === null) {
      recentReturns = { dates: [], byIsin: new Map() };
      recentReturnsLoaded = true;
      returnsLoadingEl.hidden = true;
      return;
    }

    try {
      const payload = await api.fetchJson(
        api.withPortfolioId(`${api.PORTFOLIO_API}/recent_daily_returns?days=5`),
      );
      if (requestId !== recentReturnsRequest) {
        return;
      }
      const rawDates = Array.isArray(payload.dates) ? payload.dates : [];
      const order = rawDates
        .map((date, index) => ({ date, index }))
        .sort((a, b) => String(b.date).localeCompare(String(a.date)));
      const dates = order.map((item) => item.date);
      const byIsin = new Map();
      (payload.funds || []).forEach((fund) => {
        const values = Array.isArray(fund.returns) ? fund.returns : [];
        byIsin.set(
          fund.isin,
          order.map((item) => (item.index < values.length ? values[item.index] : null)),
        );
      });
      recentReturns = {
        dates,
        byIsin,
      };
      recentReturnsLoaded = true;
    } catch (_error) {
      if (requestId !== recentReturnsRequest) {
        return;
      }
      recentReturns = { dates: [], byIsin: new Map() };
      recentReturnsLoaded = true;
    } finally {
      if (requestId === recentReturnsRequest) {
        returnsLoadingEl.hidden = true;
      }
    }
  }

  async function setMode(mode) {
    if (mode === "returns" && !returnsModeAvailable()) {
      mode = "money";
    }
    activeMode = mode === "returns" ? "returns" : "money";

    modeTabs.forEach((tab) => {
      const isActive = tab.dataset.mode === activeMode;
      tab.classList.toggle("is-active", isActive);
      tab.setAttribute("aria-selected", isActive ? "true" : "false");
    });

    moneyPanel.hidden = activeMode !== "money";
    returnsPanel.hidden = activeMode !== "returns";
    screen.classList.toggle("is-returns-mode", activeMode === "returns");

    updateTitle();

    if (activeMode === "money") {
      refreshMoney();
      return;
    }

    refreshReturns();
    await loadRecentReturns();
    if (!screen.hidden && activeMode === "returns") {
      refreshReturns();
    }
  }

  async function open() {
    totalInput.value = String(DEFAULT_TOTAL);
    recentReturns = { dates: [], byIsin: new Map() };
    recentReturnsLoaded = false;
    screen.hidden = false;
    screen.removeAttribute("hidden");
    document.body.classList.add("is-allocation-open");
    await setMode("money");
  }

  function close() {
    recentReturnsRequest += 1;
    screen.hidden = true;
    screen.setAttribute("hidden", "");
    document.body.classList.remove("is-allocation-open");
  }

  openBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    open();
  });

  closeBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    close();
  });

  modeTabs.forEach((tab) => {
    tab.addEventListener("click", (event) => {
      event.preventDefault();
      setMode(tab.dataset.mode);
    });
  });

  if (typeof returnsAvailableMq.addEventListener === "function") {
    returnsAvailableMq.addEventListener("change", syncReturnsAvailability);
  } else if (typeof returnsAvailableMq.addListener === "function") {
    returnsAvailableMq.addListener(syncReturnsAvailability);
  }
  syncReturnsAvailability();

  totalInput?.addEventListener("input", () => {
    if (activeMode === "money") {
      refreshMoney();
    }
  });

  screen?.addEventListener("click", (event) => {
    if (event.target === screen) {
      close();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (screen.hidden || event.key !== "Escape") {
      return;
    }
    close();
  });

  window.AllocationView = {
    open,
    close,
    refresh,
    setMode,
    setButtonVisible(visible) {
      if (!openBtn) {
        return;
      }
      openBtn.hidden = !visible;
    },
    isOpen() {
      return !screen.hidden;
    },
  };
})();
