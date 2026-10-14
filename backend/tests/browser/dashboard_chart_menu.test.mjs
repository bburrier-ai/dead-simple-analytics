import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { chromium } from "playwright";

const dashboardScript = await readFile(
  new URL("../../web/static/js/dashboard.js", import.meta.url),
  "utf8"
);

const chartData = {
  series: [
    { date: "2026-10-10", pageviews: 8, clicks: 2, hovers: 1, visitors: 5 },
    { date: "2026-10-11", pageviews: 0, clicks: 0, hovers: 0, visitors: 0 },
    { date: "2026-10-12", pageviews: 3, clicks: 1, hovers: 1, visitors: 2 },
  ],
  totals: { pageviews: 11, clicks: 3, hovers: 2, visitors: 7 },
};

async function openDashboard() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1080, height: 720 } });
  const dashboardHtml = `
    <main>
      <div id="visits-chart" tabindex="0" style="width: 900px"></div>
      <p id="chart-scale-note">Log scale omits zero-value points because a logarithmic axis cannot represent zero.</p>
      <div id="visits-chart-detail"></div>
      <div id="events-pagination"></div>
      <table id="events-table"><thead><tr id="events-head"></tr></thead><tbody id="events-body"></tbody></table>
      <input id="event-search"><select id="type-filter"><option value="all">All</option></select>
    </main>
  `;
  await page.route("http://dsa.test/", (route) =>
    route.fulfill({ contentType: "text/html", body: dashboardHtml })
  );
  await page.goto("http://dsa.test/");
  await page.addScriptTag({ url: "https://cdn.jsdelivr.net/npm/d3@7" });
  await page.evaluate((data) => {
    window.getActiveSiteId = () => "test-site";
    window.DSA = { visits: async () => data };
    window.EventSource = undefined;
  }, chartData);
  await page.addScriptTag({ content: dashboardScript });
  await page.evaluate(() => window.initDashboard());
  return { browser, page };
}

async function areaPaths(page) {
  return page.locator("#visits-chart path.area").evaluateAll((paths) =>
    paths.map((path) => ({ d: path.getAttribute("d"), fill: path.getAttribute("fill") }))
  );
}

test("Visits chart defaults to Log and retains filled areas through scale changes", async () => {
  const { browser, page } = await openDashboard();
  try {
    assert.equal(await page.evaluate(() => localStorage.getItem("dsa-chart-scale")), null);
    assert.equal(await page.locator("#chart-scale").count(), 0);
    assert.equal(await page.locator("#chart-scale-note").isVisible(), true);

    const logAreas = await areaPaths(page);
    assert.equal(logAreas.length, 3);
    assert.ok(logAreas.every(({ d, fill }) => d && fill));

    await page.locator("#visits-chart").click({ button: "right" });
    const menu = page.locator(".chart-context-menu");
    await assert.doesNotReject(menu.waitFor());
    assert.equal(await menu.getByRole("menuitemradio", { name: "Log" }).getAttribute("aria-checked"), "true");

    await menu.getByRole("menuitemradio", { name: "Linear" }).click();
    assert.equal(await page.evaluate(() => localStorage.getItem("dsa-chart-scale")), "linear");
    assert.equal(await page.locator("#chart-scale-note").isVisible(), false);
    const linearAreas = await areaPaths(page);
    assert.equal(linearAreas.length, 3);
    assert.ok(linearAreas.every(({ d, fill }) => d && fill));
  } finally {
    await browser.close();
  }
});

test("chart scale menu dismisses on Escape and outside click", async () => {
  const { browser, page } = await openDashboard();
  try {
    await page.locator("#visits-chart").click({ button: "right" });
    await page.keyboard.press("Escape");
    assert.equal(await page.locator(".chart-context-menu").count(), 0);

    await page.locator("#visits-chart").click({ button: "right" });
    await page.locator("#chart-scale-note").click();
    assert.equal(await page.locator(".chart-context-menu").count(), 0);
  } finally {
    await browser.close();
  }
});

test("scale selection rerenders and dismisses when persistent storage is unavailable", async () => {
  const { browser, page } = await openDashboard();
  try {
    await page.evaluate(() => {
      Storage.prototype.setItem = () => {
        throw new DOMException("Storage disabled", "SecurityError");
      };
    });
    await page.locator("#visits-chart").click({ button: "right" });
    await page.getByRole("menuitemradio", { name: "Linear" }).click();
    assert.equal(await page.locator(".chart-context-menu").count(), 0);
    assert.equal(await page.locator("#chart-scale-note").isVisible(), false);
    assert.ok((await areaPaths(page)).every(({ d, fill }) => d && fill));
  } finally {
    await browser.close();
  }
});
