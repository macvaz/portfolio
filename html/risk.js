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
    document.getElementById("risk-report-frame").hidden = !isVisible;
  }

  function prepareReportHtml(html) {
    const fitStyle = `
<style id="portfolio-risk-fit">
  html, body {
    overflow: visible !important;
    height: auto !important;
    margin: 0 !important;
    max-width: none !important;
  }
  body {
    transform-origin: top left;
  }
</style>`;
    const viewport = '<meta name="viewport" content="width=device-width, initial-scale=1" />';

    let prepared = html;
    if (prepared.includes("</head>")) {
      prepared = prepared.replace("</head>", `${viewport}${fitStyle}</head>`);
    } else {
      prepared = viewport + fitStyle + prepared;
    }
    return prepared;
  }

  function availableFrameWidth(frame) {
    const rect = frame.getBoundingClientRect();
    if (rect.width > 0) {
      return rect.width;
    }
    const parent = frame.parentElement?.getBoundingClientRect();
    return parent?.width || window.innerWidth;
  }

  function fitRiskFrame(frame) {
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
      1,
    );
    const available = availableFrameWidth(frame);
    const scale = Math.min(1, available / contentWidth);

    if (body) {
      body.style.transformOrigin = "top left";
      if (scale < 0.999) {
        body.style.transform = `scale(${scale})`;
        body.style.width = `${contentWidth}px`;
      } else {
        body.style.transform = "none";
        body.style.width = "";
      }
    }

    const naturalHeight = Math.max(
      doc.documentElement.scrollHeight,
      body ? body.scrollHeight : 0,
    );
    frame.style.height = `${Math.ceil(naturalHeight * scale)}px`;
  }

  function scheduleFitRiskFrame(frame) {
    fitRiskFrame(frame);
    window.setTimeout(() => fitRiskFrame(frame), 300);
    window.setTimeout(() => fitRiskFrame(frame), 1500);
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
      img.addEventListener("load", () => fitRiskFrame(frame), { once: true });
    });
  }

  function bindRiskFrameResize(frame) {
    frame.onload = () => {
      bindRiskFrameImages(frame);
      scheduleFitRiskFrame(frame);
    };
  }

  async function fetchReportHtml() {
    const response = await fetch(api.withPortfolioId(`${api.PORTFOLIO_API}/risk_report`));
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
        fitRiskFrame(frame);
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
      fitRiskFrame(frame);
    }, 150);
  });

  window.RiskView = {
    loadRiskAnalysis,
    resetRiskAnalysis,
  };
})();
