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

  function renderAlertRow(signal) {
    return `
      <tr>
        <td class="col-name">${signal.code}</td>
        <td class="col-name col-description">${signal.description}</td>
        <td>${formatNumericValue(signal.value)}</td>
        <td>${formatThreshold(signal.threshold)}</td>
      </tr>`;
  }

  function renderTableBody(containerId, rows, renderRow) {
    const tbody = document.getElementById(containerId);
    tbody.innerHTML = rows.map((row) => renderRow(row)).join("");
  }

  function renderSignals(snapshot) {
    const asOf = document.getElementById("tactical-as-of");
    const activated = snapshot.alerts_activated || [];
    const deactivated = snapshot.alerts_deactivated || [];
    const hasData =
      snapshot.date &&
      ((snapshot.series && snapshot.series.length) ||
        activated.length ||
        deactivated.length);

    if (!hasData) {
      setTacticalContent(false);
      setTacticalMessage("No tactical signals yet. Run the data job to compute them.");
      renderTableBody("signals-series-body", [], renderSeriesRow);
      renderTableBody("signals-alerts-activated-body", [], renderAlertRow);
      renderTableBody("signals-alerts-deactivated-body", [], renderAlertRow);
      asOf.textContent = "";
      return;
    }

    setTacticalMessage("");
    setTacticalContent(true);
    asOf.textContent = `Latest execution as of ${snapshot.date}`;
    renderTableBody("signals-series-body", snapshot.series || [], renderSeriesRow);
    renderTableBody("signals-alerts-activated-body", activated, renderAlertRow);
    renderTableBody("signals-alerts-deactivated-body", deactivated, renderAlertRow);
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
