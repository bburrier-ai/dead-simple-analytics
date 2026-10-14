from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_HTML = REPO_ROOT / "backend" / "web" / "static" / "dashboard.html"
DASHBOARD_JS = REPO_ROOT / "backend" / "web" / "static" / "js" / "dashboard.js"
DASHBOARD_CSS = REPO_ROOT / "backend" / "web" / "static" / "css" / "app.css"


def read_dashboard_assets() -> tuple[str, str, str]:
    return (
        DASHBOARD_HTML.read_text(encoding="utf-8"),
        DASHBOARD_JS.read_text(encoding="utf-8"),
        DASHBOARD_CSS.read_text(encoding="utf-8"),
    )


def test_chart_scale_defaults_to_log_without_a_visible_scale_dropdown():
    html, javascript, _ = read_dashboard_assets()

    assert 'id="chart-scale"' not in html
    assert (
        'return localStorage.getItem(SCALE_STORAGE_KEY) === "linear" ? "linear" : "log";'
        in javascript
    )
    assert "let chartScale = loadChartScale();" in javascript


def test_chart_keeps_filled_areas_in_linear_and_log_modes():
    _, javascript, _ = read_dashboard_assets()

    assert "function createLinearScale(data, innerH)" in javascript
    assert "function createLogScale(data, innerH)" in javascript
    assert (
        'chartScale === "linear" ? createLinearScale(data, innerH) : createLogScale(data, innerH)'
        in javascript
    )
    assert "function renderAreaSeries(g, data, x, y, baselineY, colors)" in javascript
    assert '.attr("fill", (key) => colors[key])' in javascript
    assert ".defined((point) => point[key] > 0)" in javascript


def test_chart_context_menu_switches_scale_and_explains_zero_treatment():
    html, javascript, css = read_dashboard_assets()

    assert (
        "Log scale omits zero-value points because a logarithmic axis cannot represent zero."
        in html
    )
    assert "chart-context-menu" in javascript
    assert 'container.addEventListener("contextmenu"' in javascript
    assert "event.preventDefault();" in javascript
    assert '["log", "linear"]' in javascript
    assert 'data-chart-scale="${scale}"' in javascript
    assert "chartScale = scale;" in javascript
    assert "saveChartScale(chartScale);" in javascript
    assert "context-menu-item--selected" in css


def test_chart_context_menu_dismisses_on_escape_and_outside_click():
    _, javascript, _ = read_dashboard_assets()

    assert 'event.key === "Escape"' in javascript
    assert '!event.target.closest(".chart-context-menu")' in javascript
    assert 'window.addEventListener("blur", hideChartMenu);' in javascript
    assert 'document.addEventListener("scroll", hideChartMenu, true);' in javascript
