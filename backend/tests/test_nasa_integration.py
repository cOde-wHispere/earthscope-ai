import hashlib
import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from earthscope_backend.analysis import annual_series, estimate_trend
from earthscope_backend.importer import import_giovanni
from earthscope_backend.main import create_app

pytestmark = pytest.mark.integration


def test_local_nasa_coverage_and_read_only(nasa_path):
    before = nasa_path.read_bytes()
    dataset = import_giovanni(nasa_path)
    summary = dataset.metadata.validation
    assert summary.valid
    assert summary.observed_rows == summary.valid_observations == 420
    assert summary.missing_months == summary.duplicate_months == summary.unexpected_months == ()
    assert summary.fill_value_count == summary.invalid_value_count == 0
    assert len(annual_series(dataset).observations) == 35
    assert nasa_path.read_bytes() == before
    assert dataset.metadata.source_sha256 == hashlib.sha256(before).hexdigest()
    assert "shape=state_dept_countries_2017/shp_85" in dataset.metadata.raw_preamble


def test_nasa_trend_matches_independent_manual_hac(nasa_path):
    script = Path(__file__).resolve().parents[1] / "scripts/independent_trend.py"
    spec = importlib.util.spec_from_file_location("independent_audit", script)
    audit_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit_module)
    independent = audit_module.audit(nasa_path)
    result = estimate_trend(import_giovanni(nasa_path)).observations
    # No scientific slope, CI or p-value is hardcoded. Both paths read the actual observations.
    assert result.slope_celsius_per_decade == pytest.approx(
        independent["slope_celsius_per_decade"], abs=1e-10
    )
    assert result.standard_error_celsius_per_decade == pytest.approx(
        independent["standard_error_celsius_per_decade"], rel=1e-9
    )
    assert result.p_value == pytest.approx(independent["p_value"], rel=1e-8, abs=1e-14)
    interval = result.confidence_interval_celsius_per_decade
    assert interval.lower == pytest.approx(independent["ci95_lower"], abs=1e-10)
    assert interval.upper == pytest.approx(independent["ci95_upper"], abs=1e-10)


def test_nasa_api_uses_same_validated_source(nasa_path):
    dataset = import_giovanni(nasa_path)
    expected = estimate_trend(dataset)
    with TestClient(create_app(nasa_path)) as client:
        assert client.get("/health").json()["status"] == "ok"
        for route in [
            "/metadata",
            "/timeseries/monthly",
            "/timeseries/annual",
            "/climatology",
            "/trend",
        ]:
            response = client.get(route)
            assert response.status_code == 200
            assert response.json()["source_sha256"] == dataset.metadata.source_sha256
        assert client.get("/trend").json() == expected.model_dump(mode="json")
