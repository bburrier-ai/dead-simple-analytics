from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_HTML = REPO_ROOT / "backend" / "web" / "static" / "dashboard.html"
DASHBOARD_JS = REPO_ROOT / "backend" / "web" / "static" / "js" / "dashboard.js"


def test_chart_scale_defaults_to_linear_and_exposes_labeled_selector():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    javascript = DASHBOARD_JS.read_text(encoding="utf-8")

    assert '<label for="chart-scale">Y-axis scale</label>' in html
    assert '<option value="linear">Linear</option>' in html
    assert '<option value="log">Log</option>' in html
    assert (
        'return localStorage.getItem(SCALE_STORAGE_KEY) === "log" ? "log" : "linear";'
        in javascript
    )


def test_log_scale_uses_real_series_and_omits_zero_values():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    javascript = DASHBOARD_JS.read_text(encoding="utf-8")

    assert "Log scale omits zero-value points" in html
    assert ".scaleLinear()" in javascript
    assert ".scaleLog()" in javascript
    assert "point[key] > 0" in javascript
    assert ".defined((point) => point[key] > 0)" in javascript
    assert "renderChart(data.series, data.totals);" in javascript