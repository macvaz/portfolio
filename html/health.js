(function () {
  const api = window.PortfolioApi;
  const MONTH_COMPARE_WINDOW = 7;
  const MONTH_COMPARE_WINDOW_SMALL = 2;
  const MONTH_COMPARE_SMALL_QUERY = "(max-width: 720px)";
  let latestHistory = { columns: [], context_columns: [], rows: [] };
  let openCompareMonth = null;

  function monthCompareWindowSize() {
    return window.matchMedia(MONTH_COMPARE_SMALL_QUERY).matches
      ? MONTH_COMPARE_WINDOW_SMALL
      : MONTH_COMPARE_WINDOW;
  }

  function setMacroLoading(isLoading) {
    document.getElementById("macro-loading").hidden = !isLoading;
  }

  function setMacroContent(isVisible) {
    document.getElementById("macro-content").hidden = !isVisible;
  }

  function setMacroMessage(message) {
    const messageEl = document.getElementById("macro-message");
    messageEl.textContent = message;
    messageEl.hidden = !message;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatThreshold(threshold) {
    if (threshold === null || threshold === undefined || !Number.isFinite(threshold)) {
      return "-";
    }
    if (Number.isInteger(threshold)) {
      return String(threshold);
    }
    return threshold.toFixed(2);
  }

  function formatThresholdTooltip(threshold, operator) {
    if (threshold === null || threshold === undefined || !Number.isFinite(threshold)) {
      return null;
    }
    const value = formatThreshold(threshold);
    if (operator === "lt") {
      return `Threshold: < ${value}`;
    }
    if (operator === "lte") {
      return `Threshold: ≤ ${value}`;
    }
    if (operator === "gt") {
      return `Threshold: > ${value}`;
    }
    return `Threshold: ≥ ${value}`;
  }

  function renderHistoryColumnHeader(column) {
    const titleParts = [];
    if (column.description) {
      titleParts.push(column.description);
    }
    const thresholdLabel = formatThresholdTooltip(column.threshold, column.operator);
    if (thresholdLabel) {
      titleParts.push(thresholdLabel);
    }
    if (column.series_start) {
      titleParts.push(`from ${column.series_start}`);
    }
    const title = escapeHtml(titleParts.join(" · "));
    const label = escapeHtml(column.label || column.code);
    if (column.source_url) {
      return `<th class="col-alert-history" title="${title}"><a href="${escapeHtml(column.source_url)}" class="fund-link" target="_blank" rel="noopener noreferrer">${label}</a></th>`;
    }
    return `<th class="col-alert-history" title="${title}">${label}</th>`;
  }

  function formatNumericValue(value) {
    if (!Number.isFinite(value)) {
      return "-";
    }
    return value.toFixed(2);
  }

  function formatMonthLabel(month) {
    if (!month) {
      return "-";
    }
    const [year, monthNumber] = month.split("-").map(Number);
    if (!year || !monthNumber) {
      return month;
    }
    return new Date(year, monthNumber - 1, 1).toLocaleDateString("en-GB", {
      month: "short",
      year: "numeric",
    });
  }

  function formatSp500Value(value) {
    if (!Number.isFinite(value)) {
      return "-";
    }
    return Math.round(value).toLocaleString("en-US");
  }

  function formatReserveBalancesValue(value) {
    if (!Number.isFinite(value)) {
      return "-";
    }
    // FRED WRESBAL is in millions of USD; show trillions.
    return (value / 1_000_000).toFixed(3);
  }

  function formatHistoryValue(value, code) {
    if (code === "SP500") {
      return formatSp500Value(value);
    }
    if (code === "Reserve_Balances") {
      return formatReserveBalancesValue(value);
    }
    return formatNumericValue(value);
  }

  function renderAlertHistoryCell(cell, code) {
    if (!Number.isFinite(cell.value)) {
      return "-";
    }
    const formatted = formatHistoryValue(cell.value, code);
    if (cell.active === null || cell.active === undefined) {
      return formatted;
    }
    if (cell.active) {
      return `<span class="alert-history-value--active">${formatted}</span>`;
    }
    return formatted;
  }

  function renderActiveCountLabel(activeCount, eligibleCount) {
    if (!eligibleCount) {
      return "-";
    }
    const label = `${activeCount ?? 0} of ${eligibleCount}`;
    let statusClass = "inactive";
    if (activeCount > 2) {
      statusClass = "active";
    } else if (activeCount === 2) {
      statusClass = "moderate";
    }
    return `<span class="alert-name alert-name--${statusClass}">${label}</span>`;
  }

  function renderSeriesName(column) {
    const label = escapeHtml(column.label || column.code);
    if (column.source_url) {
      return `<a href="${escapeHtml(column.source_url)}" class="fund-link" target="_blank" rel="noopener noreferrer">${label}</a>`;
    }
    return label;
  }

  function allHistoryColumns(history) {
    return [...(history?.columns || []), ...(history?.context_columns || [])];
  }

  function formatDomainLabel(domain) {
    if (!domain) {
      return "Other";
    }
    return String(domain)
      .split("_")
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }

  function groupColumnsByDomain(columns) {
    const groups = [];
    const indexByDomain = new Map();
    for (const column of columns) {
      const domain = column.domain || null;
      const key = domain || "";
      let group = indexByDomain.get(key);
      if (!group) {
        group = { domain, columns: [] };
        indexByDomain.set(key, group);
        groups.push(group);
      }
      group.columns.push(column);
    }
    const trailing = new Set(["equity_market"]);
    return [
      ...groups.filter((group) => !trailing.has(group.domain)),
      ...groups.filter((group) => trailing.has(group.domain)),
    ].map((group) => ({
      ...group,
      columns: sortColumnsForCompare(group.columns),
    }));
  }

  // Within-domain order for the month-compare table (thresholds + context mixed).
  const COMPARE_SERIES_ORDER = [
    "Treasury_10Y_Yield",
    "Breakeven_Inflation",
    "Real_Interest_Rates",
    "Yield_Spread_10Y3M",
  ];

  function sortColumnsForCompare(columns) {
    const rank = new Map(
      COMPARE_SERIES_ORDER.map((code, index) => [code, index]),
    );
    return [...columns].sort((left, right) => {
      const leftRank = rank.has(left.code) ? rank.get(left.code) : 1000;
      const rightRank = rank.has(right.code) ? rank.get(right.code) : 1000;
      if (leftRank !== rightRank) {
        return leftRank - rightRank;
      }
      return 0;
    });
  }

  function cellForColumn(row, column, history) {
    const alertColumns = history?.columns || [];
    const contextColumns = history?.context_columns || [];
    const alertIndex = alertColumns.findIndex((item) => item.code === column.code);
    if (alertIndex >= 0) {
      return (row?.values || [])[alertIndex] || {};
    }
    const contextIndex = contextColumns.findIndex((item) => item.code === column.code);
    if (contextIndex >= 0) {
      return (row?.context_values || [])[contextIndex] || {};
    }
    return {};
  }

  function slidingWindowRows(history, selectedMonth) {
    const rows = history?.rows || [];
    const selectedIndex = rows.findIndex((row) => row.month === selectedMonth);
    if (selectedIndex < 0) {
      return [];
    }
    // History rows are newest-first; take selected month plus older months.
    const windowSize = monthCompareWindowSize();
    return [...rows.slice(selectedIndex, selectedIndex + windowSize)].reverse();
  }

  function renderMonthCompareSeriesRow(column, windowRows, selectedMonth, history) {
    const titleParts = [];
    if (column.description) {
      titleParts.push(column.description);
    }
    const thresholdLabel = formatThresholdTooltip(column.threshold, column.operator);
    if (thresholdLabel) {
      titleParts.push(thresholdLabel);
    }
    const titleAttr = titleParts.length
      ? ` title="${escapeHtml(titleParts.join(" · "))}"`
      : "";
    const valueCells = windowRows
      .map((row) => {
        const selectedClass =
          row.month === selectedMonth ? " month-detail-month--selected" : "";
        const cell = cellForColumn(row, column, history);
        return `<td class="month-detail-value${selectedClass}">${renderAlertHistoryCell(
          cell,
          column.code
        )}</td>`;
      })
      .join("");
    return `
      <tr>
        <th class="month-detail-series-col" scope="row"${titleAttr}>
          <span class="month-detail-name">${renderSeriesName(column)}</span>
        </th>
        ${valueCells}
      </tr>`;
  }

  function renderMonthCompareTable(selectedMonth, history) {
    const windowRows = slidingWindowRows(history, selectedMonth);
    const columns = allHistoryColumns(history);
    if (!windowRows.length || !columns.length) {
      return `<p class="month-detail-empty">No data for this month.</p>`;
    }

    const monthColSpan = windowRows.length;
    const headerCells = windowRows
      .map((row) => {
        const selectedClass =
          row.month === selectedMonth ? " month-detail-month--selected" : "";
        return `<th class="${selectedClass.trim()}" scope="col">${escapeHtml(
          formatMonthLabel(row.month)
        )}</th>`;
      })
      .join("");

    const bodyRows = groupColumnsByDomain(columns)
      .map((group) => {
        const domainLabel = escapeHtml(formatDomainLabel(group.domain));
        const headerRow = `
          <tr class="month-detail-domain-row">
            <th class="month-detail-domain" scope="colgroup" colspan="${
              monthColSpan + 1
            }">${domainLabel}</th>
          </tr>`;
        const seriesRows = group.columns
          .map((column) =>
            renderMonthCompareSeriesRow(column, windowRows, selectedMonth, history)
          )
          .join("");
        return `${headerRow}${seriesRows}`;
      })
      .join("");

    return `
      <table class="month-detail-table">
        <thead>
          <tr>
            <th class="month-detail-series-col" scope="col">Series</th>
            ${headerCells}
          </tr>
        </thead>
        <tbody>
          ${bodyRows}
        </tbody>
      </table>`;
  }

  function closeMonthDetail() {
    const screen = document.getElementById("month-detail-screen");
    if (!screen) {
      return;
    }
    openCompareMonth = null;
    screen.hidden = true;
    document.body.classList.remove("is-month-detail-open");
  }

  function openMonthDetail(month) {
    const screen = document.getElementById("month-detail-screen");
    const titleEl = document.getElementById("month-detail-title");
    const listEl = document.getElementById("month-detail-list");
    if (!screen || !titleEl || !listEl) {
      return;
    }

    const windowRows = slidingWindowRows(latestHistory, month);
    if (!windowRows.length) {
      return;
    }

    const startLabel = formatMonthLabel(windowRows[0].month);
    const endLabel = formatMonthLabel(windowRows[windowRows.length - 1].month);
    titleEl.textContent =
      windowRows.length === 1 ? endLabel : `${startLabel} – ${endLabel}`;
    listEl.innerHTML = renderMonthCompareTable(month, latestHistory);
    openCompareMonth = month;
    screen.hidden = false;
    document.body.classList.add("is-month-detail-open");
  }

  function renderMonthMetricRows(row, columns) {
    return columns
      .map((column, index) => {
        const cell = (row.values || [])[index] || {};
        const label = escapeHtml(column.label || column.code);
        return `
          <div class="macro-month-metric">
            <span class="macro-month-metric-label">${label}</span>
            <span class="macro-month-metric-value">${renderAlertHistoryCell(cell, column.code)}</span>
          </div>`;
      })
      .join("");
  }

  function renderMonthCard(row, columns, options = {}) {
    const isCurrent = options.isCurrent === true;
    const monthLabel = escapeHtml(formatMonthLabel(row.month));
    const title = isCurrent ? `Current month — ${monthLabel}` : monthLabel;
    const activeCount = row.active_count ?? 0;
    const eligibleCount = row.eligible_count ?? 0;
    return `
      <article
        class="macro-month-card${isCurrent ? " macro-month-card--current" : ""}"
        data-month="${escapeHtml(row.month)}"
        role="button"
        tabindex="0"
        aria-label="Open month compare for ${monthLabel}"
      >
        <header class="macro-month-card-header">
          <h3 class="macro-month-card-title">${title}</h3>
          <div class="macro-month-card-risk">${renderActiveCountLabel(activeCount, eligibleCount)}</div>
        </header>
        <div class="macro-month-metrics">
          ${renderMonthMetricRows(row, columns)}
        </div>
      </article>`;
  }

  function renderAlertHistoryCards(history) {
    const container = document.getElementById("macro-month-cards");
    if (!container) {
      return;
    }

    const columns = history?.columns || [];
    const rows = history?.rows || [];
    if (!rows.length || !columns.length) {
      container.innerHTML = "";
      return;
    }

    const currentRow = rows[0];
    const previousRows = rows.slice(1, 13);
    const previousCards = previousRows
      .map((row) => renderMonthCard(row, columns))
      .join("");
    const previousSection = previousRows.length
      ? `<h3 class="macro-months-label">Previous 12 months</h3>${previousCards}`
      : "";

    container.innerHTML = `
      ${renderMonthCard(currentRow, columns, { isCurrent: true })}
      ${previousSection}`;
  }

  function renderAlertHistory(history) {
    latestHistory = history || { columns: [], context_columns: [], rows: [] };
    const columns = latestHistory.columns || [];
    const rows = latestHistory.rows || [];
    const thead = document.getElementById("alerts-status-head");
    const tbody = document.getElementById("alerts-status-body");

    const headerCells = columns.map((column) => renderHistoryColumnHeader(column)).join("");

    thead.innerHTML = `
      <tr>
        <th class="col-month">Month</th>
        ${headerCells}
        <th class="col-alert-active-count">Risk level</th>
      </tr>`;

    tbody.innerHTML = rows
      .map((row) => {
        const valueCells = columns
          .map((column, index) => {
            const cell = (row.values || [])[index] || {};
            return `<td class="col-value">${renderAlertHistoryCell(cell, column.code)}</td>`;
          })
          .join("");
        const activeCount = row.active_count ?? 0;
        const eligibleCount = row.eligible_count ?? 0;
        const monthLabel = escapeHtml(formatMonthLabel(row.month));
        return `
          <tr>
            <td class="col-month">
              <button
                type="button"
                class="month-select-btn"
                data-month="${escapeHtml(row.month)}"
              >${monthLabel}</button>
            </td>
            ${valueCells}
            <td class="col-alert-active-count">${renderActiveCountLabel(activeCount, eligibleCount)}</td>
          </tr>`;
      })
      .join("");

    renderAlertHistoryCards(latestHistory);
  }

  function renderMacro(snapshot) {
    const asOf = document.getElementById("macro-as-of");
    const items = snapshot.items || [];
    const history = snapshot.history || { columns: [], context_columns: [], rows: [] };
    const hasData =
      snapshot.date &&
      (items.length > 0 || history.rows.length > 0);

    if (!hasData) {
      setMacroContent(false);
      setMacroMessage("No macro health data yet. Run the data job to compute it.");
      renderAlertHistory({ columns: [], context_columns: [], rows: [] });
      asOf.textContent = "";
      closeMonthDetail();
      return;
    }

    setMacroMessage("");
    setMacroContent(true);
    asOf.textContent = snapshot.date ? `- as of ${snapshot.date}` : "";
    renderAlertHistory(history);
  }

  async function loadMacroHealth() {
    setMacroLoading(true);
    setMacroMessage("");

    try {
      const snapshot = await api.fetchJson(api.MACRO_API);
      renderMacro(snapshot);
    } catch (error) {
      setMacroContent(false);
      setMacroMessage(error.message);
    } finally {
      setMacroLoading(false);
    }
  }

  function bindMonthDetailUi() {
    const screen = document.getElementById("month-detail-screen");
    const closeBtn = document.getElementById("month-detail-close");
    const table = document.getElementById("alerts-status-table");
    const cards = document.getElementById("macro-month-cards");

    closeBtn?.addEventListener("click", closeMonthDetail);
    screen?.addEventListener("click", (event) => {
      if (event.target === screen) {
        closeMonthDetail();
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeMonthDetail();
      }
    });

    table?.addEventListener("click", (event) => {
      const button = event.target.closest(".month-select-btn");
      if (!button) {
        return;
      }
      openMonthDetail(button.dataset.month);
    });

    cards?.addEventListener("click", (event) => {
      if (event.target.closest("a")) {
        return;
      }
      const card = event.target.closest(".macro-month-card[data-month]");
      if (!card) {
        return;
      }
      openMonthDetail(card.dataset.month);
    });

    cards?.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") {
        return;
      }
      const card = event.target.closest(".macro-month-card[data-month]");
      if (!card) {
        return;
      }
      event.preventDefault();
      openMonthDetail(card.dataset.month);
    });

    const smallScreenQuery = window.matchMedia(MONTH_COMPARE_SMALL_QUERY);
    const onCompareWindowChange = () => {
      if (openCompareMonth) {
        openMonthDetail(openCompareMonth);
      }
    };
    if (typeof smallScreenQuery.addEventListener === "function") {
      smallScreenQuery.addEventListener("change", onCompareWindowChange);
    } else if (typeof smallScreenQuery.addListener === "function") {
      smallScreenQuery.addListener(onCompareWindowChange);
    }
  }

  bindMonthDetailUi();

  window.MacroView = {
    loadMacroHealth,
  };
})();
