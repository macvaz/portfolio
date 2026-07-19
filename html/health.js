(function () {
  const api = window.PortfolioApi;

  function setTacticalLoading(isLoading) {
    document.getElementById("tactical-loading").hidden = !isLoading;
  }

  function setTacticalContent(isVisible) {
    document.getElementById("tactical-content").hidden = !isVisible;
  }

  function setTacticalMessage(message) {
    const messageEl = document.getElementById("tactical-message");
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

  function renderAlertHistoryCell(cell, code) {
    if (!Number.isFinite(cell.value)) {
      return "-";
    }
    const formatted =
      code === "SP500" ? formatSp500Value(cell.value) : formatNumericValue(cell.value);
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

  function renderMonthMetricRows(row, columns) {
    return columns
      .map((column, index) => {
        const cell = (row.values || [])[index] || {};
        const label = escapeHtml(column.label || column.code);
        return `
          <div class="tactical-month-metric">
            <span class="tactical-month-metric-label">${label}</span>
            <span class="tactical-month-metric-value">${renderAlertHistoryCell(cell, column.code)}</span>
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
      <article class="tactical-month-card${isCurrent ? " tactical-month-card--current" : ""}">
        <header class="tactical-month-card-header">
          <h3 class="tactical-month-card-title">${title}</h3>
          <div class="tactical-month-card-risk">${renderActiveCountLabel(activeCount, eligibleCount)}</div>
        </header>
        <div class="tactical-month-metrics">
          ${renderMonthMetricRows(row, columns)}
        </div>
      </article>`;
  }

  function renderAlertHistoryCards(history) {
    const container = document.getElementById("tactical-month-cards");
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
      ? `<h3 class="tactical-months-label">Previous 12 months</h3>${previousCards}`
      : "";

    container.innerHTML = `
      ${renderMonthCard(currentRow, columns, { isCurrent: true })}
      ${previousSection}`;
  }

  function renderAlertHistory(history) {
    const columns = history?.columns || [];
    const rows = history?.rows || [];
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
        return `
          <tr>
            <td class="col-month">${escapeHtml(formatMonthLabel(row.month))}</td>
            ${valueCells}
            <td class="col-alert-active-count">${renderActiveCountLabel(activeCount, eligibleCount)}</td>
          </tr>`;
      })
      .join("");

    renderAlertHistoryCards(history);
  }

  function renderAlerts(snapshot) {
    const asOf = document.getElementById("tactical-as-of");
    const alerts = snapshot.alerts || [];
    const history = snapshot.history || { columns: [], rows: [] };
    const hasData =
      snapshot.date &&
      (alerts.length > 0 || history.rows.length > 0);

    if (!hasData) {
      setTacticalContent(false);
      setTacticalMessage("No macro health data yet. Run the data job to compute it.");
      renderAlertHistory({ columns: [], rows: [] });
      asOf.textContent = "";
      return;
    }

    setTacticalMessage("");
    setTacticalContent(true);
    asOf.textContent = snapshot.date ? `— as of ${snapshot.date}` : "";
    renderAlertHistory(history);
  }

  async function loadTacticalAlerts() {
    setTacticalLoading(true);
    setTacticalMessage("");

    try {
      const snapshot = await api.fetchJson(api.ALERTS_API);
      renderAlerts(snapshot);
    } catch (error) {
      setTacticalContent(false);
      setTacticalMessage(error.message);
    } finally {
      setTacticalLoading(false);
    }
  }

  window.TacticalView = {
    loadTacticalAlerts,
    loadTacticalSignals: loadTacticalAlerts,
  };
})();
