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
    return `
      <div class="fund-name-wrap">
        <a href="#" class="fund-link" data-isin="${fund.isin}">${fund.name}</a>
        <div class="fund-delete-popup" role="tooltip">
          <button type="button" class="fund-delete-btn" data-isin="${fund.isin}">Delete</button>
        </div>
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

  function renderSummaryRow(summary) {
    const cells = METRIC_COLUMNS.map((column) => {
      const value = summary[column.key];
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

  async function savePortfolioWeights() {
    if (savingWeights) {
      return;
    }

    const positions = collectWeightPositions();
    savingWeights = true;
    showError("");

    try {
      await api.fetchJson(`${api.API}/portfolio`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ positions }),
      });

      const data = await api.fetchJson(`${api.API}/management`);
      renderManagement(data);
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
    document.querySelectorAll(".fund-link").forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
      });
    });

    document.querySelectorAll(".fund-delete-btn").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        deleteFund(button.dataset.isin);
      });
    });

    document.querySelectorAll(".weight-input").forEach((input) => {
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

  function buildChartConfig(data) {
    const { labels, portfolio, benchmark } = data.chart;

    return {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Portfolio",
            data: portfolio,
            borderColor: "#e91e8c",
            backgroundColor: "rgba(233, 30, 140, 0.08)",
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.15,
          },
          {
            label: data.benchmark_name,
            data: benchmark,
            borderColor: "#1f5eff",
            backgroundColor: "rgba(31, 94, 255, 0.08)",
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.15,
          },
        ],
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
            callbacks: {
              label(context) {
                return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}`;
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

  function renderChart(data) {
    const canvas = document.getElementById("performance-chart");
    const context = canvas.getContext("2d");

    if (performanceChart) {
      performanceChart.destroy();
    }

    performanceChart = new Chart(context, buildChartConfig(data));
  }

  function renderManagement(data) {
    managementData = data;

    document.getElementById("benchmark-legend").textContent = data.benchmark_name;
    renderChart(data);
    renderTableBody("portfolio-body", data.portfolio, { editableWeights: true });
    document.getElementById("portfolio-summary").innerHTML = renderSummaryRow(data.portfolio_summary);
    renderTableBody("favorites-body", data.favorites, {
      editableWeights: true,
      forceZeroWeight: true,
    });
    bindTableInteractions();
  }

  async function loadManagement() {
    const loading = document.getElementById("management-loading");
    const view = document.getElementById("management-view");

    loading.hidden = false;
    view.hidden = true;

    try {
      const data = await api.fetchJson(`${api.API}/management`);
      renderManagement(data);
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
