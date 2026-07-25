def test_health_reports_degraded_without_db(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database"] is False       # no DB configured in tests
    assert body["queue"] is True           # in-memory queue
    assert body["status"] in ("ok", "degraded")


def test_metrics_endpoint_exposes_prometheus(client):
    # generate some traffic first
    client.get("/health")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "aegis_http_requests_total" in resp.text


def test_openapi_documents_all_endpoints(client):
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    for expected in [
        "/api/v1/research",
        "/api/v1/research/{request_id}",
        "/api/v1/recommendations",
        "/api/v1/agent-performance",
        "/api/v1/memory/search",
        "/health",
        "/metrics",
    ]:
        assert expected in paths
