"""Synthetic parser/conversion fixtures; these are never application observations."""

import csv
import hashlib
from dataclasses import replace
from datetime import date
from math import fsum

import pytest

from earthscope_backend.dataset_registry import descriptive_series, load_manifest, v2_data_directory
from earthscope_backend.importer import DatasetValidationError, month_range
from earthscope_backend.multivariable_importer import import_variable
from earthscope_backend.variables import SPECS

ADDITIONAL = tuple(variable for variable in SPECS if variable != "T2M")
VALUES = {"PRECTOTCORR": 1e-5, "QV2M": 0.012, "U10M": -2.5, "V10M": -1.25, "PS": 1008.5}


@pytest.fixture
def variable_csv(tmp_path):
    def write(variable, *, rows=None, metadata=None, header=None):
        manifest = load_manifest(variable).model_copy(
            update={
                "dataset_id": f"synthetic-{variable}-test-only",
                "region": "Synthetic test region, not NASA observations",
                "shape_id": "test_shapes/synthetic_region",
                "start": date(1999, 1, 1),
                "end": date(2000, 12, 1),
            }
        )
        spec = SPECS[variable]
        bbox = (
            ""
            if manifest.selection_bbox is None
            else ",".join(str(value) for value in manifest.selection_bbox)
        )
        bbox_parameter = "" if not bbox else f"bbox={bbox}"
        url = (
            f"{manifest.source_origin}{manifest.source_path}#service=ArAvTs"
            "&starttime=1999-01-01T00:00:00Z&endtime=2000-12-31T23:59:59Z"
            f"&shape={manifest.shape_id}&{bbox_parameter}&data={spec.data_id}"
        )
        entries = {
            "Title:": "Synthetic test fixture, not NASA observations",
            "User Start Date:": "1999-01-01T00:00:00Z",
            "User End Date:": "2000-12-31T23:59:59Z",
            "User Bounding Box:": bbox,
            "Data Bounding Box:": "",
            "URL to Reproduce Results:": url,
            f"Fill Value ({spec.value_column}):": str(spec.fill_value),
        }
        entries.update(metadata or {})
        path = tmp_path / spec.filename
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerows((key, value) for key, value in entries.items() if value is not None)
            writer.writerow([])
            writer.writerow(header or ["time", spec.value_column])
            writer.writerows(
                rows
                if rows is not None
                else [
                    [f"{month} 00:00:00", VALUES[variable]]
                    for month in month_range(manifest.start, manifest.end)
                ]
            )
        return path, manifest.model_copy(
            update={"source_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        )

    return write


@pytest.mark.parametrize("variable", ADDITIONAL)
def test_conversions_units_provenance_and_read_only(variable_csv, variable):
    path, manifest = variable_csv(variable)
    before = path.read_bytes()
    source = import_variable(path, manifest)
    monthly, annual = descriptive_series(source, manifest)
    assert path.read_bytes() == before
    assert source.source_sha256 == monthly.source_sha256 == annual.source_sha256
    assert source.source_sha256 == hashlib.sha256(before).hexdigest()
    assert source.validation.valid and source.validation.interpolated_observations == 0
    assert source.validation.valid_observations == 24
    assert source.raw_preamble.startswith('Title:,"Synthetic test fixture')
    assert any(entry.key == "URL to Reproduce Results:" for entry in source.source_metadata)
    first = monthly.observations[0]
    assert first.source_value == VALUES[variable]
    expected = {
        "PRECTOTCORR": 1e-5 * 86400 * 31,
        "QV2M": 12,
        "U10M": -2.5,
        "V10M": -1.25,
        "PS": 1008.5,
    }[variable]
    assert first.value == pytest.approx(expected)
    assert monthly.units == SPECS[variable].monthly_units
    assert annual.units == SPECS[variable].annual_units
    assert len(annual.observations) == 2
    assert all(point.months == 12 for point in annual.observations)


@pytest.mark.parametrize("year,days", [(1900, 28), (1999, 28), (2000, 29), (2024, 29), (2025, 28)])
def test_precipitation_calendar_and_century_leap_years(year, days):
    assert SPECS["PRECTOTCORR"].convert(1e-5, date(year, 2, 1)) == pytest.approx(
        1e-5 * 86400 * days
    )


def test_annual_precipitation_is_sum_including_leap_day(variable_csv):
    path, manifest = variable_csv("PRECTOTCORR")
    monthly, annual = descriptive_series(import_variable(path, manifest), manifest)
    for year, days in [(1999, 365), (2000, 366)]:
        result = next(point for point in annual.observations if point.year == year)
        assert result.value == pytest.approx(1e-5 * 86400 * days)
        assert result.value == fsum(p.value for p in monthly.observations if p.time.year == year)
    assert annual.aggregation == "sum"
    assert annual.observations[0].value != pytest.approx(monthly.observations[0].value)


@pytest.mark.parametrize("variable", ["QV2M", "U10M", "V10M", "PS"])
def test_new_state_annual_means_use_calendar_days(variable_csv, variable):
    value = VALUES[variable]
    delta = value * 0.01 if variable == "PS" else value
    rows = [
        [f"2000-{month:02}-01 00:00:00", value + (delta if month == 2 else 0)]
        for month in range(1, 13)
    ]
    rows = [[f"1999-{month:02}-01 00:00:00", value] for month in range(1, 13)] + rows
    path, manifest = variable_csv(variable, rows=rows)
    monthly, annual = descriptive_series(import_variable(path, manifest), manifest)
    factor = 1000 if variable == "QV2M" else 1
    assert annual.observations[1].value == pytest.approx((value + delta * 29 / 366) * factor)
    assert annual.aggregation == "calendar_day_weighted_mean"
    assert annual.observations[1].value != pytest.approx(
        fsum(p.value for p in monthly.observations if p.time.year == 2000) / 12
    )


@pytest.mark.parametrize("variable", ADDITIONAL)
def test_each_declared_sentinel_is_missing_not_an_observation(variable_csv, variable):
    path, manifest = variable_csv(variable)
    raw = path.read_text(encoding="utf-8").replace(
        f"1999-01-01 00:00:00,{VALUES[variable]}",
        f"1999-01-01 00:00:00,{manifest.fill_value}",
    )
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(DatasetValidationError) as error:
        import_variable(path, manifest)
    assert error.value.summary.fill_value_count == 1
    assert error.value.summary.valid_observations == 23
    assert "fill_value" in {issue.code for issue in error.value.summary.issues}


@pytest.mark.parametrize("variable", ADDITIONAL)
@pytest.mark.parametrize("bad", ["NaN", "inf", "-inf", "not-a-number"])
def test_nonfinite_and_nonnumeric_values_rejected(variable_csv, variable, bad):
    rows = [
        [f"{month} 00:00:00", bad if index == 0 else VALUES[variable]]
        for index, month in enumerate(month_range(date(1999, 1, 1), date(2000, 12, 1)))
    ]
    path, manifest = variable_csv(variable, rows=rows)
    with pytest.raises(DatasetValidationError) as error:
        import_variable(path, manifest)
    assert error.value.summary.invalid_value_count == 1


@pytest.mark.parametrize(
    "variable,bad",
    [
        ("PRECTOTCORR", -1e-6),
        ("PRECTOTCORR", 1),
        ("QV2M", -0.01),
        ("QV2M", 10),
        ("U10M", -151),
        ("U10M", 151),
        ("V10M", -151),
        ("V10M", 151),
        ("PS", 100850),
        ("PS", 1e15),
        ("PS", 0),
    ],
)
def test_variable_specific_screens(variable_csv, variable, bad):
    rows = [
        [f"{month} 00:00:00", bad] for month in month_range(date(1999, 1, 1), date(2000, 12, 1))
    ]
    path, manifest = variable_csv(variable, rows=rows)
    with pytest.raises(DatasetValidationError) as error:
        import_variable(path, manifest)
    assert error.value.summary.invalid_value_count == 24
    assert error.value.summary.fill_value_count == 0


@pytest.mark.parametrize("variable", ["U10M", "V10M"])
def test_signed_zero_and_positive_wind_components_preserved(variable_csv, variable):
    values = [-3, 0, 3] * 8
    rows = [
        [f"{month} 00:00:00", value]
        for month, value in zip(
            month_range(date(1999, 1, 1), date(2000, 12, 1)), values, strict=True
        )
    ]
    path, manifest = variable_csv(variable, rows=rows)
    monthly, _ = descriptive_series(import_variable(path, manifest), manifest)
    assert [point.value for point in monthly.observations] == values


@pytest.mark.parametrize(
    "case,code",
    [
        ("gap", "missing_month"),
        ("duplicate", "duplicate_month"),
        ("unexpected", "unexpected_month"),
        ("timestamp", "timestamp"),
        ("width", "row_width"),
    ],
)
def test_time_and_row_integrity(variable_csv, case, code):
    rows = [
        [f"{month} 00:00:00", 0.012] for month in month_range(date(1999, 1, 1), date(2000, 12, 1))
    ]
    if case == "gap":
        rows.pop(1)
    elif case == "duplicate":
        rows[1] = rows[0]
    elif case == "unexpected":
        rows[0][0] = "1998-12-01 00:00:00"
    elif case == "timestamp":
        rows[0][0] = "1999-01-02 00:00:00"
    else:
        rows[0].append("extra")
    path, manifest = variable_csv("QV2M", rows=rows)
    with pytest.raises(DatasetValidationError) as error:
        import_variable(path, manifest)
    assert code in {issue.code for issue in error.value.summary.issues}


def test_out_of_order_valid_rows_are_sorted_with_warning(variable_csv):
    rows = [
        [f"{month} 00:00:00", 0.012]
        for month in reversed(month_range(date(1999, 1, 1), date(2000, 12, 1)))
    ]
    path, manifest = variable_csv("QV2M", rows=rows)
    before = path.read_bytes()
    source = import_variable(path, manifest)
    assert not source.validation.input_was_sorted and source.validation.warnings
    assert source.observations[0].time == date(1999, 1, 1)
    assert path.read_bytes() == before


@pytest.mark.parametrize("case", ["partial", "duplicate"])
def test_annual_requires_twelve_distinct_months(variable_csv, case):
    path, manifest = variable_csv("PRECTOTCORR")
    source = import_variable(path, manifest)
    points = source.observations[:11]
    if case == "duplicate":
        points += (points[0],)
    with pytest.raises(DatasetValidationError, match="all 12 distinct months"):
        descriptive_series(replace(source, observations=points), manifest)


@pytest.mark.parametrize(
    "key,value,code",
    [
        ("User Start Date:", "1998-01-01T00:00:00Z", "identity_period"),
        ("User End Date:", "2000-12-01T00:00:00Z", "identity_period"),
        ("User Bounding Box:", "1,2,3,4", "identity_bbox"),
        ("Data Bounding Box:", "1,2,3,4", "identity_data_bbox"),
        ("Title:", None, "metadata_title"),
        ("Fill Value (mean_M2IMNXASM_5_12_4_QV2M):", "9999", "metadata_fill"),
    ],
)
def test_metadata_identity_is_independent_of_checksum(variable_csv, key, value, code):
    path, manifest = variable_csv("QV2M", metadata={key: value})
    with pytest.raises(DatasetValidationError) as error:
        import_variable(path, manifest)
    assert code in {issue.code for issue in error.value.summary.issues}
    assert "identity_sha256" not in {issue.code for issue in error.value.summary.issues}


@pytest.mark.parametrize(
    "before,after,code",
    [
        ("https://giovanni.gsfc.nasa.gov/", "https://example.org/", "identity_source"),
        ("/giovanni/#", "/other/#", "identity_source"),
        ("service=ArAvTs", "service=Other", "identity_service"),
        ("shape=test_shapes/synthetic_region", "shape=other/shape", "identity_shape"),
        ("data=M2IMNXASM_5_12_4_QV2M", "data=M2TMNXSLV_5_12_4_PS", "identity_data"),
        ("starttime=1999", "starttime=1998", "identity_starttime"),
        ("bbox=-16.8296", "bbox=-16.8", "identity_bbox"),
        ("&data=", "&&data=", "identity_source"),
        ("&data=", "&service=ArAvTs&data=", "identity_source"),
    ],
)
def test_url_identity_and_ambiguous_parameters(variable_csv, before, after, code):
    path, manifest = variable_csv("QV2M")
    path.write_bytes(path.read_bytes().replace(before.encode(), after.encode()))
    manifest = manifest.model_copy(
        update={"source_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    )
    with pytest.raises(DatasetValidationError) as error:
        import_variable(path, manifest)
    assert code in {issue.code for issue in error.value.summary.issues}


@pytest.mark.parametrize("variable", ADDITIONAL)
def test_even_plausible_changed_observation_requires_new_identity(variable_csv, variable):
    path, manifest = variable_csv(variable)
    path.write_bytes(
        path.read_bytes().replace(
            f"1999-01-01 00:00:00,{VALUES[variable]}".encode(),
            f"1999-01-01 00:00:00,{VALUES[variable] * 0.99}".encode(),
        )
    )
    with pytest.raises(DatasetValidationError) as error:
        import_variable(path, manifest)
    assert "identity_sha256" in {issue.code for issue in error.value.summary.issues}
    assert error.value.summary.invalid_value_count == 0


def test_precipitation_absent_bounds_remain_unknown(variable_csv):
    path, manifest = variable_csv("PRECTOTCORR")
    assert manifest.selection_bbox is None and manifest.empty_url_fields == 1
    assert import_variable(path, manifest).validation.valid
    path, manifest = variable_csv("PRECTOTCORR", metadata={"User Bounding Box:": "1,2,3,4"})
    with pytest.raises(DatasetValidationError) as error:
        import_variable(path, manifest)
    assert "identity_bbox" in {issue.code for issue in error.value.summary.issues}


def test_v2_relative_data_directory_independent_of_cwd(monkeypatch, tmp_path):
    from earthscope_backend.config import REPOSITORY_ROOT

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EARTHSCOPE_V2_DATA_DIR", "data/raw")
    assert v2_data_directory() == REPOSITORY_ROOT / "data/raw"
    monkeypatch.setenv("EARTHSCOPE_V2_DATA_DIR", str(tmp_path))
    assert v2_data_directory() == tmp_path
