def test_healthz(client):
    res = client.get("/api/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_readyz(client):
    res = client.get("/api/readyz")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"
