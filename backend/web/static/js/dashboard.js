/**
 * Dashboard - D3 chart + HTMX event table.
 */
(function () {
  let activeSiteId = null;
  let chartPeriod = { unit: "days", value: 14 };

  function setChartDetail(detailEl, label, metrics) {
    if (!detailEl) return;
    detailEl.innerHTML = `
      <span class="chart-detail-label">${label}</span>
      <span class="chart-detail-metrics">
        <span class="chart-detail-metric">
          <i class="chart-detail-dot chart-detail-dot--pageview" aria-hidden="true"></i>
          ${metrics.pageviews} pageviews
        </span>
        <span class="chart-detail-metric">
          <i class="chart-detail-dot chart-detail-dot--click" aria-hidden="true"></i>
          ${metrics.clicks} clicks
        </span>
        <span class="chart-detail-metric">
          <i class="chart-detail-dot chart-detail-dot--hover" aria-hidden="true"></i>
          ${metrics.hovers} hovers
        </span>
        <span class="chart-detail-metric bold">
          ${metrics.visitors} visitors
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
      return d3.utcFormat("%b %d, %I %p")(date);
    }
    return d3.utcFormat("%b %d, %Y")(date);
  }

  function renderChart(series, totals) {
    const container = document.getElementById("visits-chart");
    if (!container || typeof d3 === "undefined") return;

    container.innerHTML = "";
    const width = container.clientWidth || 800;
    const height = 220;
    const margin = { top: 8, right: 12, bottom: 28, left: 36 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const parseDate = parseSeriesDate;
    const data = series.map((d) => ({
      date: parseDate(d.date),
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

    const x = d3.scaleUtc().domain(d3.extent(data, (d) => d.date)).range([0, innerW]);
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

    const xTickFormat =
      chartPeriod.unit === "hours" ? d3.utcFormat("%I %p") : d3.utcFormat("%b %d");
    const xTicks = chartPeriod.unit === "hours" ? 8 : 7;

    g.append("g")
      .attr("transform", `translate(0,${innerH})`)
      .call(d3.axisBottom(x).ticks(xTicks).tickFormat(xTickFormat));
    g.append("g").call(d3.axisLeft(y).ticks(5));

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

  function refreshEventsTable() {
    const tbody = document.getElementById("events-body");
    if (!tbody || !activeSiteId) return;
    const q = document.getElementById("event-search")?.value || "";
    const type = document.getElementById("type-filter")?.value || "all";
    const url = `/partials/events-table?site_id=${encodeURIComponent(activeSiteId)}&type=${encodeURIComponent(type)}&q=${encodeURIComponent(q)}`;
    fetch(url, { credentials: "include" })
      .then((r) => r.text())
      .then((html) => {
        tbody.innerHTML = html;
      });
  }

  function bindControls() {
    document.getElementById("event-search")?.addEventListener("input", () => refreshEventsTable());
    document.getElementById("type-filter")?.addEventListener("change", () => refreshEventsTable());

    document.querySelectorAll(".period-pill").forEach((btn) => {
      btn.addEventListener("click", async () => {
        document.querySelectorAll(".period-pill").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        chartPeriod = {
          unit: btn.dataset.period || "days",
          value: parseInt(btn.dataset.value, 10) || 14,
        };
        await loadChart();
      });
    });

    document.addEventListener("site-changed", async (e) => {
      activeSiteId = e.detail?.siteId || getActiveSiteId();
      await loadChart();
      refreshEventsTable();
    });

    window.addEventListener("resize", () => loadChart());
  }

  window.initDashboard = async function initDashboard() {
    bindControls();
    activeSiteId = getActiveSiteId();
    if (activeSiteId) {
      await loadChart();
      refreshEventsTable();
    }
  };
})();
