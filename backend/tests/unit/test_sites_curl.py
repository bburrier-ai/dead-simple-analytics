from services.sites import SitesService


def test_curl_for_includes_collect_url_origin_and_site_key(monkeypatch):
    monkeypatch.setattr(
        "services.sites.settings.public_base_url",
        "https://stats.example.com",
    )
    curl = SitesService().curl_for("sk_test_key", ["beauburrier.com"])
    assert "https://stats.example.com/collect" in curl
    assert "Origin: https://beauburrier.com" in curl
    assert "sk_test_key" in curl
    assert "EVENT_ID=$(uuidgen" in curl
    assert "pageview" in curl
