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

  function renderSeriesIdentifier(series) {
    const label = series.label || series.identifier || series.code;
    const title = series.identifier && series.label !== series.identifier
      ? series.identifier
      : "";
    if (series.source_url) {
      return `<a href="${series.source_url}" class="fund-link" target="_blank" rel="noopener noreferrer" title="${escapeHtml(title)}">${escapeHtml(label)}</a>`;
    }
    return escapeHtml(label);
  }

  function formatSeriesStart(seriesStart) {
    if (!seriesStart) {
      return "-";
    }
    return seriesStart;
  }

  function renderSeriesRow(series) {
    return `
      <tr>
        <td class="col-name" data-label="Series">${renderSeriesIdentifier(series)}</td>
        <td class="col-name col-description" data-label="Description" title="${escapeHtml(series.description)}">${escapeHtml(series.description)}</td>
        <td class="col-series-start" data-label="Start">${formatSeriesStart(series.series_start)}</td>
        <td class="col-alert-threshold" data-label="Threshold">${formatThreshold(series.threshold)}</td>
      </tr>`;
  }

  function renderAlertBadge(content, active) {
    const statusClass = active ? "active" : "inactive";
    return `<span class="alert-name alert-name--${statusClass}">${content}</span>`;
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

    const headerCells = columns
      .map((column) => {
        const titleParts = [column.description];
        if (column.series_start) {
          titleParts.push(`from ${column.series_start}`);
        }
        return `<th class="col-alert-history" title="${escapeHtml(titleParts.join(" · "))}">${escapeHtml(column.label || column.code)}</th>`;
      })
      .join("");

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

  function renderTableBody(containerId, rows, renderRow) {
    const tbody = document.getElementById(containerId);
    tbody.innerHTML = rows.map((row) => renderRow(row)).join("");
  }

  function renderAlerts(snapshot) {
    const asOf = document.getElementById("tactical-as-of");
    const summaryEl = document.getElementById("tactical-alerts-summary");
    const series = snapshot.series || [];
    const alerts = snapshot.alerts || [];
    const history = snapshot.history || { columns: [], rows: [] };
    const activeCount = alerts.filter((alert) => alert.active).length;
    const hasData =
      snapshot.date &&
      (series.length > 0 || alerts.length > 0 || history.rows.length > 0);

    if (!hasData) {
      setTacticalContent(false);
      setTacticalMessage("No macro health data yet. Run the data job to compute it.");
      renderTableBody("alerts-series-body", [], renderSeriesRow);
      renderAlertHistory({ columns: [], rows: [] });
      asOf.textContent = "";
      summaryEl.textContent = "";
      return;
    }

    setTacticalMessage("");
    setTacticalContent(true);
    asOf.textContent = snapshot.date
      ? `— FRED series and thresholds as of ${snapshot.date}`
      : "— FRED series and thresholds";
    summaryEl.textContent =
      alerts.length > 0 ? `— ${activeCount} of ${alerts.length} active` : "";
    renderTableBody("alerts-series-body", series, renderSeriesRow);
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
