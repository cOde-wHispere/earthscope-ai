"""Read the actual Giovanni metadata-preamble CSV without altering the source."""

import csv
import hashlib
import io
import math
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from earthscope_backend.config import (
    EXPECTED_END,
    EXPECTED_START,
    FILL_VALUE,
    VALUE_COLUMN,
)
from earthscope_backend.schemas import (
    DatasetMetadata,
    MetadataEntry,
    ValidationIssue,
    ValidationSummary,
)


@dataclass(frozen=True)
class Observation:
    time: date
    kelvin: float

    @property
    def celsius(self) -> float:
        return kelvin_to_celsius(self.kelvin)


@dataclass(frozen=True)
class Dataset:
    observations: tuple[Observation, ...]
    metadata: DatasetMetadata


class DatasetUnavailableError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class DatasetValidationError(ValueError):
    def __init__(self, summary: ValidationSummary):
        super().__init__("; ".join(issue.message for issue in summary.issues))
        self.summary = summary


def kelvin_to_celsius(kelvin: float) -> float:
    if not math.isfinite(kelvin) or kelvin < 0:
        raise ValueError("Temperature must be finite and at least 0 Kelvin.")
    return kelvin - 273.15


def month_range(start: date, end: date) -> tuple[date, ...]:
    if start.day != 1 or end.day != 1 or start > end:
        raise ValueError("Expected coverage must use ordered month-start dates.")
    return tuple(
        date(index // 12, index % 12 + 1, 1)
        for index in range(start.year * 12 + start.month - 1, end.year * 12 + end.month)
    )


def import_giovanni(
    path: Path,
    *,
    expected_start: date = EXPECTED_START,
    expected_end: date = EXPECTED_END,
) -> Dataset:
    """Reject gaps, duplicate months and invalid rows; sort valid input explicitly."""
    expected = month_range(expected_start, expected_end)
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise DatasetUnavailableError(
            "dataset_missing",
            f"Source dataset '{path.name}' is missing. Set EARTHSCOPE_DATA_PATH to the "
            "local Giovanni CSV and restart the service.",
        ) from exc
    except OSError as exc:
        raise DatasetUnavailableError(
            "dataset_unavailable",
            "Cannot read source dataset. Check EARTHSCOPE_DATA_PATH and file permissions, "
            "then restart the service.",
        ) from exc

    issues: list[ValidationIssue] = []
    entries: list[MetadataEntry] = []
    observations: list[Observation] = []
    timestamps: list[date] = []
    observed_rows = invalid_count = fill_count = header_start = 0
    header_found = False

    def issue(code: str, message: str, line: int | None = None, period: str | None = None):
        issues.append(ValidationIssue(code=code, message=message, line=line, period=period))

    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = ""
        issue("encoding", "CSV must use UTF-8 encoding. Re-export it from Giovanni.")
    lines = decoded.splitlines(keepends=True)
    reader = csv.reader(io.StringIO(decoded, newline=""), skipinitialspace=True, strict=True)
    try:
        while True:
            row_start = reader.line_num
            row = next(reader, None)
            if row is None:
                break
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            stripped = [cell.strip() for cell in row]
            if not header_found:
                if stripped == ["time", VALUE_COLUMN]:
                    header_found = True
                    header_start = row_start
                elif len(row) == 2 and stripped[0].endswith(":"):
                    entries.append(MetadataEntry(key=row[0], value=row[1]))
                else:
                    issue(
                        "metadata_or_header",
                        f"Line {reader.line_num}: expected a 'key:,value' metadata row or "
                        f"the header 'time, {VALUE_COLUMN}'.",
                        reader.line_num,
                    )
                continue

            observed_rows += 1
            line = reader.line_num
            if len(row) != 2:
                issue("row_width", f"Line {line}: expected exactly 2 data columns.", line)
                continue
            timestamp = None
            try:
                parsed = datetime.strptime(stripped[0], "%Y-%m-%d %H:%M:%S")
                if (
                    parsed.day != 1
                    or parsed.time() != datetime.min.time()
                    or parsed.strftime("%Y-%m-%d %H:%M:%S") != stripped[0]
                ):
                    raise ValueError
                timestamp = parsed.date()
                timestamps.append(timestamp)
            except ValueError:
                issue(
                    "timestamp",
                    f"Line {line}: expected a month-start timestamp YYYY-MM-01 00:00:00; "
                    f"got {stripped[0]!r}.",
                    line,
                )
            try:
                value = float(stripped[1])
            except ValueError:
                value = math.nan
            if value == FILL_VALUE:
                fill_count += 1
                issue("fill_value", f"Line {line}: fill value is a missing measurement.", line)
            elif not math.isfinite(value) or not 150 <= value <= 350:
                invalid_count += 1
                issue(
                    "invalid_value",
                    f"Line {line}: expected finite monthly T2M in the conservative 150..350 K "
                    f"screen; got {stripped[1]!r}. Check units and source export.",
                    line,
                )
            elif timestamp is not None:
                observations.append(Observation(timestamp, value))
    except csv.Error as exc:
        issue("csv_syntax", f"Line {reader.line_num}: malformed CSV: {exc}.", reader.line_num)

    if not header_found:
        issue("header_missing", f"Required data header 'time, {VALUE_COLUMN}' was not found.")
    metadata = {entry.key.strip().removesuffix(":"): entry.value.strip() for entry in entries}
    keys = [entry.key.strip().removesuffix(":") for entry in entries]
    if len(set(keys)) != len(keys):
        issue("duplicate_metadata", "Metadata keys must be unique; re-export the Giovanni CSV.")
    for key, expected_date in (
        ("User Start Date", expected_start),
        ("User End Date", expected_end),
    ):
        try:
            stamp = datetime.strptime(metadata.get(key, ""), "%Y-%m-%dT%H:%M:%SZ")
            if (stamp.year, stamp.month) != (expected_date.year, expected_date.month):
                raise ValueError
        except ValueError:
            issue(
                "metadata_period",
                f"Metadata '{key}' must declare the expected month {expected_date:%Y-%m} "
                "as an ISO UTC timestamp.",
            )
    if not metadata.get("Title"):
        issue("metadata_title", "Required Giovanni 'Title:' metadata is missing or empty.")
    try:
        fill = float(metadata.get(f"Fill Value ({VALUE_COLUMN})", ""))
        if fill != FILL_VALUE:
            raise ValueError
    except ValueError:
        issue(
            "metadata_fill", f"Metadata must declare fill value {FILL_VALUE:g} for {VALUE_COLUMN}."
        )

    counts = Counter(timestamps)
    missing = tuple(f"{month:%Y-%m}" for month in expected if month not in counts)
    duplicates = tuple(f"{month:%Y-%m}" for month in sorted(counts) if counts[month] > 1)
    unexpected = tuple(f"{month:%Y-%m}" for month in sorted(set(counts) - set(expected)))
    for code, periods, action in (
        ("missing_month", missing, "Restore the original measurement; interpolation is disabled"),
        ("duplicate_month", duplicates, "Resolve duplicate source rows; no averaging is performed"),
        ("unexpected_month", unexpected, "Use the requested dataset coverage"),
    ):
        for period in periods:
            issue(code, f"{code.replace('_', ' ').capitalize()} {period}. {action}.", period=period)
    if observed_rows != len(expected):
        issue("row_count", f"Expected {len(expected)} monthly rows; found {observed_rows}.")
    ordered = timestamps == sorted(timestamps)
    summary = ValidationSummary(
        valid=not issues,
        expected_observations=len(expected),
        observed_rows=observed_rows,
        valid_observations=len(observations),
        expected_start=expected_start,
        expected_end=expected_end,
        missing_months=missing,
        duplicate_months=duplicates,
        unexpected_months=unexpected,
        invalid_value_count=invalid_count,
        fill_value_count=fill_count,
        input_was_sorted=ordered,
        issues=tuple(issues),
        warnings=()
        if ordered
        else ("Input rows were reordered chronologically; values unchanged.",),
    )
    if issues:
        raise DatasetValidationError(summary)
    return Dataset(
        observations=tuple(sorted(observations, key=lambda item: item.time)),
        metadata=DatasetMetadata(
            source_name=path.name,
            source_sha256=hashlib.sha256(raw).hexdigest(),
            value_column=VALUE_COLUMN,
            fill_value=FILL_VALUE,
            raw_preamble="".join(lines[:header_start]),
            source_metadata=tuple(entries),
            validation=summary,
        ),
    )


def main() -> int:
    # A separate CLI avoids duplicate __main__/package exception classes under python -m.
    from earthscope_backend.cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
