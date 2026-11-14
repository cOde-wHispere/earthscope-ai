import pytest
from fastapi.testclient import TestClient

from earthscope_backend.config import cors_origins
from earthscope_backend.main import create_app


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
def test_allowed_origin_and_preflight(origin, monkeypatch, write_csv, rows, app_factory):
    monkeypatch.delenv("EARTHSCOPE_CORS_ORIGINS", raising=False)
    with TestClient(app_factory(write_csv(rows))) as client:
        response = client.get("/timeseries/monthly", headers={"Origin": origin})
        assert response.status_code == 200
        assert len(response.json()["observations"]) == 420
        assert response.headers["access-control-allow-origin"] == origin
        assert "access-control-allow-credentials" not in response.headers
        assert "Origin" in response.headers["vary"]
        preflight = client.options(
            "/timeseries/monthly",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Accept",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == origin
        assert preflight.headers["access-control-allow-methods"] == "GET"
        assert "access-control-allow-credentials" not in preflight.headers


@pytest.mark.parametrize("origin", ["https://unapproved.example", "http://localhost:5174", "null"])
def test_unapproved_browser_origin(origin, monkeypatch, write_csv, rows, app_factory):
    monkeypatch.delenv("EARTHSCOPE_CORS_ORIGINS", raising=False)
    with TestClient(app_factory(write_csv(rows))) as client:
        # CORS controls browser access; it does not change the public GET contract.
        response = client.get("/health", headers={"Origin": origin})
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers
        preflight = client.options(
            "/trend",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert preflight.status_code == 400
        assert "access-control-allow-origin" not in preflight.headers


def test_production_allowlist_replaces_defaults(monkeypatch, write_csv, rows, app_factory):
    monkeypatch.setenv(
        "EARTHSCOPE_CORS_ORIGINS", "https://app.example.org, https://www.example.org"
    )
    with TestClient(app_factory(write_csv(rows))) as client:
        for origin in ["https://app.example.org", "https://www.example.org"]:
            response = client.get("/trend", headers={"Origin": origin})
            assert response.headers["access-control-allow-origin"] == origin
        local = client.get("/trend", headers={"Origin": "http://localhost:5173"})
        assert "access-control-allow-origin" not in local.headers


def test_cors_does_not_change_response_contracts(write_csv, rows, app_factory):
    with TestClient(app_factory(write_csv(rows))) as client:
        for route in [
            "/health",
            "/metadata",
            "/timeseries/monthly",
            "/timeseries/annual",
            "/climatology",
            "/trend",
            "/openapi.json",
        ]:
            ordinary = client.get(route)
            browser = client.get(route, headers={"Origin": "http://localhost:5173"})
            assert browser.status_code == ordinary.status_code == 200
            assert browser.json() == ordinary.json()


@pytest.mark.parametrize("method,headers", [("POST", "Accept"), ("GET", "Authorization")])
def test_unneeded_methods_and_headers_are_not_allowed(
    method, headers, write_csv, rows, app_factory
):
    with TestClient(app_factory(write_csv(rows))) as client:
        response = client.options(
            "/trend",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": headers,
            },
        )
        assert response.status_code == 400


@pytest.mark.parametrize(
    "value",
    [
        "*",
        "https://*.example.org",
        "null",
        "file://example.org",
        "https://example.org/path",
        "https://example.org/",
        "https://user:password@example.org",
        "https://example.org:bad",
        "https://example.org,",
        "https://example.org\nInjected",
    ],
)
def test_unsafe_cors_configuration_fails_explicitly(monkeypatch, value):
    monkeypatch.setenv("EARTHSCOPE_CORS_ORIGINS", value)
    with pytest.raises(ValueError, match="EARTHSCOPE_CORS_ORIGINS"):
        create_app()


def test_empty_allowlist_disables_cors(monkeypatch, tmp_path):
    monkeypatch.setenv("EARTHSCOPE_CORS_ORIGINS", "")
    assert cors_origins() == ()
    with TestClient(create_app(tmp_path / "missing.csv")) as client:
        response = client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers


def test_allowed_origin_can_read_structured_dataset_errors(monkeypatch, tmp_path):
    monkeypatch.delenv("EARTHSCOPE_CORS_ORIGINS", raising=False)
    with TestClient(create_app(tmp_path / "missing.csv")) as client:
        response = client.get("/metadata", headers={"Origin": "http://localhost:5173"})
        assert response.status_code == 503
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert response.json()["code"] == "dataset_missing"
