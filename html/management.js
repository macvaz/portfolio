(function () {
  const api = window.PortfolioApi;

  let performanceChart = null;
  let managementData = null;

  const METRIC_COLUMNS = [
    { key: "weight", format: "percent", weightColumn: true },
    { key: "beta_6m", format: "decimal2" },
    { key: "cor_6m", format: "decimal2" },
    { key: "vol_1y", format: "decimal2" },
    { key: "pct_1m", format: "signedPercent" },
    { key: "pct_3m", format: "signedPercent" },
    { key: "pct_6m", format: "signedPercent" },
    { key: "pct_ytd", format: "signedPercent" },
    { key: "sr_6m", format: "decimal2", colorize: true },
    { key: "sr_1y", format: "decimal2", colorize: true },
  ];

  function formatValue(value, format) {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return "—";
    }

    switch (format) {
      case "percent":
        return value.toFixed(2);
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
    return `<a href="#" class="fund-link" data-isin="${fund.isin}">${fund.name}</a>`;
  }

  function renderMetricCells(fund, options = {}) {
    const forceZeroWeight = options.forceZeroWeight === true;
    return METRIC_COLUMNS.map((column) => {
      const value = column.weightColumn && forceZeroWeight ? 0 : fund[column.key];
      const text = formatValue(value, column.format);
      const className = metricClass(value, column);
      return `<td class="${className}">${text}</td>`;
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
      const className = metricClass(value, column);
      return `<td class="${className}">${text}</td>`;
    }).join("");

    return `
    <tr class="summary-row">
      <td class="col-name"><strong>Portfolio</strong></td>
      ${cells}
    </tr>`;
  }

  function renderTableBody(containerId, funds, options = {}) {
    const container = document.getElementById(containerId);
    container.innerHTML = funds.map((fund) => renderFundRow(fund, options)).join("");
  }

  function bindTableInteractions() {
    document.querySelectorAll(".fund-link").forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
      });
    });
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
    renderTableBody("portfolio-body", data.portfolio);
    document.getElementById("portfolio-summary").innerHTML = renderSummaryRow(data.portfolio_summary);
    renderTableBody("favorites-body", data.favorites, { forceZeroWeight: true });
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
