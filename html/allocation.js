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
  const returnsBenchmarkRowEl = document.getElementById("allocation-returns-benchmark-row");
  const weightTotalEl = document.getElementById("allocation-weight-total");
  const amountTotalEl = document.getElementById("allocation-amount-total");
  const moneyEmptyEl = document.getElementById("allocation-money-empty");
  const returnsEmptyEl = document.getElementById("allocation-returns-empty");
  const returnsLoadingEl = document.getElementById("allocation-returns-loading");
  const closeBtn = document.getElementById("allocation-close");
  const returnsBtn = document.getElementById("portfolio-allocation-btn");
  const moneyBtn = document.getElementById("portfolio-money-btn");

  const DEFAULT_TOTAL = 500000;

  const amountFormatter = new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 0,
  });

  let activeMode = "money";
  let recentReturns = { dates: [], byIsin: new Map(), benchmark: null };
  let recentReturnsRequest = 0;
  let recentReturnsLoaded = false;

  function syncButtonVisibility(portfolioSelected) {
    if (moneyBtn) {
      moneyBtn.hidden = !portfolioSelected;
    }
    if (returnsBtn) {
      returnsBtn.hidden = !portfolioSelected;
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
        const amount = total === null ? null : Math.round((total * weight) / 100);
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

  function compoundReturns(values) {
    // Daily values are newest → oldest; compound in chronological order.
    if (!Array.isArray(values) || !values.length) {
      return null;
    }
    let growth = 1;
    let anyValue = false;
    for (let index = values.length - 1; index >= 0; index -= 1) {
      const value = values[index];
      if (value === null || value === undefined || Number.isNaN(value)) {
        // Missing days count as 0% (no change).
        continue;
      }
      anyValue = true;
      growth *= 1 + Number(value) / 100;
    }
    return anyValue ? (growth - 1) * 100 : null;
  }

  function renderReturnCell(value, extraClass = "") {
    const cls = ["allocation-col-day", dailyReturnClass(value), extraClass]
      .filter(Boolean)
      .join(" ");
    return `<td class="${cls}">${formatDailyReturn(value)}</td>`;
  }

  function renderDailyReturnCells(values, dateCount) {
    const cells = [];
    for (let index = 0; index < dateCount; index += 1) {
      const value = index < values.length ? values[index] : null;
      const isOldest = index === dateCount - 1;
      cells.push(renderReturnCell(value, isOldest ? "allocation-col-before-total" : ""));
    }
    return cells;
  }

  function renderSummaryReturnRow(rowEl, label, values, dateCount) {
    if (!rowEl) {
      return;
    }
    const aligned = [];
    for (let index = 0; index < dateCount; index += 1) {
      aligned.push(index < values.length ? values[index] : null);
    }
    const cells = renderDailyReturnCells(aligned, dateCount);
    const total = compoundReturns(aligned);
    rowEl.hidden = false;
    rowEl.innerHTML = `
      <th scope="row">${escapeHtml(label)}</th>
      ${cells.join("")}
      ${renderReturnCell(total, "allocation-col-total")}`;
  }

  function hideSummaryReturnRow(rowEl, label) {
    if (!rowEl) {
      return;
    }
    rowEl.hidden = true;
    rowEl.innerHTML = `<th scope="row">${escapeHtml(label)}</th>`;
  }

  function renderReturnsRows(funds) {
    const dates = recentReturns.dates || [];
    const dateCount = dates.length;

    returnsHeadRowEl.innerHTML = `
      <th scope="col" class="allocation-col-name">Name</th>
      ${dates
        .map((date, index) => {
          const isOldest = index === dateCount - 1;
          const extra = isOldest ? " allocation-col-before-total" : "";
          return `<th scope="col" class="allocation-col-day${extra}" title="${escapeHtml(date)}">${formatDateHeader(date)}</th>`;
        })
        .join("")}
      <th scope="col" class="allocation-col-day allocation-col-total" title="Compounded return over the shown dates">Total</th>`;

    if (!funds.length) {
      returnsBodyEl.innerHTML = "";
      hideSummaryReturnRow(returnsPortfolioRowEl, "Portfolio");
      hideSummaryReturnRow(
        returnsBenchmarkRowEl,
        "SP500",
      );
      returnsEmptyEl.hidden = false;
      return;
    }

    returnsEmptyEl.hidden = true;
    returnsBodyEl.innerHTML = funds
      .map((fund) => {
        const values = recentReturns.byIsin.get(fund.isin) || [];
        const aligned = [];
        for (let index = 0; index < dateCount; index += 1) {
          aligned.push(index < values.length ? values[index] : null);
        }
        const cells = renderDailyReturnCells(aligned, dateCount);
        const total = compoundReturns(aligned);
        return `
          <tr>
            <td class="allocation-col-name">${renderFundName(fund)}</td>
            ${cells.join("")}
            ${renderReturnCell(total, "allocation-col-total")}
          </tr>`;
      })
      .join("");

    const portfolioReturns = computePortfolioDailyReturns(funds, dateCount);
    renderSummaryReturnRow(returnsPortfolioRowEl, "Portfolio", portfolioReturns, dateCount);

    const benchmark = recentReturns.benchmark;
    const benchmarkValues = Array.isArray(benchmark?.returns) ? benchmark.returns : [];
    renderSummaryReturnRow(
      returnsBenchmarkRowEl,
      "SP500",
      benchmarkValues,
      dateCount,
    );
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
      recentReturns = { dates: [], byIsin: new Map(), benchmark: null };
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
      const benchmarkPayload = payload.benchmark;
      const benchmarkValues = Array.isArray(benchmarkPayload?.returns)
        ? benchmarkPayload.returns
        : [];
      recentReturns = {
        dates,
        byIsin,
        benchmark: {
          isin: benchmarkPayload?.isin || null,
          name: benchmarkPayload?.name || "SP500",
          returns: order.map((item) =>
            item.index < benchmarkValues.length ? benchmarkValues[item.index] : null,
          ),
        },
      };
      recentReturnsLoaded = true;
    } catch (_error) {
      if (requestId !== recentReturnsRequest) {
        return;
      }
      recentReturns = { dates: [], byIsin: new Map(), benchmark: null };
      recentReturnsLoaded = true;
    } finally {
      if (requestId === recentReturnsRequest) {
        returnsLoadingEl.hidden = true;
      }
    }
  }

  async function setMode(mode) {
    activeMode = mode === "returns" ? "returns" : "money";

    moneyPanel.hidden = activeMode !== "money";
    returnsPanel.hidden = activeMode !== "returns";
    screen.classList.toggle("is-returns-mode", activeMode === "returns");

    updateTitle();

    if (activeMode === "money") {
      refreshMoney();
      totalInput?.focus();
      return;
    }

    refreshReturns();
    await loadRecentReturns();
    if (!screen.hidden && activeMode === "returns") {
      refreshReturns();
    }
  }

  async function open(mode = "money") {
    const requested = mode === "returns" ? "returns" : "money";

    totalInput.value = String(DEFAULT_TOTAL);
    recentReturns = { dates: [], byIsin: new Map(), benchmark: null };
    recentReturnsLoaded = false;
    screen.hidden = false;
    screen.removeAttribute("hidden");
    document.body.classList.add("is-allocation-open");
    await setMode(requested);
  }

  function close() {
    recentReturnsRequest += 1;
    screen.hidden = true;
    screen.setAttribute("hidden", "");
    document.body.classList.remove("is-allocation-open");
  }

  moneyBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    open("money");
  });

  returnsBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    open("returns");
  });

  closeBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    close();
  });

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
      syncButtonVisibility(Boolean(visible));
    },
    isOpen() {
      return !screen.hidden;
    },
  };
})();
