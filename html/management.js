(function () {
  const api = window.PortfolioApi;

  let performanceChart = null;
  let managementData = null;
  let savingWeights = false;

  const METRIC_COLUMNS = [
    { key: "weight", format: "percent", weightColumn: true },
    { key: "beta_6m", format: "decimal2" },
    { key: "cor_6m", format: "decimal2" },
    { key: "vol_1y", format: "decimal2", beforeDivider: true },
    { key: "pct_1m", format: "signedPercent", divider: true },
    { key: "pct_3m", format: "signedPercent" },
    { key: "pct_6m", format: "signedPercent" },
    { key: "pct_ytd", format: "signedPercent", beforeDivider: true },
    { key: "sr_6m", format: "decimal2", colorize: true, divider: true },
    { key: "sr_1y", format: "decimal2", colorize: true },
  ];

  function showError(message) {
    const el = document.getElementById("error");
    if (!el) return;
    el.textContent = message;
    el.hidden = !message;
  }

  function formatWeight(value) {
    if (!Number.isFinite(value)) {
      return "0";
    }
    if (Math.abs(value - Math.round(value)) < 1e-9) {
      return String(Math.round(value));
    }
    return String(value);
  }

  function formatValue(value, format) {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return "—";
    }

    switch (format) {
      case "percent":
        return formatWeight(value);
      case "decimal2":
        return value.toFixed(2);
      case "signedPercent":
        return `${value >= 0 ? "" : ""}${value.toFixed(2)}`;
      default:
        return String(value);
    }
  }

  function metricClass(value, column) {
    if (!column.colorize && column.format !== "signedPercent") {
      return "";
    }
    if (value > 0) return "metric-positive";
    if (value < 0) return "metric-negative";
    return "metric-neutral";
  }

  function renderFundName(fund) {
    const nameLink = fund.morningstar_url
      ? `<a href="${fund.morningstar_url}" class="fund-link" target="_blank" rel="noopener noreferrer">${fund.name}</a>`
      : `<span class="fund-name">${fund.name}</span>`;
    return `
      <div class="fund-name-wrap">
        <div class="fund-delete-popup">
          <button
            type="button"
            class="fund-delete-btn"
            data-isin="${fund.isin}"
            aria-label="Delete fund"
          >
            <svg
              class="fund-delete-icon"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
              <path d="M10 11v6" />
              <path d="M14 11v6" />
              <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
            </svg>
          </button>
        </div>
        ${nameLink}
      </div>`;
  }

  function cellClasses(value, column) {
    return [
      metricClass(value, column),
      column.beforeDivider ? "col-before-divider" : "",
      column.divider ? "col-divider" : "",
    ]
      .filter(Boolean)
      .join(" ");
  }

  function renderWeightInputCell(isin, weight) {
    const display = formatWeight(weight);
    return `<td class="col-weight col-weight-editable">
      <div class="weight-cell-slot">
        <span class="weight-display">${display}</span>
        <input
          type="number"
          class="weight-input"
          min="0"
          max="100"
          step="1"
          value="${display}"
          data-isin="${isin}"
          aria-label="Weight percent"
        />
      </div>
    </td>`;
  }

  function renderMetricCells(fund, options = {}) {
    const forceZeroWeight = options.forceZeroWeight === true;
    const editableWeights = options.editableWeights === true;

    return METRIC_COLUMNS.map((column) => {
      if (column.weightColumn && editableWeights) {
        const weight = forceZeroWeight ? 0 : fund.weight;
        return renderWeightInputCell(fund.isin, weight);
      }

      const value = column.weightColumn && forceZeroWeight ? 0 : fund[column.key];
      const text = formatValue(value, column.format);
      return `<td class="${cellClasses(value, column)}">${text}</td>`;
    }).join("");
  }

  function renderFundRow(fund, options = {}) {
    return `
    <tr data-isin="${fund.isin}">
      <td class="col-name">${renderFundName(fund)}</td>
      ${renderMetricCells(fund, options)}
    </tr>`;
  }

  function renderSummaryWeightCell(value) {
    const text = formatWeight(value);
    return `<td class="col-weight col-weight-editable">
      <div class="weight-cell-slot">
        <span class="weight-display">${text}</span>
      </div>
    </td>`;
  }

  function renderSummaryRow(summary) {
    const cells = METRIC_COLUMNS.map((column) => {
      const value = summary[column.key];
      if (column.weightColumn) {
        return renderSummaryWeightCell(value);
      }
      const text = formatValue(value, column.format);
      return `<td class="${cellClasses(value, column)}">${text}</td>`;
    }).join("");

    return `
    <tr class="summary-row">
      <td class="col-name"></td>
      ${cells}
    </tr>`;
  }

  function renderTableBody(containerId, funds, options = {}) {
    const container = document.getElementById(containerId);
    container.innerHTML = funds.map((fund) => renderFundRow(fund, options)).join("");
  }

  function ensureSyncedColgroup(table, columnCount) {
    let colgroup = table.querySelector("colgroup[data-sync-cols]");
    if (!colgroup) {
      colgroup = document.createElement("colgroup");
      colgroup.dataset.syncCols = "true";
      table.insertBefore(colgroup, table.firstChild);
    }

    while (colgroup.children.length < columnCount) {
      colgroup.appendChild(document.createElement("col"));
    }
    while (colgroup.children.length > columnCount) {
      colgroup.removeChild(colgroup.lastChild);
    }

    return colgroup;
  }

  function resetSyncedTableLayout(...tables) {
    tables.forEach((table) => {
      table.querySelector("colgroup[data-sync-cols]")?.remove();
      table.style.tableLayout = "";
      table.style.width = "";
    });
  }

  function measureTableColumnWidths(table) {
    const headerCells = table.querySelectorAll("thead tr:first-child th");
    const rows = [
      ...table.querySelectorAll("tbody tr"),
      ...table.querySelectorAll("tfoot tr"),
    ];

    return Array.from(headerCells).map((headerCell, index) => {
      let maxWidth = headerCell.getBoundingClientRect().width;
      rows.forEach((row) => {
        const cell = row.cells[index];
        if (cell) {
          maxWidth = Math.max(maxWidth, cell.getBoundingClientRect().width);
        }
      });
      return maxWidth;
    });
  }

  function applyTableColumnWidths(table, widths) {
    const colgroup = ensureSyncedColgroup(table, widths.length);
    Array.from(colgroup.children).forEach((col, index) => {
      col.style.width = `${widths[index]}px`;
    });
    const tableWidth = widths.reduce((sum, width) => sum + width, 0);
    table.style.tableLayout = "fixed";
    table.style.width = `${Math.max(tableWidth, 1100)}px`;
  }

  function syncFundTableColumns() {
    const portfolioTable = document.getElementById("portfolio-table");
    const favoritesTable = document.getElementById("favorites-table");
    if (!portfolioTable || !favoritesTable) {
      return;
    }

    resetSyncedTableLayout(portfolioTable, favoritesTable);

    const widths = measureTableColumnWidths(portfolioTable);
    if (!widths.length) {
      return;
    }

    applyTableColumnWidths(portfolioTable, widths);
    applyTableColumnWidths(favoritesTable, widths);
  }

  let columnSyncFrame = null;
  let columnSyncTimer = null;

  function scheduleFundTableColumnSync() {
    if (columnSyncFrame !== null) {
      cancelAnimationFrame(columnSyncFrame);
    }
    columnSyncFrame = requestAnimationFrame(() => {
      columnSyncFrame = null;
      syncFundTableColumns();
    });
  }

  function collectWeightPositions() {
    const positions = [];
    document.querySelectorAll(".weight-input").forEach((input) => {
      const pct = Number.parseFloat(input.value);
      if (!Number.isFinite(pct) || pct <= 0) {
        return;
      }
      positions.push({
        isin: input.dataset.isin,
        weighted_assets: pct / 100,
      });
    });
    return positions;
  }

  async function loadScreenData() {
    const [curve, dashboard, portfolios] = await Promise.all([
      api.fetchJson(api.withPortfolioId(`${api.API}/curve`)),
      api.fetchJson(api.withPortfolioId(`${api.API}/dashboard`)),
      api.fetchJson(`${api.API}/portfolios`),
    ]);
    return { curve, dashboard, portfolios };
  }

  function updatePortfolioTableTitle(portfolios) {
    window.AppShell?.updateActivePortfolioName(portfolios);
  }

  async function savePortfolioWeights() {
    if (savingWeights) {
      return;
    }

    const positions = collectWeightPositions();
    savingWeights = true;
    showError("");

    try {
      await api.fetchJson(api.withPortfolioId(`${api.API}/portfolio`), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ positions }),
      });

      renderScreen(await loadScreenData());
      window.RiskView?.resetRiskAnalysis();
    } catch (error) {
      showError(error.message);
    } finally {
      savingWeights = false;
    }
  }

  async function deleteFund(isin) {
    showError("");
    try {
      await api.fetchJson(`${api.API}/funds/${encodeURIComponent(isin)}`, {
        method: "DELETE",
      });
      await loadManagement();
      window.RiskView?.resetRiskAnalysis();
    } catch (error) {
      showError(error.message);
    }
  }

  function bindRowActions() {
    document.querySelectorAll("tr[data-isin]").forEach((row) => {
      const nameCell = row.querySelector(".col-name");
      const weightCell = row.querySelector(".col-weight-editable");
      const weightInput = row.querySelector(".weight-input");

      function showActions(focusWeight = false) {
        row.classList.add("row-actions-visible");
        if (focusWeight && weightInput && document.activeElement !== weightInput) {
          weightInput.focus({ preventScroll: true });
          weightInput.select();
        }
      }

      function hideActions() {
        row.classList.remove("row-actions-visible");
      }

      nameCell?.addEventListener("mouseenter", () => showActions(true));
      weightCell?.addEventListener("mouseenter", () => showActions(true));

      row.addEventListener("mouseleave", (event) => {
        if (!row.contains(event.relatedTarget)) {
          weightInput?.blur();
          hideActions();
        }
      });

      weightInput?.addEventListener("focus", () => showActions(false));
    });
  }

  function bindTableInteractions() {
    document.querySelectorAll(".fund-delete-btn").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        deleteFund(button.dataset.isin);
      });
    });

    document.querySelectorAll(".weight-input").forEach((input) => {
      input.addEventListener("focus", () => {
        input.select();
      });
      input.addEventListener("click", () => {
        input.select();
      });
      input.addEventListener("change", () => {
        savePortfolioWeights();
      });
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          input.blur();
        }
      });
    });

    bindRowActions();
  }

  // Chart-only smoothing: trailing moving average for readability. The API and
  // Risk analysis tab always use raw daily returns; only this chart is smoothed.
  // The last point stays exact so end-of-period performance matches QuantStats.
  const CHART_SMOOTH_WINDOW = 5;

  /** Trailing MA for display; final value is never averaged (see above). */
  function smoothSeriesPreserveLast(values, windowSize = CHART_SMOOTH_WINDOW) {
    if (!values.length || windowSize <= 1 || values.length === 1) {
      return values;
    }

    const lastIndex = values.length - 1;
    return values.map((_, index) => {
      if (index === lastIndex) {
        return values[index];
      }

      const start = Math.max(0, index - windowSize + 1);
      let sum = 0;
      for (let i = start; i <= index; i += 1) {
        sum += values[i];
      }
      return sum / (index - start + 1);
    });
  }

  function cumulativeReturn(values) {
    if (!values || !values.length) {
      return null;
    }
    const last = values[values.length - 1];
    return Number.isFinite(last) ? last : null;
  }

  function formatMetricHtml(value, suffix) {
    if (value === null || value === undefined || !Number.isFinite(value)) {
      return "";
    }
    const sign = value < 0 ? "-" : "";
    const number = Math.abs(value).toFixed(2);
    return `&nbsp;${sign}<strong>${number}%</strong>&nbsp;${suffix}`;
  }

  function formatLegendPerformanceHtml(cumulative, annualized) {
    const parts = [];
    const cumulativeLabel = formatMetricHtml(cumulative, "total");
    const annualizedLabel = formatMetricHtml(annualized, "CAGR");
    if (cumulativeLabel) {
      parts.push(cumulativeLabel);
    }
    if (annualizedLabel) {
      parts.push(annualizedLabel);
    }
    return parts.join(",");
  }

  function formatPortfolioLegendHtml(curve) {
    const perf = formatLegendPerformanceHtml(
      cumulativeReturn(curve.portfolio),
      curve.portfolio_annualized_pct,
    );
    return perf ? `Portfolio:${perf}` : "Portfolio";
  }

  function formatBenchmarkLegendHtml(curve) {
    const name = curve.benchmark_name || "S&P 500";
    const isin = curve.benchmark_isin ? ` (${curve.benchmark_isin})` : "";
    const perf = formatLegendPerformanceHtml(
      cumulativeReturn(curve.benchmark),
      curve.benchmark_annualized_pct,
    );
    const base = `${name}${isin}`;
    return perf ? `${base}:${perf}` : base;
  }

  function buildChartConfig(curve) {
    const { labels, portfolio, benchmark, benchmark_name: benchmarkName } = curve;
    const portfolioSeries = smoothSeriesPreserveLast(portfolio);
    const benchmarkSeries =
      benchmark.length > 0 ? smoothSeriesPreserveLast(benchmark) : benchmark;
    const datasets = [
      {
        label: "Portfolio",
        data: portfolioSeries,
        rawValues: portfolio,
        borderColor: "#e91e8c",
        backgroundColor: "rgba(233, 30, 140, 0.08)",
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.1,
      },
    ];

    if (benchmark.length > 0) {
      datasets.push({
        label: benchmarkName || "S&P 500",
        data: benchmarkSeries,
        rawValues: benchmark,
        borderColor: "#1f5eff",
        backgroundColor: "rgba(31, 94, 255, 0.08)",
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.1,
      });
    }

    return {
      type: "line",
      data: {
        labels,
        datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false,
        },
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            boxPadding: 6,
            callbacks: {
              label(context) {
                const rawValues = context.dataset.rawValues;
                const value = rawValues?.[context.dataIndex];
                const displayValue = Number.isFinite(value) ? value : context.parsed.y;
                return `${context.dataset.label}: ${displayValue.toFixed(2)}%`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: {
              color: "rgba(0, 0, 0, 0.06)",
            },
            ticks: {
              maxTicksLimit: 12,
              maxRotation: 0,
            },
          },
          y: {
            grid: {
              color: "rgba(0, 0, 0, 0.06)",
            },
            ticks: {
              callback(value) {
                return Number(value).toFixed(0);
              },
            },
          },
        },
      },
    };
  }

  function renderChart(curve) {
    const canvas = document.getElementById("performance-chart");
    const context = canvas.getContext("2d");

    if (performanceChart) {
      performanceChart.destroy();
    }

    performanceChart = new Chart(context, buildChartConfig(curve));
  }

  function renderScreen({ curve, dashboard, portfolios }) {
    managementData = { curve, dashboard, portfolios };

    updatePortfolioTableTitle(portfolios);

    document.getElementById("portfolio-legend").innerHTML = formatPortfolioLegendHtml(curve);
    document.getElementById("benchmark-legend").innerHTML = formatBenchmarkLegendHtml(curve);
    renderChart(curve);
    renderTableBody("portfolio-body", dashboard.portfolio, { editableWeights: true });
    document.getElementById("portfolio-summary").innerHTML = renderSummaryRow(
      dashboard.portfolio_summary,
    );
    renderTableBody("favorites-body", dashboard.favorites, {
      editableWeights: true,
      forceZeroWeight: true,
    });
    bindTableInteractions();
    scheduleFundTableColumnSync();
  }

  window.addEventListener("resize", () => {
    if (columnSyncTimer !== null) {
      clearTimeout(columnSyncTimer);
    }
    columnSyncTimer = setTimeout(() => {
      columnSyncTimer = null;
      scheduleFundTableColumnSync();
    }, 150);
  });

  async function loadManagement() {
    const loading = document.getElementById("management-loading");
    const view = document.getElementById("management-view");

    loading.hidden = false;
    view.hidden = true;

    try {
      renderScreen(await loadScreenData());
      loading.hidden = true;
      view.hidden = false;
    } catch (error) {
      loading.textContent = "Failed to load dashboard.";
      throw error;
    }
  }

  function resetManagement() {
    managementData = null;
    savingWeights = false;
    if (performanceChart) {
      performanceChart.destroy();
      performanceChart = null;
    }
    document.getElementById("management-loading").hidden = false;
    document.getElementById("management-loading").textContent = "Loading dashboard…";
    document.getElementById("management-view").hidden = true;
    document.getElementById("portfolio-body").innerHTML = "";
    document.getElementById("portfolio-summary").innerHTML = "";
    document.getElementById("favorites-body").innerHTML = "";
  }

  window.ManagementView = {
    loadManagement,
    resetManagement,
  };
})();
