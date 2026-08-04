(function () {
  const api = window.PortfolioApi;

  let reportLoaded = false;
  let cachedReportHtml = null;
  let lastStackedLayout = null;
  let resizeTimer = null;

  // Match portfolio management card breakpoint.
  const MOBILE_LAYOUT_MQ = window.matchMedia("(max-width: 720px)");

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

  function isStackedLayout() {
    return MOBILE_LAYOUT_MQ.matches;
  }

  // QuantStats has no layout mode — only a fixed #left/#right float template.
  // Desktop: compact side-by-side at 900px (avoids accidental stack + heavy scroll).
  // Mobile: force a single column so phones don't need horizontal scroll.
  const REPORT_MIN_WIDTH = 1300;
  const REPORT_BODY_PAD_Y = 16;
  const REPORT_BODY_PAD_X = 16;
  const REPORT_COLUMN_GAP = 16;
  const REPORT_CONTENT_WIDTH = REPORT_MIN_WIDTH - REPORT_BODY_PAD_X * 2;
  const REPORT_LEFT_WIDTH = Math.round(REPORT_CONTENT_WIDTH * (620 / 958));
  const REPORT_RIGHT_WIDTH =
    REPORT_CONTENT_WIDTH - REPORT_LEFT_WIDTH - REPORT_COLUMN_GAP;

  function desktopFitStyle() {
    return `
<style id="portfolio-risk-fit">
  html, body {
    overflow: visible !important;
    height: auto !important;
    margin: 0 !important;
    padding: ${REPORT_BODY_PAD_Y}px ${REPORT_BODY_PAD_X}px !important;
    box-sizing: border-box !important;
    max-width: none !important;
    width: ${REPORT_MIN_WIDTH}px !important;
    min-width: ${REPORT_MIN_WIDTH}px !important;
  }
  .container {
    max-width: none !important;
    width: 100% !important;
    box-sizing: border-box !important;
  }
  .container::after {
    content: "";
    display: table;
    clear: both;
  }
  #left {
    float: left !important;
    width: ${REPORT_LEFT_WIDTH}px !important;
    margin-right: ${REPORT_COLUMN_GAP}px !important;
  }
  #right {
    float: right !important;
    width: ${REPORT_RIGHT_WIDTH}px !important;
  }
</style>`;
  }

  function stackedFitStyle() {
    return `
<style id="portfolio-risk-fit">
  html, body {
    overflow: visible !important;
    height: auto !important;
    margin: 0 !important;
    padding: ${REPORT_BODY_PAD_Y}px ${REPORT_BODY_PAD_X}px !important;
    box-sizing: border-box !important;
    max-width: none !important;
    min-width: 0 !important;
    width: 100% !important;
  }
  .container {
    max-width: none !important;
    width: 100% !important;
    box-sizing: border-box !important;
  }
  .container > h1,
  .container > h4,
  .container > hr {
    display: none !important;
  }
  #left,
  #right {
    float: none !important;
    width: 100% !important;
    margin: 0 0 1rem !important;
    box-sizing: border-box !important;
  }
  #left {
    margin-top: 0 !important;
  }
  /* QuantStats SVGs include large internal padding; keep their pull-up margins
     and scale height with width so stacked charts don't leave huge gaps. */
  #left svg,
  #monthly_heatmap svg {
    display: block !important;
    width: 100% !important;
    height: auto !important;
    margin: -1.5rem 0 !important;
  }
  #left > div {
    margin-bottom: -0.75rem !important;
  }
</style>`;
  }

  function prepareReportHtml(html, stacked) {
    const fitStyle = stacked ? stackedFitStyle() : desktopFitStyle();
    const viewport = stacked
      ? `<meta name="viewport" content="width=device-width, initial-scale=1" />`
      : `<meta name="viewport" content="width=${REPORT_MIN_WIDTH}" />`;

    let prepared = html.replace(/<meta\s+name="viewport"[^>]*>/i, viewport);
    if (!/<meta\s+name="viewport"/i.test(prepared)) {
      prepared = prepared.includes("</head>")
        ? prepared.replace("</head>", `${viewport}</head>`)
        : viewport + prepared;
    }

    if (prepared.includes("</head>")) {
      return prepared.replace("</head>", `${fitStyle}</head>`);
    }
    return fitStyle + prepared;
  }

  function frameMinWidth(frame) {
    if (!isStackedLayout()) {
      return REPORT_MIN_WIDTH;
    }
    const scroll = frame.closest(".risk-report-scroll");
    return Math.max(scroll?.clientWidth || 0, 280);
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

    const minWidth = frameMinWidth(frame);
    const contentWidth = isStackedLayout()
      ? minWidth
      : Math.max(
          doc.documentElement.scrollWidth,
          body ? body.scrollWidth : 0,
          minWidth,
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

  function applyReportHtml(frame, html, stacked) {
    lastStackedLayout = stacked;
    bindRiskFrameResize(frame);
    frame.srcdoc = prepareReportHtml(html, stacked);
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
    if (reportLoaded && !force && cachedReportHtml) {
      const frame = document.getElementById("risk-report-frame");
      if (!frame || frame.hidden) {
        return;
      }
      const stacked = isStackedLayout();
      if (stacked !== lastStackedLayout) {
        applyReportHtml(frame, cachedReportHtml, stacked);
      } else {
        sizeRiskFrame(frame);
      }
      return;
    }

    setRiskLoading(true);
    setRiskMessage("");
    setRiskFrameVisible(false);

    try {
      const frame = document.getElementById("risk-report-frame");
      cachedReportHtml = await fetchReportHtml();
      applyReportHtml(frame, cachedReportHtml, isStackedLayout());
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
    cachedReportHtml = null;
    lastStackedLayout = null;
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

  function onViewportChange() {
    if (resizeTimer !== null) {
      clearTimeout(resizeTimer);
    }
    resizeTimer = window.setTimeout(() => {
      resizeTimer = null;
      const frame = document.getElementById("risk-report-frame");
      if (!frame || frame.hidden || !reportLoaded || !cachedReportHtml) {
        return;
      }
      const stacked = isStackedLayout();
      if (stacked !== lastStackedLayout) {
        applyReportHtml(frame, cachedReportHtml, stacked);
        return;
      }
      sizeRiskFrame(frame);
    }, 150);
  }

  window.addEventListener("resize", onViewportChange);
  if (typeof MOBILE_LAYOUT_MQ.addEventListener === "function") {
    MOBILE_LAYOUT_MQ.addEventListener("change", onViewportChange);
  } else if (typeof MOBILE_LAYOUT_MQ.addListener === "function") {
    MOBILE_LAYOUT_MQ.addListener(onViewportChange);
  }

  window.RiskView = {
    loadRiskAnalysis,
    resetRiskAnalysis,
  };
})();
