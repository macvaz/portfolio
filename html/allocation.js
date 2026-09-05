(function () {
  const screen = document.getElementById("allocation-screen");
  const titleEl = document.getElementById("allocation-title");
  const totalInput = document.getElementById("allocation-total");
  const bodyEl = document.getElementById("allocation-body");
  const weightTotalEl = document.getElementById("allocation-weight-total");
  const amountTotalEl = document.getElementById("allocation-amount-total");
  const emptyEl = document.getElementById("allocation-empty");
  const closeBtn = document.getElementById("allocation-close");
  const openBtn = document.getElementById("portfolio-allocation-btn");

  const amountFormatter = new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function formatWeight(value) {
    if (!Number.isFinite(value)) {
      return "—";
    }
    if (Math.abs(value - Math.round(value)) < 1e-9) {
      return String(Math.round(value));
    }
    return value.toFixed(2);
  }

  function parseTotal(value) {
    const total = Number.parseFloat(String(value).trim().replace(",", "."));
    if (!Number.isFinite(total) || total < 0) {
      return null;
    }
    return total;
  }

  function renderFundName(fund) {
    const name = escapeHtml(fund.name);
    if (fund.morningstar_url) {
      return `<a href="${fund.morningstar_url}" class="fund-link" target="_blank" rel="noopener noreferrer">${name}</a>`;
    }
    return `<span class="fund-name">${name}</span>`;
  }

  function renderRows(funds, total) {
    if (!funds.length) {
      bodyEl.innerHTML = "";
      weightTotalEl.textContent = "—";
      amountTotalEl.textContent = "—";
      emptyEl.hidden = false;
      return;
    }

    emptyEl.hidden = true;
    let weightSum = 0;
    let amountSum = 0;

    bodyEl.innerHTML = funds
      .map((fund) => {
        const weight = fund.weight;
        const amount = total === null ? null : (total * weight) / 100;
        weightSum += weight;
        if (amount !== null) {
          amountSum += amount;
        }
        const amountText = amount === null ? "—" : amountFormatter.format(amount);
        return `
          <tr>
            <td class="allocation-col-name">${renderFundName(fund)}</td>
            <td class="allocation-col-weight">${formatWeight(weight)}</td>
            <td class="allocation-col-amount">${amountText}</td>
          </tr>`;
      })
      .join("");

    weightTotalEl.textContent = `${formatWeight(weightSum)}`;
    amountTotalEl.textContent = total === null ? "—" : amountFormatter.format(amountSum);
  }

  function refresh() {
    const funds = window.ManagementView?.getPortfolioAllocationFunds?.() ?? [];
    const portfolioName = document.getElementById("portfolio-table-name")?.textContent?.trim();
    titleEl.textContent = portfolioName ? `Fund allocation — ${portfolioName}` : "Fund allocation";
    renderRows(funds, parseTotal(totalInput.value));
  }

  function open() {
    totalInput.value = "";
    refresh();
    screen.hidden = false;
    screen.removeAttribute("hidden");
    document.body.classList.add("is-allocation-open");
    totalInput.focus();
  }

  function close() {
    screen.hidden = true;
    screen.setAttribute("hidden", "");
    document.body.classList.remove("is-allocation-open");
  }

  openBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    open();
  });

  closeBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    close();
  });

  totalInput?.addEventListener("input", refresh);

  screen?.addEventListener("click", (event) => {
    if (event.target === screen) {
      close();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (screen.hidden || event.key !== "Escape") {
      return;
    }
    close();
  });

  window.AllocationView = {
    open,
    close,
    refresh,
    setButtonVisible(visible) {
      if (!openBtn) {
        return;
      }
      openBtn.hidden = !visible;
    },
    isOpen() {
      return !screen.hidden;
    },
  };
})();
