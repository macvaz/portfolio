(function () {
  const api = window.PortfolioApi;

  const MORNINGSTAR_DOMAIN = "https://global.morningstar.com";

  const screen = document.getElementById("add-fund-screen");
  const form = document.getElementById("add-fund-import-form");
  const isinInput = document.getElementById("add-fund-isin");
  const jsonInput = document.getElementById("add-fund-json");
  const msLink = document.getElementById("add-fund-ms-link");
  const msLinkPlaceholder = document.getElementById("add-fund-ms-link-placeholder");
  const cancelBtn = document.getElementById("add-fund-cancel");
  const submitBtn = document.getElementById("add-fund-submit");
  const toolbarIsinInput = document.getElementById("isin-input");

  let onComplete = null;

  function isValidIsin(value) {
    const isin = value.trim().toUpperCase();
    return isin.length === 12 && /^[A-Z0-9]{12}$/.test(isin);
  }

  function morningstarLegacySearchUrl(isin) {
    const query = `((isin+~%3D+%22${isin}%22))`;
    return (
      `${MORNINGSTAR_DOMAIN}/api/v1/es/legacy-search/securities` +
      `?fields=isin,name&query=${query}&sort=_score`
    );
  }

  function setSubmitting(submitting) {
    submitBtn.disabled = submitting;
    cancelBtn.disabled = submitting;
    isinInput.disabled = submitting;
    jsonInput.disabled = submitting;
    submitBtn.textContent = submitting ? "Adding fund…" : "Add fund";
  }

  function refreshMorningstarLink() {
    const isin = isinInput.value.trim().toUpperCase();

    if (!isValidIsin(isin)) {
      msLink.hidden = true;
      msLink.href = "#";
      msLink.textContent = "";
      msLinkPlaceholder.hidden = false;
      msLinkPlaceholder.textContent =
        "Enter a valid 12-character ISIN to generate the search URL.";
      return;
    }

    const url = morningstarLegacySearchUrl(isin);
    msLink.href = url;
    msLink.textContent = url;
    msLink.hidden = false;
    msLinkPlaceholder.hidden = true;
  }

  function open(initialIsin = "", completeCallback = null) {
    onComplete = completeCallback;
    isinInput.value = initialIsin.trim().toUpperCase();
    jsonInput.value = "";
    setSubmitting(false);
    screen.hidden = false;
    screen.removeAttribute("hidden");
    document.body.classList.add("is-add-fund-open");
    toolbarIsinInput.value = "";
    refreshMorningstarLink();
    if (isValidIsin(isinInput.value)) {
      jsonInput.focus();
    } else {
      isinInput.focus();
    }
  }

  function close() {
    screen.hidden = true;
    screen.setAttribute("hidden", "");
    document.body.classList.remove("is-add-fund-open");
    onComplete = null;
    toolbarIsinInput.focus();
  }

  async function submitImport(event) {
    event.preventDefault();
    window.AppShell?.showError("");

    const isin = isinInput.value.trim().toUpperCase();
    if (!isValidIsin(isin)) {
      window.AppShell?.showError("Enter a valid 12-character ISIN.");
      isinInput.focus();
      return;
    }

    let payload;
    try {
      payload = JSON.parse(jsonInput.value.trim());
    } catch (_err) {
      window.AppShell?.showError("Morningstar response must be valid JSON.");
      jsonInput.focus();
      return;
    }

    setSubmitting(true);
    try {
      await api.fetchJson(`${api.PORTFOLIO_API}/funds/import`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const callback = onComplete;
      close();
      if (typeof callback === "function") {
        await callback();
      }
    } catch (err) {
      window.AppShell?.showError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  form.addEventListener("submit", (event) => {
    submitImport(event).catch((err) => window.AppShell?.showError(err.message));
  });

  cancelBtn.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    window.AppShell?.showError("");
    close();
  });

  isinInput.addEventListener("input", () => {
    isinInput.value = isinInput.value.toUpperCase();
    refreshMorningstarLink();
  });

  screen.addEventListener("click", (event) => {
    if (event.target === screen) {
      window.AppShell?.showError("");
      close();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (screen.hidden || event.key !== "Escape") {
      return;
    }
    window.AppShell?.showError("");
    close();
  });

  window.AddFundView = {
    open,
    close,
    isOpen() {
      return !screen.hidden;
    },
  };
})();
