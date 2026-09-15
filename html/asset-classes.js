(function () {
  const api = window.PortfolioApi;

  const RETURN_COLUMNS = [
    { key: "intramonth", label: "MTD" },
    { key: "1m", label: "1m" },
    { key: "2m", label: "2m" },
    { key: "3m", label: "3m" },
    { key: "6m", label: "6m" },
    { key: "12m", label: "12m" },
    { key: "2y", label: "2y" },
    { key: "3y", label: "3y" },
    { key: "5y", label: "5y" },
    { key: "7y", label: "7y" },
    { key: "10y", label: "10y" },
  ];

  let rankingRows = [];
  let sortKey = "1m";
  let sortDir = "desc";
  let assetClassFilter = "";
  let headersBound = false;
  let filterBound = false;

  function formatPct(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "—";
    }
    const number = Number(value);
    const sign = number > 0 ? "+" : number < 0 ? "−" : "";
    return `${sign}${Math.abs(number).toFixed(2)}%`;
  }

  function metricClass(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "metric-neutral";
    }
    const number = Number(value);
    if (number > 0) return "metric-positive";
    if (number < 0) return "metric-negative";
    return "metric-neutral";
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function formatAsOf(asOf) {
    if (!asOf) return "";
    const text = String(asOf).slice(0, 10);
    return `As of ${text}`;
  }

  function setLoading(isLoading) {
    const loading = document.getElementById("asset-classes-loading");
    const content = document.getElementById("asset-classes-content");
    const message = document.getElementById("asset-classes-message");
    if (loading) loading.hidden = !isLoading;
    if (content) content.hidden = isLoading;
    if (message && isLoading) message.hidden = true;
  }

  function showMessage(text) {
    const message = document.getElementById("asset-classes-message");
    const content = document.getElementById("asset-classes-content");
    if (content) content.hidden = true;
    if (!message) return;
    message.textContent = text;
    message.hidden = !text;
  }

  function renderReturnCell(value) {
    return `<td class="col-return ${metricClass(value)}">${formatPct(value)}</td>`;
  }

  function filteredRows() {
    if (!assetClassFilter) return rankingRows;
    return rankingRows.filter((row) => row.asset_class === assetClassFilter);
  }

  function sortValue(row, key) {
    if (key === "name") {
      return String(row.name || "").toLowerCase();
    }
    if (key === "asset_class") {
      return String(row.asset_class_name || row.asset_class || "").toLowerCase();
    }
    const value = row.returns?.[key];
    return value === null || value === undefined || Number.isNaN(Number(value))
      ? null
      : Number(value);
  }

  function compareRows(a, b) {
    const left = sortValue(a, sortKey);
    const right = sortValue(b, sortKey);
    const leftMissing = left === null || left === undefined || left === "";
    const rightMissing = right === null || right === undefined || right === "";
    if (leftMissing && rightMissing) return 0;
    if (leftMissing) return 1;
    if (rightMissing) return -1;

    let cmp = 0;
    if (typeof left === "string" || typeof right === "string") {
      cmp = String(left).localeCompare(String(right), undefined, {
        sensitivity: "base",
      });
    } else {
      cmp = left < right ? -1 : left > right ? 1 : 0;
    }
    return sortDir === "asc" ? cmp : -cmp;
  }

  function updateSortHeaders() {
    const table = document.getElementById("asset-classes-table");
    if (!table) return;
    table.querySelectorAll("th[data-sort]").forEach((th) => {
      const active = th.dataset.sort === sortKey;
      th.classList.toggle("is-sorted", active);
      th.classList.toggle("is-sorted-asc", active && sortDir === "asc");
      th.classList.toggle("is-sorted-desc", active && sortDir === "desc");
      th.setAttribute(
        "aria-sort",
        active ? (sortDir === "asc" ? "ascending" : "descending") : "none",
      );
    });
  }

  function renderTableBody() {
    const body = document.getElementById("asset-classes-body");
    if (!body) return;

    const rows = [...filteredRows()].sort(compareRows);
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="${3 + RETURN_COLUMNS.length}" class="asset-classes-empty">No categories for this asset class.</td></tr>`;
      updateSortHeaders();
      return;
    }

    body.innerHTML = rows
      .map((row, index) => {
        const returns = row.returns || {};
        const assetClass = row.asset_class_name || "—";
        const returnCells = RETURN_COLUMNS.map((column) =>
          renderReturnCell(returns[column.key]),
        ).join("");
        return `<tr>
          <td class="col-rank">${index + 1}</td>
          <td class="col-name">${escapeHtml(row.name)}</td>
          <td class="col-asset-class">${escapeHtml(assetClass)}</td>
          ${returnCells}
        </tr>`;
      })
      .join("");
    updateSortHeaders();
  }

  function setSort(key) {
    if (sortKey === key) {
      sortDir = sortDir === "desc" ? "asc" : "desc";
    } else {
      sortKey = key;
      sortDir = key === "name" || key === "asset_class" ? "asc" : "desc";
    }
    renderTableBody();
  }

  function bindSortHeaders() {
    if (headersBound) return;
    const table = document.getElementById("asset-classes-table");
    if (!table) return;
    table.querySelectorAll("th[data-sort]").forEach((th) => {
      th.addEventListener("click", () => setSort(th.dataset.sort));
    });
    headersBound = true;
  }

  function populateAssetClassFilter() {
    const select = document.getElementById("asset-classes-filter");
    if (!select) return;

    const options = new Map();
    rankingRows.forEach((row) => {
      if (!row.asset_class) return;
      const label = row.asset_class_name || row.asset_class;
      if (!options.has(row.asset_class)) {
        options.set(row.asset_class, label);
      }
    });

    const previous = assetClassFilter;
    const sorted = [...options.entries()].sort((a, b) =>
      String(a[1]).localeCompare(String(b[1]), undefined, { sensitivity: "base" }),
    );

    select.innerHTML =
      `<option value="">All asset classes</option>` +
      sorted
        .map(
          ([value, label]) =>
            `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`,
        )
        .join("");

    if (previous && options.has(previous)) {
      select.value = previous;
      assetClassFilter = previous;
    } else {
      select.value = "";
      assetClassFilter = "";
    }
  }

  function bindAssetClassFilter() {
    if (filterBound) return;
    const select = document.getElementById("asset-classes-filter");
    if (!select) return;
    select.addEventListener("change", () => {
      assetClassFilter = select.value || "";
      renderTableBody();
    });
    filterBound = true;
  }

  function renderRanking(payload) {
    const asOf = document.getElementById("asset-classes-as-of");
    const content = document.getElementById("asset-classes-content");
    const message = document.getElementById("asset-classes-message");
    const body = document.getElementById("asset-classes-body");
    if (!body) return;

    rankingRows = payload?.categories || [];
    if (asOf) {
      asOf.textContent = formatAsOf(payload?.as_of);
    }

    if (!rankingRows.length) {
      body.innerHTML = "";
      showMessage("No category monthly data yet. Run the categories batch to download it.");
      return;
    }

    if (message) message.hidden = true;
    if (content) content.hidden = false;
    bindSortHeaders();
    bindAssetClassFilter();
    populateAssetClassFilter();
    renderTableBody();
  }

  async function loadAssetClasses() {
    setLoading(true);
    try {
      const payload = await api.fetchJson(`${api.API}/categories/ranking`);
      setLoading(false);
      renderRanking(payload);
    } catch (err) {
      setLoading(false);
      showMessage(err.message || "Failed to load ranking.");
      throw err;
    }
  }

  window.AssetClassesView = {
    loadAssetClasses,
  };
})();
