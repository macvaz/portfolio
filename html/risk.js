(function () {
  const api = window.PortfolioApi;

  let reportLoaded = false;
  let resizeTimer = null;

  function setRiskMessage(message) {
    const messageEl = document.getElementById("risk-message");
    messageEl.textContent = message;
    messageEl.hidden = !message;
  }

  function setRiskLoading(isLoading) {
    document.getElementById("risk-loading").hidden = !isLoading;
  }

  function setRiskFrameVisible(isVisible) {
    const frame = document.getElementById("risk-report-frame");
    const scroll = frame?.closest(".risk-report-scroll");
    frame.hidden = !isVisible;
    if (scroll) {
      scroll.hidden = !isVisible;
    }
  }

  const REPORT_MIN_WIDTH = 1100;

  function prepareReportHtml(html) {
    // Keep QuantStats' desktop multi-column layout; the risk tab scrolls instead.
    const fitStyle = `
<style id="portfolio-risk-fit">
  html, body {
    overflow: visible !important;
    height: auto !important;
    margin: 0 !important;
    max-width: none !important;
    min-width: ${REPORT_MIN_WIDTH}px !important;
  }
</style>`;
    const viewport = `<meta name="viewport" content="width=${REPORT_MIN_WIDTH}" />`;

    let prepared = html;
    if (prepared.includes("</head>")) {
      prepared = prepared.replace("</head>", `${viewport}${fitStyle}</head>`);
    } else {
      prepared = viewport + fitStyle + prepared;
    }
    return prepared;
  }

  function sizeRiskFrame(frame) {
    const doc = frame.contentDocument;
    if (!doc?.documentElement) {
      return;
    }

    const body = doc.body;
    if (body) {
      body.style.transform = "none";
      body.style.width = "";
    }

    const contentWidth = Math.max(
      doc.documentElement.scrollWidth,
      body ? body.scrollWidth : 0,
      REPORT_MIN_WIDTH,
    );
    const contentHeight = Math.max(
      doc.documentElement.scrollHeight,
      body ? body.scrollHeight : 0,
    );

    frame.style.width = `${contentWidth}px`;
    frame.style.height = `${Math.ceil(contentHeight)}px`;
  }

  function scheduleSizeRiskFrame(frame) {
    sizeRiskFrame(frame);
    window.setTimeout(() => sizeRiskFrame(frame), 300);
    window.setTimeout(() => sizeRiskFrame(frame), 1500);
  }

  function bindRiskFrameImages(frame) {
    const doc = frame.contentDocument;
    if (!doc) {
      return;
    }

    Array.from(doc.images || []).forEach((img) => {
      if (img.complete) {
        return;
      }
      img.addEventListener("load", () => sizeRiskFrame(frame), { once: true });
    });
  }

  function bindRiskFrameResize(frame) {
    frame.onload = () => {
      bindRiskFrameImages(frame);
      scheduleSizeRiskFrame(frame);
    };
  }

  async function fetchReportHtml() {
    let path = `${api.PORTFOLIO_API}/risk_report`;
    const startDate = window.ManagementView?.getCurveStartDate?.();
    if (startDate) {
      path += `?start_date=${encodeURIComponent(startDate)}`;
    }
    const response = await fetch(api.withPortfolioId(path));
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
      const frame = document.getElementById("risk-report-frame");
      if (frame && !frame.hidden) {
        sizeRiskFrame(frame);
      }
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
    frame.style.width = "";
    frame.style.height = "0";
    frame.onload = null;
    document.getElementById("risk-loading").textContent = "Generating risk report…";
  }

  window.addEventListener("resize", () => {
    if (resizeTimer !== null) {
      clearTimeout(resizeTimer);
    }
    resizeTimer = window.setTimeout(() => {
      resizeTimer = null;
      const frame = document.getElementById("risk-report-frame");
      if (!frame || frame.hidden || !reportLoaded) {
        return;
      }
      sizeRiskFrame(frame);
    }, 150);
  });

  window.RiskView = {
    loadRiskAnalysis,
    resetRiskAnalysis,
  };
})();
