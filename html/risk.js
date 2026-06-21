(function () {
  const api = window.PortfolioApi;

  let reportLoaded = false;

  function setRiskMessage(message) {
    const messageEl = document.getElementById("risk-message");
    messageEl.textContent = message;
    messageEl.hidden = !message;
  }

  function setRiskLoading(isLoading) {
    document.getElementById("risk-loading").hidden = !isLoading;
  }

  function setRiskFrameVisible(isVisible) {
    document.getElementById("risk-report-frame").hidden = !isVisible;
  }

  function prepareReportHtml(html) {
    const overflowStyle =
      "<style>html, body { overflow: visible !important; height: auto !important; }</style>";
    if (html.includes("</head>")) {
      return html.replace("</head>", `${overflowStyle}</head>`);
    }
    return overflowStyle + html;
  }

  function resizeRiskFrame(frame) {
    const doc = frame.contentDocument;
    if (!doc) {
      return;
    }

    const height = Math.max(
      doc.documentElement.scrollHeight,
      doc.body ? doc.body.scrollHeight : 0,
    );
    frame.style.height = `${height}px`;
  }

  function bindRiskFrameResize(frame) {
    frame.onload = () => {
      resizeRiskFrame(frame);
      window.setTimeout(() => resizeRiskFrame(frame), 300);
      window.setTimeout(() => resizeRiskFrame(frame), 1500);
    };
  }

  async function fetchReportHtml() {
    const response = await fetch(api.withPortfolioId(`${api.PORTFOLIO_API}/report`));
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const detail = body.detail;
      const message = Array.isArray(detail)
        ? detail.map((item) => item.msg).join(", ")
        : detail || response.statusText;
      throw new Error(message);
    }
    return response.text();
  }

  async function loadRiskAnalysis({ force = false } = {}) {
    if (reportLoaded && !force) {
      return;
    }

    setRiskLoading(true);
    setRiskMessage("");
    setRiskFrameVisible(false);

    try {
      const frame = document.getElementById("risk-report-frame");
      bindRiskFrameResize(frame);
      frame.srcdoc = prepareReportHtml(await fetchReportHtml());
      setRiskFrameVisible(true);
      reportLoaded = true;
    } catch (error) {
      setRiskMessage(error.message);
    } finally {
      setRiskLoading(false);
    }
  }

  function resetRiskAnalysis() {
    reportLoaded = false;
    setRiskLoading(false);
    setRiskMessage("");
    setRiskFrameVisible(false);
    const frame = document.getElementById("risk-report-frame");
    frame.srcdoc = "";
    frame.style.height = "0";
    frame.onload = null;
    document.getElementById("risk-loading").textContent = "Generating risk analysis…";
  }

  window.RiskView = {
    loadRiskAnalysis,
    resetRiskAnalysis,
  };
})();
