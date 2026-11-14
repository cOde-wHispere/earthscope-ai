import hashlib

import pytest
from fastapi.testclient import TestClient

from earthscope_backend.identity import (
    DatasetIdentity,
    load_baseline_identity,
    load_verified_dataset,
    validate_identity,
)
from earthscope_backend.importer import DatasetValidationError, import_giovanni
from earthscope_backend.main import create_app
from earthscope_backend.schemas import ErrorResponse


@pytest.mark.parametrize(
    "original,replacement,code",
    [
        ("test_shapes/synthetic_region", "test_shapes/other_country", "identity_shape"),
        ("M2IMNXASM_5_12_4_T2M", "M2TMNXSLV_5_12_4_T2M", "identity_collection"),
        ("M2IMNXASM_5_12_4_T2M", "M2IMNXASM_5_12_5_T2M", "identity_collection"),
        ("M2IMNXASM_5_12_4_T2M", "M2IMNXASM_5_12_4_T10M", "identity_variable"),
        ("M2IMNXASM_5_12_4_T2M", "M2IMNXASM_5_12_4_EXTRA_T2M", "identity_data"),
        ("service=ArAvTs", "service=TmAvMp", "identity_service"),
        ("service=ArAvTs", "service=ArAvTs&service=ArAvTs", "identity_service"),
        ("shape=test_shapes", "shape=other&shape=test_shapes", "identity_shape"),
        ("https://giovanni.gsfc.nasa.gov", "https://example.org", "identity_source"),
        (
            "https://giovanni.gsfc.nasa.gov",
            "https://giovanni.gsfc.nasa.gov.evil.test",
            "identity_source",
        ),
        (
            "https://giovanni.gsfc.nasa.gov",
            "https://user@giovanni.gsfc.nasa.gov",
            "identity_source",
        ),
        ("https://giovanni.gsfc.nasa.gov", "http://giovanni.gsfc.nasa.gov", "identity_source"),
        ("/giovanni/#", "/other/#", "identity_source"),
        ("/giovanni/#", "/giovanni/?service=ArAvTs#", "identity_source"),
        ("bbox=-16.8296", "bbox=-15.8296", "identity_bbox"),
    ],
)
def test_identity_checks_are_independent_of_approved_checksum(
    write_csv,
    rows,
    fixture_identity,
    original,
    replacement,
    code,
):
    path = write_csv(rows)
    # Alter metadata only, so the numeric/coverage parser still succeeds. In these tests
    # approve the altered bytes to isolate identity checks from the digest check.
    raw = path.read_bytes()
    assert original.encode() in raw
    path.write_bytes(raw.replace(original.encode(), replacement.encode(), 1))
    identity = fixture_identity(path)
    parsed = import_giovanni(path)
    assert "The Gambia" not in parsed.metadata.region
    with pytest.raises(DatasetValidationError) as caught:
        validate_identity(parsed, identity)
    assert code in {issue.code for issue in caught.value.summary.issues}


def test_unapproved_snapshot_is_rejected_but_separate_identity_can_be_approved(
    write_csv,
    rows,
    fixture_identity,
):
    path = write_csv(rows)
    original_identity = fixture_identity(path)
    rows[0][1] = str(float(rows[0][1]) + 0.01)
    write_csv(rows)
    with pytest.raises(DatasetValidationError) as caught:
        load_verified_dataset(path, original_identity)
    assert {issue.code for issue in caught.value.summary.issues} == {"identity_sha256"}
    revised_identity = original_identity.model_copy(
        update={
            "dataset_id": "separately-reviewed-synthetic-snapshot-v2",
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
    revised = load_verified_dataset(path, revised_identity)
    assert revised.metadata.region == revised_identity.region
    assert original_identity.source_sha256 != revised_identity.source_sha256
    assert original_identity.dataset_id != revised_identity.dataset_id


def test_missing_reproduction_url_is_rejected(write_csv, rows, fixture_identity):
    path = write_csv(rows)
    raw = path.read_bytes()
    path.write_bytes(
        b"\n".join(line for line in raw.splitlines() if not line.startswith(b"URL to "))
    )
    with pytest.raises(DatasetValidationError) as caught:
        load_verified_dataset(path, fixture_identity(path))
    assert "identity_source" in {issue.code for issue in caught.value.summary.issues}


def test_manifest_is_required_when_packaged(monkeypatch, tmp_path):
    import earthscope_backend.identity as identity_module

    monkeypatch.setattr(identity_module, "files", lambda package: tmp_path)
    with TestClient(create_app(tmp_path / "source.csv")) as client:
        response = client.get("/metadata")
        assert response.status_code == 503
        error = ErrorResponse.model_validate(response.json())
        assert error.code == "dataset_invalid"
        assert error.validation.issues[0].code == "manifest_invalid"
        assert client.get("/health").json()["dataset_status"] == "invalid"


def test_malformed_packaged_manifest_is_rejected(monkeypatch, tmp_path):
    import earthscope_backend.identity as identity_module

    folder = tmp_path / "manifests"
    folder.mkdir()
    (folder / "gambia_merra2_1991_2025.json").write_text('{"dataset_id": "incomplete"}')
    monkeypatch.setattr(identity_module, "files", lambda package: tmp_path)
    with pytest.raises(DatasetValidationError) as caught:
        load_baseline_identity()
    assert caught.value.summary.issues[0].code == "manifest_invalid"


def test_environment_data_path_does_not_approve_a_different_identity(
    monkeypatch,
    write_csv,
    rows,
):
    monkeypatch.setenv("EARTHSCOPE_DATA_PATH", str(write_csv(rows)))
    with TestClient(create_app()) as client:
        assert client.get("/health").json()["dataset_status"] == "invalid"
        response = client.get("/metadata")
        assert response.status_code == 503
        assert "region" not in response.json()
        codes = {item["code"] for item in response.json()["validation"]["issues"]}
        assert {"identity_shape", "identity_sha256"} <= codes


def test_manifest_schema_roundtrip():
    identity = load_baseline_identity()
    assert DatasetIdentity.model_validate_json(identity.model_dump_json()) == identity
    assert identity.data_id == "M2IMNXASM_5_12_4_T2M"


@pytest.mark.integration
def test_mvp_approved_copy_is_independent_of_filename(nasa_path, tmp_path):
    path = tmp_path / "mounted-baseline.csv"
    path.write_bytes(nasa_path.read_bytes())
    with TestClient(create_app(path)) as client:
        metadata = client.get("/metadata")
        assert metadata.status_code == 200
        assert metadata.json()["region"] == load_baseline_identity().region
        assert metadata.json()["source_name"] == "mounted-baseline.csv"


@pytest.mark.integration
def test_baseline_checksum_mismatch_is_rejected_at_startup(nasa_path, tmp_path):
    path = tmp_path / "changed.csv"
    path.write_bytes(nasa_path.read_bytes().replace(b"298.871277", b"298.971277", 1))
    assert import_giovanni(path).metadata.validation.valid  # Valid measurements, unapproved bytes.
    with TestClient(create_app(path)) as client:
        health = client.get("/health").json()
        assert health["status"] == "degraded"
        assert health["dataset_status"] == "invalid"
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
            assert error.validation.valid is False
            assert {issue.code for issue in error.validation.issues} == {"identity_sha256"}


@pytest.mark.integration
@pytest.mark.parametrize(
    "original,replacement,code",
    [
        (b"shp_85", b"shp_86", "identity_shape"),
        (b"data=M2IMNXASM", b"data=M2TMNXSLV", "identity_collection"),
        (b"service=ArAvTs", b"service=TmAvMp", "identity_service"),
        (b"https://giovanni.gsfc.nasa.gov", b"https://example.org", "identity_source"),
    ],
)
def test_baseline_startup_reports_altered_identity(
    nasa_path, tmp_path, original, replacement, code
):
    path = tmp_path / "altered-metadata.csv"
    path.write_bytes(nasa_path.read_bytes().replace(original, replacement, 1))
    with TestClient(create_app(path)) as client:
        assert client.get("/health").json()["dataset_status"] == "invalid"
        response = client.get("/metadata")
        assert response.status_code == 503
        error = ErrorResponse.model_validate(response.json())
        assert {code, "identity_sha256"} <= {issue.code for issue in error.validation.issues}
