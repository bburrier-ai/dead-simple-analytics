/**
 * Dashboard - D3 chart + fetch event table.
 */
(function () {
  let activeSiteId = null;

  const EVENT_COLUMN_LABELS = {
    occurred_at: "Time",
    type: "Type",
    path: "Path",
    track_id: "Track ID",
    session_id: "Session",
    visitor_hash: "Visitor",
    visitor_id: "Visitor ID",
    referrer: "Referrer",
    location: "Location",
  };
  const DEFAULT_EVENT_COLUMNS = [
    "occurred_at",
    "type",
    "path",
    "track_id",
    "session_id",
    "visitor_hash",
    "referrer",
    "location",
  ];
  const COLUMNS_STORAGE_KEY = "dsa-events-columns";
  const PERIOD_STORAGE_KEY = "dsa-chart-period";
  const DEFAULT_CHART_PERIOD = { unit: "days", value: 14 };
  const ALLOWED_CHART_PERIODS = [
    { unit: "hours", value: 24 },
    { unit: "days", value: 7 },
    { unit: "days", value: 14 },
    { unit: "days", value: 30 },
    { unit: "days", value: 90 },
  ];

  function isAllowedChartPeriod(period) {
    return ALLOWED_CHART_PERIODS.some(
      (allowed) => allowed.unit === period.unit && allowed.value === period.value
    );
  }

  function loadChartPeriod() {
    try {
      const raw = localStorage.getItem(PERIOD_STORAGE_KEY);
      if (!raw) return { ...DEFAULT_CHART_PERIOD };
      const parsed = JSON.parse(raw);
      const period = {
        unit: parsed?.unit === "hours" ? "hours" : "days",
        value: parseInt(parsed?.value, 10),
      };
      if (!Number.isFinite(period.value) || !isAllowedChartPeriod(period)) {
        return { ...DEFAULT_CHART_PERIOD };
      }
      return period;
    } catch {
      return { ...DEFAULT_CHART_PERIOD };
    }
  }

  function saveChartPeriod(period) {
    localStorage.setItem(PERIOD_STORAGE_KEY, JSON.stringify(period));
  }

  function syncPeriodPills() {
    document.querySelectorAll(".period-pill").forEach((btn) => {
      const unit = btn.dataset.period || "days";
      const value = parseInt(btn.dataset.value, 10);
      btn.classList.toggle(
        "active",
        unit === chartPeriod.unit && value === chartPeriod.value
      );
    });
  }

  function loadEventColumns() {
    try {
      const raw = localStorage.getItem(COLUMNS_STORAGE_KEY);
      if (!raw) return DEFAULT_EVENT_COLUMNS.slice();
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return DEFAULT_EVENT_COLUMNS.slice();
      const cols = [];
      for (const key of parsed) {
        if (EVENT_COLUMN_LABELS[key] && !cols.includes(key)) cols.push(key);
      }
      return cols.length ? cols : DEFAULT_EVENT_COLUMNS.slice();
    } catch {
      return DEFAULT_EVENT_COLUMNS.slice();
    }
  }

  function saveEventColumns(cols) {
    localStorage.setItem(COLUMNS_STORAGE_KEY, JSON.stringify(cols));
  }

  let chartPeriod = loadChartPeriod();
  let eventColumns = loadEventColumns();
  let eventsPage = 1;
  let eventsPageCount = 1;

  function renderEventsHeader() {
    const head = document.getElementById("events-head");
    if (!head) return;
    head.innerHTML = eventColumns
      .map(
        (key) =>
          `<th data-column="${key}">${EVENT_COLUMN_LABELS[key] || key}</th>`
      )
      .join("");
  }

  function periodQueryParams() {
    const params = new URLSearchParams();
    if (chartPeriod.unit === "hours") {
      params.set("hours", String(chartPeriod.value));
    } else {
      params.set("days", String(chartPeriod.value));
    }
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (tz) params.set("tz", tz);
    return params;
  }

  function formatCompactMetric(value) {
    const n = Number(value) || 0;
    if (n < 1000) return String(n);
    if (n < 1_000_000) {
      const k = Math.round((n / 1000) * 10) / 10;
      return `${Number.isInteger(k) ? k : k.toFixed(1)}k`;
    }
    const m = Math.round((n / 1_000_000) * 10) / 10;
    return `${Number.isInteger(m) ? m : m.toFixed(1)}m`;
  }

  function setChartDetail(detailEl, label, metrics) {
    if (!detailEl) return;
    detailEl.innerHTML = `
      <span class="chart-detail-label">${label}</span>
      <span class="chart-detail-metrics">
        <span class="chart-detail-metric">
          <i class="chart-detail-dot chart-detail-dot--pageview" aria-hidden="true"></i>
          <span class="chart-detail-metric-value">${formatCompactMetric(metrics.pageviews)}</span>
          <span class="chart-detail-metric-name">views</span>
        </span>
        <span class="chart-detail-metric">
          <i class="chart-detail-dot chart-detail-dot--click" aria-hidden="true"></i>
          <span class="chart-detail-metric-value">${formatCompactMetric(metrics.clicks)}</span>
          <span class="chart-detail-metric-name">clicks</span>
        </span>
        <span class="chart-detail-metric">
          <i class="chart-detail-dot chart-detail-dot--hover" aria-hidden="true"></i>
          <span class="chart-detail-metric-value">${formatCompactMetric(metrics.hovers)}</span>
          <span class="chart-detail-metric-name">hovers</span>
        </span>
        <span class="chart-detail-metric bold">
          <span class="chart-detail-metric-value">${formatCompactMetric(metrics.visitors)}</span>
          <span class="chart-detail-metric-name">visitors</span>
        </span>
      </span>
    `;
  }

  function chartColor(token, fallback) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(token).trim();
    return value || fallback;
  }

  function parseSeriesDate(value) {
    if (String(value).includes("T")) {
      return new Date(value);
    }
    return d3.utcParse("%Y-%m-%d")(value);
  }

  function periodTotalLabel() {
    if (chartPeriod.unit === "hours") {
      return `${chartPeriod.value}-hour total`;
    }
    return `${chartPeriod.value}-day total`;
  }

  function formatDetailLabel(date) {
    if (chartPeriod.unit === "hours") {
      return d3.timeFormat("%b %d, %I %p")(date);
    }
    return d3.utcFormat("%b %d, %Y")(date);
  }

  function zeroPoint(date) {
    return { date, pageviews: 0, clicks: 0, hovers: 0, visitors: 0 };
  }

  /** Ensure the series covers the full selected period through now, including empty buckets. */
  function padSeriesToPeriod(series) {
    const byKey = new Map((series || []).map((row) => [row.date, row]));
    const now = new Date();

    if (chartPeriod.unit === "hours") {
      const start = new Date(now.getTime() - chartPeriod.value * 3600 * 1000);
      const cursor = new Date(start);
      cursor.setMinutes(0, 0, 0);
      const out = [];
      for (let t = new Date(cursor); t <= now; t.setHours(t.getHours() + 1)) {
        const key = new Date(t).toISOString().replace(/\.\d{3}Z$/, "Z");
        const existing = byKey.get(key);
        out.push(existing ? { ...zeroPoint(key), ...existing, date: key } : zeroPoint(key));
      }
      return out;
    }

    const out = [];
    for (let i = chartPeriod.value - 1; i >= 0; i -= 1) {
      const local = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i);
      const key = [
        local.getFullYear(),
        String(local.getMonth() + 1).padStart(2, "0"),
        String(local.getDate()).padStart(2, "0"),
      ].join("-");
      const existing = byKey.get(key);
      out.push(existing ? { ...zeroPoint(key), ...existing, date: key } : zeroPoint(key));
    }
    return out;
  }

  function periodXDomain(data) {
    const start = data[0].date;
    const last = data[data.length - 1].date;
    if (chartPeriod.unit === "hours") {
      // Snap the right edge to now so the current partial hour is visible.
      return [start, new Date()];
    }
    // Give the last calendar day a full band through end-of-day.
    return [start, d3.utcDay.offset(last, 1)];
  }

  function periodTickValues(data, count) {
    const dates = data.map((d) => d.date);
    if (dates.length <= count) return dates;
    const picked = [];
    for (let i = 0; i < count; i += 1) {
      const idx = Math.round((i * (dates.length - 1)) / (count - 1));
      picked.push(dates[idx]);
    }
    const seen = new Set();
    const out = [];
    for (const date of picked) {
      const key = +date;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(date);
    }
    return out;
  }

  function renderChart(series, totals) {
    const container = document.getElementById("visits-chart");
    if (!container || typeof d3 === "undefined") return;

    container.innerHTML = "";
    const width = container.clientWidth || 800;
    const height = 220;
    const margin = {
      top: 8,
      right: width < 480 ? 8 : 12,
      bottom: 28,
      left: width < 480 ? 28 : 36,
    };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;
    const useLocalTime = chartPeriod.unit === "hours";

    const padded = padSeriesToPeriod(series);
    const data = padded.map((d) => ({
      date: parseSeriesDate(d.date),
      pageviews: d.pageviews,
      clicks: d.clicks,
      hovers: d.hovers || 0,
      visitors: d.visitors || 0,
    }));

    const svg = d3
      .select(container)
      .append("svg")
      .attr("viewBox", `0 0 ${width} ${height}`)
      .attr("preserveAspectRatio", "xMidYMid meet");

    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

    const xScale = useLocalTime ? d3.scaleTime() : d3.scaleUtc();
    const x = xScale.domain(periodXDomain(data)).range([0, innerW]);
    const y = d3
      .scaleLinear()
      .domain([0, d3.max(data, (d) => d.pageviews + d.clicks + d.hovers) * 1.1 || 1])
      .nice()
      .range([innerH, 0]);

    const stack = d3.stack().keys(["pageviews", "clicks", "hovers"]);
    const areas = stack(data);
    const area = d3
      .area()
      .x((d) => x(d.data.date))
      .y0((d) => y(d[0]))
      .y1((d) => y(d[1]))
      .curve(d3.curveMonotoneX);

    const colors = {
      pageviews: chartColor("--chart-pageview", "rgba(180, 208, 239, 0.5)"),
      clicks: chartColor("--chart-click", "rgba(169, 226, 216, 0.44)"),
      hovers: chartColor("--chart-hover", "rgba(249, 209, 181, 0.39)"),
    };

    g.selectAll(".area")
      .data(areas)
      .join("path")
      .attr("fill", (d) => colors[d.key])
      .attr("d", area);

    const focusLine = g
      .append("line")
      .attr("class", "chart-focus-line")
      .attr("y1", 0)
      .attr("y2", innerH)
      .attr("stroke", "#000")
      .attr("stroke-opacity", 0.5)
      .attr("stroke-width", 1)
      .style("display", "none");

    const xTickFormat = useLocalTime ? d3.timeFormat("%I %p") : d3.utcFormat("%b %d");
    const xTicks = width < 480 ? 4 : useLocalTime ? 8 : 7;

    g.append("g")
      .attr("transform", `translate(0,${innerH})`)
      .call(d3.axisBottom(x).tickValues(periodTickValues(data, xTicks)).tickFormat(xTickFormat));
    g.append("g").call(d3.axisLeft(y).ticks(width < 480 ? 4 : 5));

    const detailEl = document.getElementById("visits-chart-detail");
    const periodLabel = periodTotalLabel();
    const periodMetrics = {
      pageviews: totals?.pageviews ?? 0,
      clicks: totals?.clicks ?? 0,
      hovers: totals?.hovers ?? 0,
      visitors: totals?.visitors ?? 0,
    };
    setChartDetail(detailEl, periodLabel, periodMetrics);

    const bisect = d3.bisector((d) => d.date).center;

    g.append("rect")
      .attr("class", "chart-overlay")
      .attr("width", innerW)
      .attr("height", innerH)
      .attr("fill", "transparent")
      .style("cursor", "crosshair")
      .style("pointer-events", "all")
      .on("mousemove", (event) => {
        const [mx] = d3.pointer(event);
        const point = data[bisect(data, x.invert(mx))];
        if (!point) return;
        const xPos = x(point.date);
        focusLine.attr("x1", xPos).attr("x2", xPos).style("display", null);
        setChartDetail(detailEl, formatDetailLabel(point.date), {
          pageviews: point.pageviews,
          clicks: point.clicks,
          hovers: point.hovers,
          visitors: point.visitors,
        });
      })
      .on("mouseleave", () => {
        focusLine.style("display", "none");
        setChartDetail(detailEl, periodLabel, periodMetrics);
      });
  }

  async function loadChart() {
    if (!activeSiteId) return;
    const data =
      chartPeriod.unit === "hours"
        ? await DSA.visits(activeSiteId, { hours: chartPeriod.value })
        : await DSA.visits(activeSiteId, { days: chartPeriod.value });
    renderChart(data.series, data.totals);
  }

  function renderEventsPagination(total, page, limit) {
    const el = document.getElementById("events-pagination");
    if (!el) return;
    const pageSize = Math.max(1, Number(limit) || 25);
    const pageCount = Math.max(1, Math.ceil(Number(total) / pageSize));
    eventsPage = Math.min(Math.max(1, Number(page) || 1), pageCount);
    eventsPageCount = pageCount;
    const range = el.querySelector("[data-events-range]");
    const actions = el.querySelector(".events-pagination-actions");
    const prev = el.querySelector("[data-events-prev]");
    const next = el.querySelector("[data-events-next]");
    if (range) {
      if (total === 0) {
        range.textContent = "No events";
      } else {
        const start = (eventsPage - 1) * pageSize + 1;
        const end = Math.min(eventsPage * pageSize, total);
        range.textContent = `${start}-${end} of ${total}`;
      }
    }
    // Nav only when there is more than one page (not merely more than one record).
    if (actions) actions.hidden = pageCount <= 1;
    if (prev) {
      prev.hidden = pageCount <= 1;
      prev.disabled = eventsPage <= 1;
    }
    if (next) {
      next.hidden = pageCount <= 1;
      next.disabled = eventsPage >= pageCount;
    }
    el.hidden = false;
  }

  /** Format UTC ISO timestamps in the browser's local timezone with 12-hour clock. */
  function formatEventTime(iso) {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  }

  function localizeEventTimes(root) {
    root.querySelectorAll('td[data-field="occurred_at"]').forEach((td) => {
      const iso = td.getAttribute("data-value");
      if (!iso) return;
      td.textContent = formatEventTime(iso);
    });
  }

  function refreshEventsTable(options = {}) {
    hideEventsMenu();
    const tbody = document.getElementById("events-body");
    if (!tbody || !activeSiteId) return;
    if (options.resetPage) eventsPage = 1;
    renderEventsHeader();
    const q = document.getElementById("event-search")?.value || "";
    const type = document.getElementById("type-filter")?.value || "all";
    const params = periodQueryParams();
    params.set("site_id", activeSiteId);
    params.set("type", type);
    params.set("q", q);
    params.set("columns", eventColumns.join(","));
    params.set("page", String(eventsPage));
    fetch(`/partials/events-table?${params}`, { credentials: "include" })
      .then((r) => {
        const total = parseInt(r.headers.get("X-Events-Total") || "0", 10);
        const page = parseInt(r.headers.get("X-Events-Page") || "1", 10);
        const limit = parseInt(r.headers.get("X-Events-Limit") || "25", 10);
        return r.text().then((html) => ({ html, total, page, limit }));
      })
      .then(({ html, total, page, limit }) => {
        tbody.innerHTML = html;
        localizeEventTimes(tbody);
        renderEventsPagination(total, page, limit);
      });
  }

  let eventsMenuEl = null;
  let columnsDialogEl = null;

  function hideEventsMenu() {
    if (eventsMenuEl) {
      eventsMenuEl.remove();
      eventsMenuEl = null;
    }
  }

  function hideColumnsDialog() {
    if (columnsDialogEl) {
      columnsDialogEl.remove();
      columnsDialogEl = null;
    }
  }

  function placeEventsMenu(menu, clientX, clientY) {
    menu.hidden = false;
    const pad = 8;
    const rect = menu.getBoundingClientRect();
    let left = clientX;
    let top = clientY;
    if (left + rect.width > window.innerWidth - pad) {
      left = Math.max(pad, window.innerWidth - rect.width - pad);
    }
    if (top + rect.height > window.innerHeight - pad) {
      top = Math.max(pad, window.innerHeight - rect.height - pad);
    }
    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
  }

  function showEventsMenu(cell, clientX, clientY) {
    hideEventsMenu();
    const value = cell.getAttribute("data-value") ?? "";
    const filterBy = cell.getAttribute("data-filter");
    const canFilter = Boolean(filterBy && value);

    const menu = document.createElement("div");
    menu.className = "context-menu";
    menu.setAttribute("role", "menu");
    menu.innerHTML = `
      <button type="button" class="context-menu-item" data-action="copy" role="menuitem">Copy value</button>
      <button type="button" class="context-menu-item" data-action="match" role="menuitem" ${canFilter ? "" : "disabled"}>Show matching</button>
    `;
    document.body.appendChild(menu);
    eventsMenuEl = menu;
    placeEventsMenu(menu, clientX, clientY);

    menu.addEventListener("click", async (e) => {
      const btn = e.target.closest("[data-action]");
      if (!btn || btn.disabled) return;
      const action = btn.getAttribute("data-action");
      hideEventsMenu();
      if (action === "copy") {
        try {
          await navigator.clipboard.writeText(value);
        } catch {
          /* ignore clipboard failures */
        }
        return;
      }
      if (action === "match" && canFilter) {
        applyMatchingFilter(filterBy, value);
      }
    });
  }

  function showHeaderMenu(clientX, clientY) {
    hideEventsMenu();
    const menu = document.createElement("div");
    menu.className = "context-menu";
    menu.setAttribute("role", "menu");
    menu.innerHTML = `
      <button type="button" class="context-menu-item" data-action="configure" role="menuitem">Configure table</button>
    `;
    document.body.appendChild(menu);
    eventsMenuEl = menu;
    placeEventsMenu(menu, clientX, clientY);
    menu.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-action]");
      if (!btn) return;
      hideEventsMenu();
      if (btn.getAttribute("data-action") === "configure") {
        openColumnsDialog();
      }
    });
  }

  function openColumnsDialog() {
    hideColumnsDialog();
    const draft = eventColumns.slice();
    const order = [
      ...draft,
      ...Object.keys(EVENT_COLUMN_LABELS).filter((key) => !draft.includes(key)),
    ];
    const overlay = document.createElement("div");
    overlay.className = "columns-dialog-overlay";
    overlay.innerHTML = `
      <div class="columns-dialog card" role="dialog" aria-modal="true" aria-label="Configure table">
        <h2>Configure table</h2>
        <p class="columns-dialog-hint">Drag rows to reorder. Uncheck to hide a column.</p>
        <ul class="columns-dialog-list"></ul>
        <div class="columns-dialog-actions">
          <button type="button" class="btn" data-columns-cancel>Cancel</button>
          <button type="button" class="btn btn-primary" data-columns-save>Save</button>
        </div>
      </div>
    `;
    const list = overlay.querySelector(".columns-dialog-list");
    let dragKey = null;

    function syncDraftFromDom() {
      const next = [];
      list.querySelectorAll(".columns-dialog-item").forEach((item) => {
        const key = item.dataset.column;
        const checked = item.querySelector('input[type="checkbox"]')?.checked;
        if (key && checked) next.push(key);
      });
      draft.length = 0;
      draft.push(...next);
    }

    function moveItem(fromKey, toKey, placeAfter) {
      if (!fromKey || !toKey || fromKey === toKey) return;
      const from = order.indexOf(fromKey);
      if (from < 0) return;
      const [item] = order.splice(from, 1);
      let insertAt = order.indexOf(toKey);
      if (insertAt < 0) {
        order.splice(from, 0, item);
        return;
      }
      if (placeAfter) insertAt += 1;
      order.splice(insertAt, 0, item);
      renderList();
      syncDraftFromDom();
    }

    function renderList() {
      list.innerHTML = "";
      for (const key of order) {
        const li = document.createElement("li");
        li.className = "columns-dialog-item";
        li.dataset.column = key;
        li.draggable = true;
        const checked = draft.includes(key);
        li.innerHTML = `
          <span class="columns-dialog-handle" aria-hidden="true" title="Drag to reorder"></span>
          <label class="columns-dialog-check">
            <input type="checkbox" ${checked ? "checked" : ""} />
            <span>${EVENT_COLUMN_LABELS[key]}</span>
          </label>
        `;
        const checkbox = li.querySelector('input[type="checkbox"]');
        checkbox.addEventListener("change", () => {
          if (checkbox.checked) {
            if (!draft.includes(key)) draft.push(key);
          } else {
            const at = draft.indexOf(key);
            if (at >= 0) draft.splice(at, 1);
          }
        });
        checkbox.addEventListener("mousedown", (e) => e.stopPropagation());
        checkbox.addEventListener("click", (e) => e.stopPropagation());

        li.addEventListener("dragstart", (e) => {
          dragKey = key;
          li.classList.add("is-dragging");
          e.dataTransfer.effectAllowed = "move";
          e.dataTransfer.setData("text/plain", key);
        });
        li.addEventListener("dragend", () => {
          dragKey = null;
          li.classList.remove("is-dragging");
          list.querySelectorAll(".is-drop-before, .is-drop-after").forEach((el) => {
            el.classList.remove("is-drop-before", "is-drop-after");
          });
        });
        li.addEventListener("dragover", (e) => {
          e.preventDefault();
          e.dataTransfer.dropEffect = "move";
          const rect = li.getBoundingClientRect();
          const after = e.clientY > rect.top + rect.height / 2;
          li.classList.toggle("is-drop-before", !after);
          li.classList.toggle("is-drop-after", after);
        });
        li.addEventListener("dragleave", () => {
          li.classList.remove("is-drop-before", "is-drop-after");
        });
        li.addEventListener("drop", (e) => {
          e.preventDefault();
          const fromKey = dragKey || e.dataTransfer.getData("text/plain");
          const rect = li.getBoundingClientRect();
          const after = e.clientY > rect.top + rect.height / 2;
          li.classList.remove("is-drop-before", "is-drop-after");
          moveItem(fromKey, key, after);
        });
        list.appendChild(li);
      }
    }

    renderList();
    overlay.querySelector("[data-columns-cancel]").addEventListener("click", hideColumnsDialog);
    overlay.querySelector("[data-columns-save]").addEventListener("click", () => {
      syncDraftFromDom();
      if (!draft.length) return;
      eventColumns = draft.slice();
      saveEventColumns(eventColumns);
      hideColumnsDialog();
      refreshEventsTable({ resetPage: true });
    });
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) hideColumnsDialog();
    });
    document.body.appendChild(overlay);
    columnsDialogEl = overlay;
  }

  function applyMatchingFilter(filterBy, value) {
    const search = document.getElementById("event-search");
    const typeFilter = document.getElementById("type-filter");
    if (filterBy === "type" && typeFilter) {
      typeFilter.value = value;
      if (search) search.value = "";
    } else if (filterBy === "q" && search) {
      search.value = value;
      if (typeFilter) typeFilter.value = "all";
    }
    refreshEventsTable({ resetPage: true });
  }

  function bindEventsTableMenu() {
    const table = document.getElementById("events-table");
    if (!table) return;

    table.addEventListener("contextmenu", (e) => {
      const headerCell = e.target.closest("#events-table thead th");
      if (headerCell) {
        e.preventDefault();
        showHeaderMenu(e.clientX, e.clientY);
        return;
      }
      const cell = e.target.closest("#events-body td[data-field]");
      if (!cell) return;
      e.preventDefault();
      showEventsMenu(cell, e.clientX, e.clientY);
    });

    document.addEventListener("click", (e) => {
      if (eventsMenuEl && !e.target.closest(".context-menu")) {
        hideEventsMenu();
      }
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        hideEventsMenu();
        hideColumnsDialog();
      }
    });
    window.addEventListener("blur", hideEventsMenu);
    window.addEventListener("resize", hideEventsMenu);
    document.addEventListener("scroll", hideEventsMenu, true);
  }

  let liveSource = null;
  let liveRefreshTimer = null;
  const LIVE_REFRESH_MS = 1500;

  function scheduleLiveRefresh(siteId) {
    if (!siteId || siteId !== activeSiteId) return;
    if (liveRefreshTimer) clearTimeout(liveRefreshTimer);
    liveRefreshTimer = setTimeout(async () => {
      liveRefreshTimer = null;
      await loadChart();
      refreshEventsTable();
    }, LIVE_REFRESH_MS);
  }

  function stopLiveUpdates() {
    if (liveRefreshTimer) {
      clearTimeout(liveRefreshTimer);
      liveRefreshTimer = null;
    }
    if (liveSource) {
      liveSource.close();
      liveSource = null;
    }
  }

  function startLiveUpdates() {
    stopLiveUpdates();
    if (typeof EventSource === "undefined") return;
    liveSource = new EventSource("/api/events/live");
    liveSource.addEventListener("event", (msg) => {
      try {
        const data = JSON.parse(msg.data);
        scheduleLiveRefresh(data.site_id);
      } catch {
        /* ignore malformed payloads */
      }
    });
    liveSource.onerror = () => {
      // EventSource reconnects automatically; leave the instance open.
    };
  }

  function bindControls() {
    bindEventsTableMenu();
    document.getElementById("event-search")?.addEventListener("input", () => {
      refreshEventsTable({ resetPage: true });
    });
    document.getElementById("type-filter")?.addEventListener("change", () => {
      refreshEventsTable({ resetPage: true });
    });
    document.getElementById("events-pagination")?.addEventListener("click", (e) => {
      const prev = e.target.closest("[data-events-prev]");
      const next = e.target.closest("[data-events-next]");
      if (prev && !prev.disabled && eventsPage > 1) {
        eventsPage -= 1;
        refreshEventsTable();
      } else if (next && !next.disabled && eventsPage < eventsPageCount) {
        eventsPage += 1;
        refreshEventsTable();
      }
    });

    document.querySelectorAll(".period-pill").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const next = {
          unit: btn.dataset.period || "days",
          value: parseInt(btn.dataset.value, 10) || 14,
        };
        if (!isAllowedChartPeriod(next)) return;
        chartPeriod = next;
        saveChartPeriod(chartPeriod);
        syncPeriodPills();
        await loadChart();
        refreshEventsTable({ resetPage: true });
      });
    });

    document.addEventListener("site-changed", async (e) => {
      activeSiteId = e.detail?.siteId || getActiveSiteId();
      await loadChart();
      refreshEventsTable({ resetPage: true });
    });

    window.addEventListener("resize", () => loadChart());
    window.addEventListener("beforeunload", stopLiveUpdates);
  }

  window.initDashboard = async function initDashboard() {
    bindControls();
    syncPeriodPills();
    renderEventsHeader();
    activeSiteId = getActiveSiteId();
    if (activeSiteId) {
      await loadChart();
      refreshEventsTable();
    }
    startLiveUpdates();
  };
})();
