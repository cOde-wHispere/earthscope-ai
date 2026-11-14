import hashlib
from datetime import date

import pytest

from earthscope_backend.config import VALUE_COLUMN
from earthscope_backend.importer import (
    DatasetUnavailableError,
    DatasetValidationError,
    import_giovanni,
    kelvin_to_celsius,
    month_range,
)


@pytest.mark.parametrize("kelvin,celsius", [(273.15, 0), (300, 26.85), (0, -273.15)])
def test_kelvin_conversion(kelvin, celsius):
    assert kelvin_to_celsius(kelvin) == pytest.approx(celsius)


@pytest.mark.parametrize("kelvin", [-1, float("nan"), float("inf")])
def test_kelvin_conversion_rejects_invalid(kelvin):
    with pytest.raises(ValueError, match="finite"):
        kelvin_to_celsius(kelvin)


def test_exact_coverage_and_metadata(write_csv, rows):
    path = write_csv(rows)
    before = path.read_bytes()
    dataset = import_giovanni(path)
    assert len(dataset.observations) == 420
    assert tuple(point.time for point in dataset.observations) == month_range(
        date(1991, 1, 1), date(2025, 12, 1)
    )
    assert dataset.metadata.validation.valid
    assert dataset.metadata.source_sha256 == hashlib.sha256(before).hexdigest()
    assert dataset.metadata.raw_preamble.startswith('Title:,"Synthetic test fixture,')
    assert len(dataset.metadata.source_metadata) == 6
    assert dataset.metadata.region.startswith("Unverified")
    assert "The Gambia" not in dataset.metadata.region
    assert path.read_bytes() == before


def test_unsorted_rows_are_sorted_and_disclosed(write_csv, rows):
    dataset = import_giovanni(write_csv(rows[::-1]))
    assert dataset.observations[0].time == date(1991, 1, 1)
    assert dataset.observations[-1].time == date(2025, 12, 1)
    assert not dataset.metadata.validation.input_was_sorted
    assert dataset.metadata.validation.warnings


def test_duplicate_timestamp(write_csv, rows):
    rows[1] = rows[0].copy()
    with pytest.raises(DatasetValidationError) as caught:
        import_giovanni(write_csv(rows))
    assert caught.value.summary.duplicate_months == ("1991-01",)
    assert caught.value.summary.missing_months == ("1991-02",)


@pytest.mark.parametrize("index", [0, 200, 419])
def test_missing_period_including_boundaries(write_csv, rows, index):
    missing = rows.pop(index)[0][:7]
    with pytest.raises(DatasetValidationError) as caught:
        import_giovanni(write_csv(rows))
    assert caught.value.summary.missing_months == (missing,)
    assert caught.value.summary.interpolated_observations == 0
    assert "interpolation is disabled" in str(caught.value)


@pytest.mark.parametrize("value", ["", "NaN", "inf", "-inf", "abc", "0", "-2", "400"])
def test_invalid_numeric_values(write_csv, rows, value):
    rows[5][1] = value
    with pytest.raises(DatasetValidationError) as caught:
        import_giovanni(write_csv(rows))
    assert caught.value.summary.invalid_value_count == 1
    assert caught.value.summary.valid_observations == 419
    assert any(
        issue.code == "invalid_value" and issue.line for issue in caught.value.summary.issues
    )


@pytest.mark.parametrize("value", ["1000000000000000", "1e15", "1000000000000000.0"])
def test_fill_value_is_not_a_temperature(write_csv, rows, value):
    rows[3][1] = value
    with pytest.raises(DatasetValidationError) as caught:
        import_giovanni(write_csv(rows))
    assert caught.value.summary.fill_value_count == 1
    assert caught.value.summary.valid_observations == 419
    assert caught.value.summary.invalid_value_count == 0


@pytest.mark.parametrize(
    "stamp", ["bad", "1991-01-15 00:00:00", "1991-01-01 01:00:00", "1991-1-1 00:00:00"]
)
def test_bad_timestamps(write_csv, rows, stamp):
    rows[0][0] = stamp
    with pytest.raises(DatasetValidationError) as caught:
        import_giovanni(write_csv(rows))
    assert any(issue.code == "timestamp" for issue in caught.value.summary.issues)


def test_unexpected_period(write_csv, rows):
    rows[-1][0] = "2026-01-01 00:00:00"
    with pytest.raises(DatasetValidationError) as caught:
        import_giovanni(write_csv(rows))
    assert caught.value.summary.unexpected_months == ("2026-01",)


@pytest.mark.parametrize("header", [["time", "wrong_product"], ["time", VALUE_COLUMN, "extra"]])
def test_wrong_header(write_csv, rows, header):
    with pytest.raises(DatasetValidationError) as caught:
        import_giovanni(write_csv(rows, header=header))
    assert any(issue.code == "header_missing" for issue in caught.value.summary.issues)


def test_extra_data_column(write_csv, rows):
    rows[0].append("unexpected")
    with pytest.raises(DatasetValidationError) as caught:
        import_giovanni(write_csv(rows))
    assert any(issue.code == "row_width" for issue in caught.value.summary.issues)


def test_empty_measurement_row_is_rejected(write_csv, rows):
    rows[0] = ["", ""]
    with pytest.raises(DatasetValidationError) as caught:
        import_giovanni(write_csv(rows))
    assert caught.value.summary.observed_rows == 420
    assert caught.value.summary.invalid_value_count == 1


def test_duplicate_metadata_is_rejected(write_csv, rows):
    path = write_csv(rows)
    path.write_text("Title:,second title\n" + path.read_text(), encoding="utf-8")
    with pytest.raises(DatasetValidationError) as caught:
        import_giovanni(path)
    assert any(issue.code == "duplicate_metadata" for issue in caught.value.summary.issues)


def test_missing_metadata(write_csv, rows):
    with pytest.raises(DatasetValidationError) as caught:
        import_giovanni(write_csv(rows, metadata=[]))
    codes = {issue.code for issue in caught.value.summary.issues}
    assert {"metadata_period", "metadata_title", "metadata_fill"} <= codes


def test_metadata_period_and_fill_mismatch(write_csv, rows):
    path = write_csv(rows)
    text = (
        path.read_text().replace("1991-01-01T", "1992-01-01T").replace("1000000000000000", "-9999")
    )
    path.write_text(text, encoding="utf-8")
    with pytest.raises(DatasetValidationError) as caught:
        import_giovanni(path)
    assert {"metadata_period", "metadata_fill"} <= {
        issue.code for issue in caught.value.summary.issues
    }


@pytest.mark.parametrize("line_ending", ["\n", "\r\n"])
def test_quoted_multiline_metadata_and_utf8_bom(write_csv, rows, line_ending):
    path = write_csv(rows)
    text = path.read_text().replace(
        '"Synthetic test fixture, not NASA observations"',
        f'"Synthetic test fixture,{line_ending}second line"',
    )
    path.write_bytes(text.encode("utf-8-sig"))
    dataset = import_giovanni(path)
    assert (
        dataset.metadata.source_metadata[0].value
        == f"Synthetic test fixture,{line_ending}second line"
    )
    assert "second line" in dataset.metadata.raw_preamble
    assert len(dataset.observations) == 420


@pytest.mark.parametrize(
    "content,code", [(b'"unclosed', "csv_syntax"), (b"\xff", "encoding"), (b"", "header_missing")]
)
def test_malformed_input(tmp_path, content, code):
    path = tmp_path / "bad.csv"
    path.write_bytes(content)
    with pytest.raises(DatasetValidationError) as caught:
        import_giovanni(path)
    assert any(issue.code == code for issue in caught.value.summary.issues)


def test_missing_file_and_unreadable_directory(tmp_path):
    with pytest.raises(DatasetUnavailableError, match="EARTHSCOPE_DATA_PATH"):
        import_giovanni(tmp_path / "missing.csv")
    with pytest.raises(DatasetUnavailableError, match="permissions"):
        import_giovanni(tmp_path)
