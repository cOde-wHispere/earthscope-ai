"""All six original local exports are required; no fallback or synthetic substitutions."""

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from earthscope_backend import dataset_registry
from earthscope_backend.config import REPOSITORY_ROOT
from earthscope_backend.dataset_registry import load_manifest
from earthscope_backend.main import create_app
from earthscope_backend.multivariable_schemas import (
    DatasetCatalog,
    DescriptiveAnnualResponse,
    DescriptiveMonthlyResponse,
    VariableMetadata,
)
from earthscope_backend.schemas import ErrorResponse
from earthscope_backend.variables import SPECS

pytestmark = pytest.mark.integration
RAW = REPOSITORY_ROOT / "data/raw"


@pytest.fixture(scope="module")
def original_sources():
    sources = {variable: RAW / spec.filename for variable, spec in SPECS.items()}
    for variable, path in sources.items():
        assert path.is_file(), f"Original local {variable} CSV required at {path}; restore it."
    return sources


@pytest.fixture(scope="module")
def independent_values(original_sources):
    script = Path(__file__).resolve().parents[1] / "scripts/independent_multivariable.py"
    spec = importlib.util.spec_from_file_location("independent_variables", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.audit(RAW)


@pytest.fixture(scope="module")
def client(original_sources):
    with TestClient(create_app(original_sources["T2M"], v2_directory=RAW)) as client:
        yield client


def test_discovery_lists_only_six_approved_datasets(client):
    response = client.get("/v2/datasets")
    assert response.status_code == 200
    catalog = DatasetCatalog.model_validate(response.json())
    assert [item.id for item in catalog.datasets] == list(SPECS)
    assert all(item.status == "ready" and item.error is None for item in catalog.datasets)
    assert all(item.statistical_inference == "Not provided by /v2" for item in catalog.datasets)
    assert catalog.datasets[0].approved_legacy_trend_url == "/trend"
    assert all(item.approved_legacy_trend_url is None for item in catalog.datasets[1:])


@pytest.mark.parametrize("variable", tuple(SPECS))
def test_all_original_values_match_independent_decimal_audit(
    client, original_sources, independent_values, variable
):
    path = original_sources[variable]
    before = path.read_bytes()
    base = f"/v2/datasets/{variable}"
    responses = [
        client.get(f"{base}/{suffix}")
        for suffix in ("metadata", "timeseries/monthly", "timeseries/annual")
    ]
    assert all(response.status_code == 200 for response in responses)
    metadata = VariableMetadata.model_validate(responses[0].json())
    monthly = DescriptiveMonthlyResponse.model_validate(responses[1].json())
    annual = DescriptiveAnnualResponse.model_validate(responses[2].json())
    expected = independent_values[variable]
    checksum = hashlib.sha256(before).hexdigest()
    assert metadata.source_sha256 == monthly.source_sha256 == annual.source_sha256 == checksum
    assert metadata.identity.source_sha256 == expected["source_sha256"] == checksum
    assert [point.value for point in monthly.observations] == pytest.approx(
        expected["monthly_values"], rel=1e-12, abs=1e-10
    )
    assert [point.value for point in annual.observations] == pytest.approx(
        expected["annual_values"], rel=1e-12, abs=1e-10
    )
    assert len(monthly.observations) == 420 and len(annual.observations) == 35
    assert metadata.validation.fill_value_count == metadata.validation.invalid_value_count == 0
    assert metadata.validation.interpolated_observations == 0
    assert metadata.identity.shape_id == "state_dept_countries_2017/shp_85"
    assert metadata.identity.data_bbox is None
    assert path.read_bytes() == before
    if variable == "PRECTOTCORR":
        assert metadata.identity.selection_bbox is None
        assert metadata.identity.empty_url_fields == 1
    if variable == "PS":
        assert metadata.product_native_units == "Pa"
        assert metadata.exported_units == monthly.units == annual.units == "hPa"
        assert metadata.fill_value == 999999986991104
        assert all(point.value == point.source_value for point in monthly.observations)
        assert "Technical Lead" in metadata.units_basis
    if variable in {"U10M", "V10M"}:
        assert any(point.value < 0 for point in monthly.observations)
        assert any(point.value > 0 for point in monthly.observations)
        assert all(point.value == point.source_value for point in monthly.observations)


def test_v2_temperature_uses_identical_approved_snapshot_and_equal_month_means(client):
    legacy = client.get("/timeseries/monthly").json()
    v2 = client.get("/v2/datasets/T2M/timeseries/monthly").json()
    assert v2["source_sha256"] == legacy["source_sha256"]
    assert [point["source_value"] for point in v2["observations"]] == [
        point["temperature_kelvin"] for point in legacy["observations"]
    ]
    assert [point["value"] for point in v2["observations"]] == [
        point["temperature_celsius"] for point in legacy["observations"]
    ]
    annual = client.get("/timeseries/annual").json()
    v2_annual = client.get("/v2/datasets/T2M/timeseries/annual").json()
    assert v2_annual["method"] == annual["method"]
    assert [point["value"] for point in v2_annual["observations"]] == [
        point["mean_celsius"] for point in annual["observations"]
    ]


@pytest.mark.parametrize("variable", [variable for variable in SPECS if variable != "T2M"])
@pytest.mark.parametrize("failure", ["missing", "corrupt"])
def test_failure_of_any_new_dataset_leaves_temperature_and_others_ready(
    original_sources, tmp_path, variable, failure
):
    for name, path in original_sources.items():
        if name != "T2M":
            shutil.copyfile(path, tmp_path / path.name)
    target = tmp_path / SPECS[variable].filename
    if failure == "missing":
        target.unlink()
    else:
        target.write_bytes(target.read_bytes() + b"\n")  # Plausible data, changed identity.
    with TestClient(create_app(original_sources["T2M"], v2_directory=tmp_path)) as c:
        assert c.get("/health").json()["status"] == "ok"
        for route in [
            "/metadata",
            "/timeseries/monthly",
            "/timeseries/annual",
            "/climatology",
            "/trend",
        ]:
            assert c.get(route).status_code == 200
        catalog = {item["id"]: item for item in c.get("/v2/datasets").json()["datasets"]}
        assert catalog[variable]["status"] == ("missing" if failure == "missing" else "invalid")
        for other in set(SPECS) - {variable}:
            assert catalog[other]["status"] == "ready"
            assert c.get(f"/v2/datasets/{other}/timeseries/monthly").status_code == 200
        for suffix in ["metadata", "timeseries/monthly", "timeseries/annual"]:
            response = c.get(f"/v2/datasets/{variable}/{suffix}")
            assert response.status_code == 503
            error = ErrorResponse.model_validate(response.json())
            assert error.code == ("dataset_missing" if failure == "missing" else "dataset_invalid")
            if failure == "corrupt":
                assert "identity_sha256" in {issue.code for issue in error.validation.issues}


@pytest.mark.parametrize("failure", ["missing", "malformed", "wrong_variable", "wrong_units"])
def test_bad_individual_manifest_is_isolated(original_sources, tmp_path, monkeypatch, failure):
    manifests = tmp_path / "manifests"
    shutil.copytree(REPOSITORY_ROOT / "backend/src/earthscope_backend/manifests", manifests)
    target = manifests / "gambia_merra2_ps_1991_2025.json"
    if failure == "missing":
        target.unlink()
    elif failure == "malformed":
        target.write_text("{broken", encoding="utf-8")
    else:
        data = json.loads(target.read_text(encoding="utf-8"))
        data["variable" if failure == "wrong_variable" else "exported_units"] = (
            "QV2M" if failure == "wrong_variable" else "Pa"
        )
        target.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(dataset_registry, "files", lambda package: tmp_path)
    with TestClient(create_app(original_sources["T2M"], v2_directory=RAW)) as c:
        catalog = {item["id"]: item for item in c.get("/v2/datasets").json()["datasets"]}
        assert catalog["PS"]["status"] == "invalid"
        assert catalog["PS"]["error"]["validation"]["issues"][0]["code"] == "manifest_invalid"
        assert all(catalog[variable]["status"] == "ready" for variable in set(SPECS) - {"PS"})
        assert c.get("/health").json()["status"] == "ok"
        assert c.get("/trend").status_code == 200


def test_file_as_data_directory_does_not_disable_temperature(original_sources):
    with TestClient(create_app(original_sources["T2M"], v2_directory=original_sources["PS"])) as c:
        catalog = c.get("/v2/datasets").json()["datasets"]
        assert catalog[0]["status"] == "ready"
        # Windows may report an absent child path, whereas POSIX reports ENOTDIR.
        assert all(item["status"] in {"missing", "unavailable"} for item in catalog[1:])
        assert c.get("/health").json()["status"] == "ok"


def test_permission_error_for_additional_files_is_isolated(original_sources, monkeypatch):
    original_read = Path.read_bytes
    additional_names = {spec.filename for variable, spec in SPECS.items() if variable != "T2M"}

    def denied_read(path):
        if path.name in additional_names:
            raise PermissionError("Injected read denial for test; original files unchanged")
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", denied_read)
    with TestClient(create_app(original_sources["T2M"], v2_directory=RAW)) as c:
        catalog = c.get("/v2/datasets").json()["datasets"]
        assert catalog[0]["status"] == "ready"
        assert all(item["status"] == "unavailable" for item in catalog[1:])
        assert c.get("/health").json()["status"] == "ok"


def test_temperature_failure_does_not_disable_additional_variables(original_sources, tmp_path):
    with TestClient(create_app(tmp_path / "absent.csv", v2_directory=RAW)) as c:
        assert c.get("/health").json()["status"] == "degraded"
        catalog = c.get("/v2/datasets").json()["datasets"]
        assert catalog[0]["status"] == "missing"
        assert all(item["status"] == "ready" for item in catalog[1:])
        assert c.get("/v2/datasets/T2M/metadata").status_code == 503


def test_immutable_snapshot_and_restart_rechecks(original_sources, tmp_path):
    for variable, path in original_sources.items():
        if variable != "T2M":
            shutil.copyfile(path, tmp_path / path.name)
    app = create_app(original_sources["T2M"], v2_directory=tmp_path)
    route = "/v2/datasets/PS/timeseries/monthly"
    with TestClient(app) as c:
        first = c.get(route).json()
        (tmp_path / SPECS["PS"].filename).write_bytes(b"changed test copy")
        assert c.get(route).json() == first
    with TestClient(app) as c:
        assert c.get(route).status_code == 503
        assert c.get("/health").json()["status"] == "ok"


def test_v2_does_not_approve_legacy_fixture_identity(write_csv, rows, app_factory):
    with TestClient(app_factory(write_csv(rows))) as c:
        assert c.get("/timeseries/monthly").status_code == 200
        assert c.get("/v2/datasets/T2M/timeseries/monthly").status_code == 503


def test_v2_openapi_and_unsupported_requests(client):
    paths = client.get("/openapi.json").json()["paths"]
    v2_paths = {path: methods for path, methods in paths.items() if path.startswith("/v2")}
    assert len(v2_paths) == 4
    assert all(set(methods) == {"get"} for methods in v2_paths.values())
    assert "trend" not in " ".join(v2_paths)
    for suffix in ["metadata", "timeseries/monthly", "timeseries/annual"]:
        response = client.get(f"/v2/datasets/UNAPPROVED/{suffix}")
        assert response.status_code == 404
        assert ErrorResponse.model_validate(response.json()).code == "dataset_not_found"
        assert client.get(f"/v2/datasets/QV2M/{suffix}").status_code == 200
    assert client.get("/v2/datasets/QV2M/trend").status_code == 404
    assert client.post("/v2/datasets").status_code == 405


def test_manifest_sha256_agrees_with_all_original_bytes(original_sources):
    for variable, path in original_sources.items():
        assert (
            load_manifest(variable).source_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
        )
