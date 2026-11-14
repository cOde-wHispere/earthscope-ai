from fastapi.testclient import TestClient

from earthscope_backend.main import create_app
from earthscope_backend.schemas import (
    AnnualResponse,
    ClimatologyResponse,
    DatasetMetadata,
    ErrorResponse,
    HealthResponse,
    MonthlyResponse,
    TrendResponse,
)


def test_response_schemas_and_openapi(write_csv, rows, app_factory):
    contracts = {
        "/health": HealthResponse,
        "/metadata": DatasetMetadata,
        "/timeseries/monthly": MonthlyResponse,
        "/timeseries/annual": AnnualResponse,
        "/climatology": ClimatologyResponse,
        "/trend": TrendResponse,
    }
    with TestClient(app_factory(write_csv(rows))) as client:
        for route, schema in contracts.items():
            response = client.get(route)
            assert response.status_code == 200
            schema.model_validate(response.json())
        assert client.get("/health").json()["status"] == "ok"
        assert len(client.get("/timeseries/monthly").json()["observations"]) == 420
        assert len(client.get("/timeseries/annual").json()["observations"]) == 35
        openapi = client.get("/openapi.json").json()
        assert set(contracts) <= openapi["paths"].keys()
        assert "503" in openapi["paths"]["/trend"]["get"]["responses"]
        assert client.get("/unknown").status_code == 404
        assert client.post("/trend").status_code == 405


def test_missing_dataset_still_serves_health(tmp_path):
    with TestClient(create_app(tmp_path / "absent.csv")) as client:
        response = client.get("/health")
        assert response.status_code == 200
        health = HealthResponse.model_validate(response.json())
        assert health.status == "degraded"
        assert health.dataset_status == "missing"
        for route in [
            "/metadata",
            "/timeseries/monthly",
            "/timeseries/annual",
            "/climatology",
            "/trend",
        ]:
            response = client.get(route)
            assert response.status_code == 503
            error = ErrorResponse.model_validate(response.json())
            assert error.code == "dataset_missing"
            assert "EARTHSCOPE_DATA_PATH" in error.message


def test_invalid_dataset_reports_validation(write_csv, rows, app_factory):
    rows.pop(2)
    with TestClient(app_factory(write_csv(rows))) as client:
        assert client.get("/health").json()["dataset_status"] == "invalid"
        response = client.get("/metadata")
        assert response.status_code == 503
        error = ErrorResponse.model_validate(response.json())
        assert error.code == "dataset_invalid"
        assert error.validation.missing_months == ("1991-03",)
        assert client.get("/trend").status_code == 503


def test_environment_path_and_snapshot(monkeypatch, write_csv, rows, fixture_identity):
    path = write_csv(rows)
    monkeypatch.setenv("EARTHSCOPE_DATA_PATH", str(path))
    app = create_app(identity=fixture_identity(path))
    with TestClient(app) as client:
        first = client.get("/metadata").json()["source_sha256"]
        path.write_text("broken", encoding="utf-8")
        assert client.get("/metadata").json()["source_sha256"] == first
        assert client.get("/health").json()["status"] == "ok"
    with TestClient(app) as client:
        assert client.get("/health").json()["dataset_status"] == "invalid"


def test_relative_environment_path_is_independent_of_cwd(monkeypatch, tmp_path):
    from earthscope_backend.config import REPOSITORY_ROOT, data_path

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EARTHSCOPE_DATA_PATH", "data/raw/example.csv")
    assert data_path() == REPOSITORY_ROOT / "data/raw/example.csv"


def test_unreadable_source(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/health").json()["dataset_status"] == "unavailable"
        assert client.get("/trend").status_code == 503


def test_unestimable_trend_preserves_descriptive_endpoints(write_csv, rows, app_factory):
    for row in rows:
        row[1] = "300"
    with TestClient(app_factory(write_csv(rows))) as client:
        assert client.get("/health").json()["dataset_status"] == "analysis_unavailable"
        assert client.get("/metadata").status_code == 200
        assert client.get("/timeseries/annual").status_code == 200
        response = client.get("/trend")
        assert response.status_code == 503
        assert ErrorResponse.model_validate(response.json()).code == "analysis_unavailable"
