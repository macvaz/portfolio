(function () {
  const api = window.PortfolioApi;

  let performanceChart = null;
  let managementData = null;
  let savingWeights = false;
  let saveWeightsTimer = null;
  let saveWeightsStartedAt = null;
  let curveStartDate = null;

  const METRIC_COLUMNS = [
    { key: "weight", format: "percent", weightColumn: true, beforeDivider: true, label: "Weight (%)" },
    { key: "pct_1w", format: "signedPercent", divider: true, label: "% 1w" },
    { key: "pct_1m", format: "signedPercent", label: "% 1m" },
    { key: "pct_6m", format: "signedPercent", label: "% 6m" },
    { key: "pct_ytd", format: "signedPercent", beforeDivider: true, label: "% YTD", columnClass: "col-ytd" },
    {
      key: "vol_1y",
      format: "decimal2",
      divider: true,
      label: "Vol (1y)",
      columnClass: "col-metric-vol",
    },
    { key: "beta_6m", format: "decimal2", label: "β (6m)", columnClass: "col-metric-beta" },
    { key: "cor_6m", format: "decimal2", label: "Cor (6m)", columnClass: "col-metric-cor" },
    { key: "sr_6m", format: "decimal2", label: "SR 6m", columnClass: "col-metric-sr" },
    { key: "sr_1y", format: "decimal2", label: "SR 1y", columnClass: "col-metric-sr" },
  ];

  const MOBILE_CARDS_MQ = window.matchMedia("(max-width: 720px)");
  const MID_WIDTH_MQ = window.matchMedia("(min-width: 721px) and (max-width: 1200px)");
  // Phones/tablets in any orientation — width alone fails in landscape.
  const TOUCH_PRIMARY_MQ = window.matchMedia("(hover: none) and (pointer: coarse)");

  function canSetChartStartDate() {
    return !MOBILE_CARDS_MQ.matches && !TOUCH_PRIMARY_MQ.matches;
  }

  function showError(message) {
    const el = document.getElementById("error");
    if (!el) return;
    el.textContent = message;
    el.hidden = !message;
  }

  function setSavingWeightsUi(isSaving) {
    const loading = document.getElementById("management-loading");
    const view = document.getElementById("management-view");

    if (saveWeightsTimer !== null) {
      clearInterval(saveWeightsTimer);
      saveWeightsTimer = null;
    }

    if (!isSaving) {
      saveWeightsStartedAt = null;
      if (managementData) {
        loading.hidden = true;
        view.hidden = false;
      }
      return;
    }

    saveWeightsStartedAt = Date.now();
    loading.hidden = false;
    view.hidden = true;

    const tick = () => {
      const seconds = Math.floor((Date.now() - saveWeightsStartedAt) / 1000);
      loading.textContent = `Saving portfolio and generating risk report… ${seconds}s`;
    };
    tick();
    saveWeightsTimer = setInterval(tick, 1000);
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

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function fundDisplayName(fund) {
    // Names may arrive already entity-encoded from older imports.
    const raw = String(fund?.name || fund?.isin || "");
    const textarea = document.createElement("textarea");
    textarea.innerHTML = raw;
    return textarea.value;
  }

  function renderFundName(fund) {
    const name = escapeHtml(fundDisplayName(fund));
    const nameLink = fund.morningstar_url
      ? `<a href="${fund.morningstar_url}" class="fund-link" target="_blank" rel="noopener noreferrer">${name}</a>`
      : `<span class="fund-name">${name}</span>`;
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
      column.columnClass || "",
      column.beforeDivider ? "col-before-divider" : "",
      column.divider ? "col-divider" : "",
    ]
      .filter(Boolean)
      .join(" ");
  }

  function renderWeightInputCell(isin, weight, label) {
    const display = formatWeight(weight);
    return `<td class="col-weight col-weight-editable col-before-divider" data-label="${label}">
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
        return renderWeightInputCell(fund.isin, weight, column.label);
      }

      const value = column.weightColumn && forceZeroWeight ? 0 : fund[column.key];
      const text = formatValue(value, column.format);
      return `<td class="${cellClasses(value, column)}" data-label="${column.label}"><span class="metric-value">${text}</span></td>`;
    }).join("");
  }

  function renderFundRow(fund, options = {}) {
    return `
    <tr data-isin="${fund.isin}">
      <td class="col-name">${renderFundName(fund)}</td>
      ${renderMetricCells(fund, options)}
    </tr>`;
  }

  function renderSummaryWeightCell(value, label) {
    const text = formatWeight(value);
    return `<td class="col-weight col-weight-editable col-before-divider" data-label="${label}">
      <div class="weight-cell-slot">
        <span class="weight-display">${text}</span>
      </div>
    </td>`;
  }

  function renderSummaryRow(summary) {
    const cells = METRIC_COLUMNS.map((column) => {
      const value = summary[column.key];
      if (column.weightColumn) {
        return renderSummaryWeightCell(value, column.label);
      }
      const text = formatValue(value, column.format);
      return `<td class="${cellClasses(value, column)}" data-label="${column.label}"><span class="metric-value">${text}</span></td>`;
    }).join("");

    const hasTer =
      summary.ter !== null && summary.ter !== undefined && !Number.isNaN(summary.ter);
    const terText = hasTer ? Number(summary.ter).toFixed(2) : "—";

    return `
    <tr class="summary-row">
      <td class="col-name"></td>
      ${cells}
      <td class="col-portfolio-ter" data-label="% TER"><span class="metric-value">${terText}</span></td>
    </tr>`;
  }

  function buildFundNumberIds(funds) {
    const byIsin = new Map();
    funds.forEach((fund, index) => {
      byIsin.set(fund.isin, index + 1);
    });
    return byIsin;
  }

  function correlationCellClass(value) {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return "";
    }
    if (value < 0) {
      return "corr-negative";
    }
    if (value < 0.5) {
      return "corr-low";
    }
    if (value < 0.75) {
      return "corr-mid";
    }
    return "corr-high";
  }

  function renderCorrelationMatrixRow(correlation, fundIds) {
    if (
      !correlation ||
      !Array.isArray(correlation.labels) ||
      correlation.labels.length < 2 ||
      !Array.isArray(correlation.matrix)
    ) {
      return "";
    }

    const labels = correlation.labels.map((item, index) => ({
      isin: item.isin,
      name: item.name || item.isin,
      id: fundIds?.get(item.isin) ?? index + 1,
    }));

    // Lower triangle only (no diagonal): columns are funds 0..n-2, rows are 1..n-1.
    const columnLabels = labels.slice(0, -1);
    const headerCells = columnLabels
      .map(
        (label) =>
          `<th scope="col" title="${escapeHtml(label.name)}">${label.id}</th>`,
      )
      .join("");

    const bodyRows = labels
      .slice(1)
      .map((rowLabel, offset) => {
        const rowIndex = offset + 1;
        const values = correlation.matrix[rowIndex] || [];
        const cells = columnLabels
          .map((colLabel, colIndex) => {
            if (colIndex >= rowIndex) {
              return `<td class="corr-empty" aria-hidden="true"></td>`;
            }
            const value = values[colIndex];
            const text = formatValue(value, "decimal2");
            const cls = correlationCellClass(value);
            return `<td class="${cls}" title="${escapeHtml(rowLabel.name)} × ${escapeHtml(colLabel.name)}">${text}</td>`;
          })
          .join("");
        return `<tr><th scope="row" title="${escapeHtml(rowLabel.name)}">${rowLabel.id}</th>${cells}</tr>`;
      })
      .join("");

    return `
    <tr class="correlation-matrix-row">
      <td class="correlation-matrix-card" colspan="${METRIC_COLUMNS.length + 1}">
        <div class="correlation-matrix-scroll">
          <table class="correlation-matrix-table">
            <thead>
              <tr>
                <th scope="col"></th>
                ${headerCells}
              </tr>
            </thead>
            <tbody>${bodyRows}</tbody>
          </table>
        </div>
      </td>
    </tr>`;
  }

  function renderWeightsSummaryRow(funds) {
    const items = funds
      .map((fund, index) => {
        const id = index + 1;
        const name = escapeHtml(fundDisplayName(fund));
        const nameHtml = fund.morningstar_url
          ? `<a href="${fund.morningstar_url}" class="fund-link weights-summary-name" target="_blank" rel="noopener noreferrer">${name}</a>`
          : `<span class="fund-name weights-summary-name">${name}</span>`;
        return `
      <div class="weights-summary-item">
        <span class="weights-summary-id" aria-label="Fund ${id}">${id}</span>
        ${nameHtml}
        <span class="metric-value">${formatWeight(fund.weight)}%</span>
      </div>`;
      })
      .join("");

    return `
    <tr class="weights-summary-row">
      <td class="weights-summary-card" colspan="${METRIC_COLUMNS.length + 1}">
        <div class="weights-summary-list">${items}</div>
      </td>
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
      ...table.querySelectorAll(
        "tfoot tr:not(.weights-summary-row):not(.correlation-matrix-row)",
      ),
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

    // Mobile cards and mid-width (CSS-hidden columns) use auto layout.
    // Fixed col sync + display:none columns overlaps content.
    if (MOBILE_CARDS_MQ.matches || MID_WIDTH_MQ.matches) {
      return;
    }

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

  async function fetchCurve(startDate = null) {
    let path = `${api.PORTFOLIO_API}/curve`;
    if (startDate) {
      path += `?start_date=${encodeURIComponent(startDate)}`;
    }
    return api.fetchJson(api.withPortfolioId(path));
  }

  async function loadScreenData() {
    const [curve, metrics, portfolios] = await Promise.all([
      fetchCurve(curveStartDate),
      api.fetchJson(api.withPortfolioId(`${api.PORTFOLIO_API}/metrics`)),
      api.fetchJson(`${api.PORTFOLIO_API}/portfolios`),
    ]);
    return { curve, metrics, portfolios };
  }

  async function applyCurveStartDate(startDate) {
    showError("");
    try {
      const curve = await fetchCurve(startDate);
      curveStartDate = startDate;
      if (managementData) {
        managementData.curve = curve;
      }
      document.getElementById("portfolio-legend").innerHTML = formatPortfolioLegendHtml(curve);
      document.getElementById("benchmark-legend").innerHTML = formatBenchmarkLegendHtml(curve);
      renderChart(curve);
      window.RiskView?.resetRiskAnalysis();
    } catch (error) {
      showError(error.message);
    }
  }

  function updatePortfolioTableMeta(metrics) {
    const asOfEl = document.getElementById("portfolio-table-as-of");
    const terEl = document.getElementById("portfolio-table-ter");
    const sepEl = document.getElementById("portfolio-table-meta-sep");
    const asOf = metrics?.as_of;
    const ter = metrics?.portfolio_summary?.ter;

    let hasAsOf = false;
    if (asOfEl) {
      if (asOf) {
        asOfEl.textContent = `as of ${asOf}`;
        asOfEl.hidden = false;
        hasAsOf = true;
      } else {
        asOfEl.textContent = "";
        asOfEl.hidden = true;
      }
    }

    let hasTer = false;
    if (terEl) {
      const validTer = ter !== null && ter !== undefined && !Number.isNaN(ter);
      if (validTer) {
        terEl.textContent = `TER ${Number(ter).toFixed(2)} %`;
        terEl.hidden = false;
        hasTer = true;
      } else {
        terEl.hidden = true;
        terEl.textContent = "";
      }
    }

    if (sepEl) {
      sepEl.hidden = !(hasTer && hasAsOf);
    }
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
    setSavingWeightsUi(true);

    try {
      await api.fetchJson(api.withPortfolioId(`${api.PORTFOLIO_API}/positions`), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ positions }),
      });

      renderScreen(await loadScreenData());
      window.RiskView?.resetRiskAnalysis();
    } catch (error) {
      showError(error.message);
    } finally {
      setSavingWeightsUi(false);
      savingWeights = false;
    }
  }

  async function deleteFund(isin) {
    showError("");
    try {
      await api.fetchJson(`${api.PORTFOLIO_API}/funds/${encodeURIComponent(isin)}`, {
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
      const weightCell = row.querySelector(".col-weight-editable");
      const weightInput = row.querySelector(".weight-input");

      function showWeightEdit(focusWeight = false) {
        row.classList.add("row-weight-visible");
        if (focusWeight && weightInput && document.activeElement !== weightInput) {
          weightInput.focus({ preventScroll: true });
          weightInput.select();
        }
      }

      function hideWeightEdit() {
        row.classList.remove("row-weight-visible");
      }

      weightCell?.addEventListener("mouseenter", () => showWeightEdit(true));

      weightCell?.addEventListener("mouseleave", (event) => {
        if (weightCell.contains(event.relatedTarget)) {
          return;
        }
        if (document.activeElement === weightInput) {
          return;
        }
        hideWeightEdit();
      });

      row.addEventListener("mouseleave", (event) => {
        if (!row.contains(event.relatedTarget)) {
          weightInput?.blur();
          hideWeightEdit();
        }
      });

      weightInput?.addEventListener("focus", () => showWeightEdit(false));

      weightInput?.addEventListener("blur", () => {
        if (!weightCell?.matches(":hover")) {
          hideWeightEdit();
        }
      });
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
  // Risk report tab always use raw daily returns; only this chart is smoothed.
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

  function dailyReturnFromCumulative(values, index) {
    if (!values || index < 1) {
      return null;
    }
    const previous = values[index - 1];
    const current = values[index];
    if (!Number.isFinite(previous) || !Number.isFinite(current)) {
      return null;
    }
    return ((1 + current / 100) / (1 + previous / 100) - 1) * 100;
  }

  function formatSignedPercent(value, digits = 2) {
    if (!Number.isFinite(value)) {
      return "—";
    }
    const sign = value < 0 ? "-" : "";
    return `${sign}${Math.abs(value).toFixed(digits)}%`;
  }

  function formatTooltipLineHtml(label, color, totalValue, dayValue) {
    const totalText = formatSignedPercent(totalValue);
    const dayText = dayValue === null ? "—" : formatSignedPercent(dayValue);
    return (
      `<span class="chart-tooltip-swatch" style="background:${color}"></span>` +
      `<span class="chart-tooltip-text">${label}: <strong>${totalText}</strong> total, <strong>${dayText}</strong> day</span>`
    );
  }

  function getOrCreateChartTooltip() {
    return document.getElementById("chart-tooltip");
  }

  function positionChartTooltip(tooltipEl, chart, tooltip) {
    const GAP = 12;
    const canvas = chart.canvas;
    const caretX = canvas.offsetLeft + tooltip.caretX;
    const caretY = canvas.offsetTop + tooltip.caretY;
    const areaLeft = canvas.offsetLeft;
    const areaTop = canvas.offsetTop;
    const areaRight = areaLeft + canvas.offsetWidth;
    const areaBottom = areaTop + canvas.offsetHeight;

    tooltipEl.style.left = "0px";
    tooltipEl.style.top = "0px";
    tooltipEl.style.transform = "none";
    const tipW = tooltipEl.offsetWidth;
    const tipH = tooltipEl.offsetHeight;

    const spaceRight = areaRight - caretX - GAP;
    const spaceLeft = caretX - areaLeft - GAP;
    let left =
      spaceRight >= tipW || spaceRight >= spaceLeft
        ? caretX + GAP
        : caretX - GAP - tipW;
    left = Math.min(Math.max(left, areaLeft), Math.max(areaLeft, areaRight - tipW));

    let top = caretY - tipH / 2;
    top = Math.min(Math.max(top, areaTop), Math.max(areaTop, areaBottom - tipH));

    tooltipEl.style.left = `${left}px`;
    tooltipEl.style.top = `${top}px`;
  }

  function externalChartTooltip(context) {
    const tooltipEl = getOrCreateChartTooltip();
    if (!tooltipEl) {
      return;
    }

    const { chart, tooltip } = context;
    if (tooltip.opacity === 0) {
      tooltipEl.hidden = true;
      return;
    }

    const title = tooltip.title?.[0] || "";
    const lines = (tooltip.dataPoints || []).map((point) => {
      const rawValues = point.dataset.rawValues;
      const index = point.dataIndex;
      const value = rawValues?.[index];
      const displayValue = Number.isFinite(value) ? value : point.parsed.y;
      const dayReturn = dailyReturnFromCumulative(rawValues, index);
      const color = point.dataset.borderColor || point.dataset.backgroundColor || "#888";
      return formatTooltipLineHtml(
        point.dataset.label,
        color,
        displayValue,
        dayReturn,
      );
    });

    tooltipEl.innerHTML = [
      title ? `<div class="chart-tooltip-title">${title}</div>` : "",
      ...lines.map((line) => `<div class="chart-tooltip-line">${line}</div>`),
    ].join("");

    tooltipEl.hidden = false;
    tooltipEl.style.opacity = String(tooltip.opacity);
    positionChartTooltip(tooltipEl, chart, tooltip);
  }

  function formatMetricHtml(value, suffix) {
    if (value === null || value === undefined || !Number.isFinite(value)) {
      return "";
    }
    const sign = value < 0 ? "-" : "";
    const number = Math.abs(value).toFixed(2);
    return `&nbsp;${sign}<strong>${number}%</strong>&nbsp;${suffix}`;
  }

  function formatLegendPerformanceHtml(cumulative, annualized, volatility) {
    const parts = [];
    const cumulativeLabel = formatMetricHtml(cumulative, "total");
    const annualizedLabel = formatMetricHtml(annualized, "CAGR");
    const volatilityLabel = formatMetricHtml(volatility, "Vol");
    if (cumulativeLabel) {
      parts.push(cumulativeLabel);
    }
    if (annualizedLabel) {
      parts.push(annualizedLabel);
    }
    if (volatilityLabel) {
      parts.push(volatilityLabel);
    }
    return parts.join(",");
  }

  function formatPortfolioLegendHtml(curve) {
    const perf = formatLegendPerformanceHtml(
      cumulativeReturn(curve.portfolio),
      curve.portfolio_annualized_pct,
      curve.portfolio_volatility_pct,
    );
    return perf ? `Portfolio:${perf}` : "Portfolio";
  }

  function formatBenchmarkLegendHtml(curve) {
    const name = curve.benchmark_name || "S&P 500";
    const perf = formatLegendPerformanceHtml(
      cumulativeReturn(curve.benchmark),
      curve.benchmark_annualized_pct,
      curve.benchmark_volatility_pct,
    );
    return perf ? `${name}:${perf}` : name;
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
        borderColor: "#348dc1",
        backgroundColor: "rgba(52, 141, 193, 0.08)",
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
        borderColor: "#c9a227",
        backgroundColor: "rgba(201, 162, 39, 0.08)",
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
        onClick(event, _elements, chart) {
          if (!canSetChartStartDate()) {
            return;
          }
          const points = chart.getElementsAtEventForMode(
            event,
            "index",
            { intersect: false },
            true,
          );
          if (!points.length) {
            return;
          }
          const label = chart.data.labels[points[0].index];
          if (!label || label === curveStartDate) {
            return;
          }
          applyCurveStartDate(label);
        },
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            enabled: false,
            external: externalChartTooltip,
          },
        },
        scales: {
          x: {
            grid: {
              color: "rgba(0, 0, 0, 0.06)",
            },
            ticks: {
              align: "start",
              maxTicksLimit: 12,
              maxRotation: 0,
              callback(value) {
                const label = this.getLabelForValue(value);
                if (typeof label === "string" && /^\d{4}-\d{2}/.test(label)) {
                  return label.slice(0, 7);
                }
                return label;
              },
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
    canvas.title = canSetChartStartDate() && curveStartDate
      ? `From ${curveStartDate} — double-click to reset`
      : "";
    canvas.ondblclick = () => {
      if (canSetChartStartDate() && curveStartDate) {
        applyCurveStartDate(null);
      }
    };
  }

  function renderScreen({ curve, metrics, portfolios }) {
    managementData = { curve, metrics, portfolios };

    updatePortfolioTableTitle(portfolios);
    updatePortfolioTableMeta(metrics);

    document.getElementById("portfolio-legend").innerHTML = formatPortfolioLegendHtml(curve);
    document.getElementById("benchmark-legend").innerHTML = formatBenchmarkLegendHtml(curve);
    renderChart(curve);
    renderTableBody("portfolio-body", metrics.portfolio, { editableWeights: true });
    const fundIds = buildFundNumberIds(metrics.portfolio);
    document.getElementById("portfolio-summary").innerHTML =
      renderWeightsSummaryRow(metrics.portfolio) +
      renderSummaryRow(metrics.portfolio_summary) +
      renderCorrelationMatrixRow(metrics.correlation_matrix, fundIds);
    renderTableBody("favorites-body", metrics.favorites, {
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

  if (typeof MOBILE_CARDS_MQ.addEventListener === "function") {
    MOBILE_CARDS_MQ.addEventListener("change", scheduleFundTableColumnSync);
    MID_WIDTH_MQ.addEventListener("change", scheduleFundTableColumnSync);
  } else if (typeof MOBILE_CARDS_MQ.addListener === "function") {
    MOBILE_CARDS_MQ.addListener(scheduleFundTableColumnSync);
    MID_WIDTH_MQ.addListener(scheduleFundTableColumnSync);
  }

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
      loading.textContent = "Failed to load metrics.";
      throw error;
    }
  }

  function resetManagement() {
    managementData = null;
    savingWeights = false;
    setSavingWeightsUi(false);
    curveStartDate = null;
    if (performanceChart) {
      performanceChart.destroy();
      performanceChart = null;
    }
    document.getElementById("management-loading").hidden = false;
    document.getElementById("management-loading").textContent = "Loading metrics…";
    document.getElementById("management-view").hidden = true;
    document.getElementById("portfolio-body").innerHTML = "";
    document.getElementById("portfolio-summary").innerHTML = "";
    document.getElementById("favorites-body").innerHTML = "";
    updatePortfolioTableMeta(null);
  }

  window.ManagementView = {
    loadManagement,
    resetManagement,
    getCurveStartDate() {
      return curveStartDate;
    },
  };
})();
