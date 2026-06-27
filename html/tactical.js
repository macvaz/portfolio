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

  function formatThreshold(threshold) {
    if (threshold === null || threshold === undefined || !Number.isFinite(threshold)) {
      return "—";
    }
    if (Number.isInteger(threshold)) {
      return String(threshold);
    }
    return threshold.toFixed(2);
  }

  function formatNumericValue(value) {
    if (!Number.isFinite(value)) {
      return "—";
    }
    return value.toFixed(2);
  }

  function formatSeriesValue(identifier, value) {
    if (!Number.isFinite(value)) {
      return "—";
    }
    if (identifier === "SP500") {
      return value.toFixed(0);
    }
    return value.toFixed(2);
  }

  function renderSeriesIdentifier(signal) {
    const identifier = signal.identifier || signal.code;
    if (signal.source_url) {
      return `<a href="${signal.source_url}" class="fund-link" target="_blank" rel="noopener noreferrer">${identifier}</a>`;
    }
    return identifier;
  }

  function renderSeriesRow(signal) {
    const identifier = signal.identifier || signal.code;
    return `
      <tr>
        <td class="col-name">${renderSeriesIdentifier(signal)}</td>
        <td class="col-name col-description">${signal.description}</td>
        <td>${formatSeriesValue(identifier, signal.value)}</td>
        <td>${formatThreshold(signal.threshold)}</td>
      </tr>`;
  }

  function mergeAlerts(snapshot) {
    const activated = (snapshot.alerts_activated || []).map((alert) => ({
      ...alert,
      active: true,
    }));
    const inactive = (snapshot.alerts_deactivated || []).map((alert) => ({
      ...alert,
      active: false,
    }));
    return [...activated, ...inactive].sort((left, right) => {
      if (left.active !== right.active) {
        return left.active ? -1 : 1;
      }
      return left.code.localeCompare(right.code);
    });
  }

  const ALERT_DISPLAY_NAMES = {
    SP500_DEATH_CROSS_ACTIVE: "SP500_DEATH_CROSS",
    SP500_CONFIRMED_DEATH_CROSS: "SP500_DEATH_CROSS_C",
  };

  function formatAlertDisplayName(code) {
    return ALERT_DISPLAY_NAMES[code] || code;
  }

  function renderAlertBadge(content, active) {
    const statusClass = active ? "active" : "inactive";
    return `<span class="alert-name alert-name--${statusClass}">${content}</span>`;
  }

  function renderAlertName(alert) {
    return renderAlertBadge(formatAlertDisplayName(alert.code), alert.active);
  }

  function renderAlertRow(alert) {
    return `
      <tr>
        <td class="col-name">${renderAlertName(alert)}</td>
        <td class="col-name col-description">${alert.description}</td>
        <td class="col-value">${renderAlertBadge(formatNumericValue(alert.value), alert.active)}</td>
        <td>${formatThreshold(alert.threshold)}</td>
      </tr>`;
  }

  function renderTableBody(containerId, rows, renderRow) {
    const tbody = document.getElementById(containerId);
    tbody.innerHTML = rows.map((row) => renderRow(row)).join("");
  }

  function renderSignals(snapshot) {
    const asOf = document.getElementById("tactical-as-of");
    const summaryEl = document.getElementById("tactical-alerts-summary");
    const alerts = mergeAlerts(snapshot);
    const activeCount = alerts.filter((alert) => alert.active).length;
    const hasData =
      snapshot.date &&
      ((snapshot.series && snapshot.series.length) || alerts.length);

    if (!hasData) {
      setTacticalContent(false);
      setTacticalMessage("No tactical signals yet. Run the data job to compute them.");
      renderTableBody("signals-series-body", [], renderSeriesRow);
      renderTableBody("signals-alerts-body", [], renderAlertRow);
      asOf.textContent = "";
      summaryEl.textContent = "";
      return;
    }

    setTacticalMessage("");
    setTacticalContent(true);
    asOf.textContent = `Latest execution as of ${snapshot.date}`;
    summaryEl.textContent =
      alerts.length > 0 ? `— ${activeCount} of ${alerts.length} active` : "";
    renderTableBody("signals-series-body", snapshot.series || [], renderSeriesRow);
    renderTableBody("signals-alerts-body", alerts, renderAlertRow);
  }

  async function loadTacticalSignals() {
    setTacticalLoading(true);
    setTacticalMessage("");

    try {
      const snapshot = await api.fetchJson(api.SIGNALS_API);
      renderSignals(snapshot);
    } catch (error) {
      setTacticalContent(false);
      setTacticalMessage(error.message);
    } finally {
      setTacticalLoading(false);
    }
  }

  window.TacticalView = {
    loadTacticalSignals,
  };
})();
