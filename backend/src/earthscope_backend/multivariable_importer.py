"""Strict read-only import for additional variables, isolated from the T2M importer."""

import csv
import hashlib
import io
import math
from calendar import monthrange
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from earthscope_backend.importer import (
    DatasetUnavailableError,
    DatasetValidationError,
    month_range,
)
from earthscope_backend.multivariable_schemas import DatasetManifest
from earthscope_backend.schemas import MetadataEntry, ValidationIssue, ValidationSummary
from earthscope_backend.variables import SPECS


@dataclass(frozen=True)
class SourcePoint:
    time: date
    value: float


@dataclass(frozen=True)
class VariableSource:
    observations: tuple[SourcePoint, ...]
    source_name: str
    source_sha256: str
    raw_preamble: str
    source_metadata: tuple[MetadataEntry, ...]
    validation: ValidationSummary


def identity_issues(
    metadata: dict[str, str], manifest: DatasetManifest, source_sha256: str
) -> list[ValidationIssue]:
    """Check source support independently of numeric plausibility and the pinned checksum."""
    issues: list[ValidationIssue] = []

    def issue(code: str, message: str):
        issues.append(ValidationIssue(code=code, message=message))

    url = metadata.get("URL to Reproduce Results", "")
    params: dict[str, list[str]] = {}
    try:
        parsed = urlsplit(url)
        if (
            f"{parsed.scheme}://{parsed.netloc}" != manifest.source_origin
            or parsed.path != manifest.source_path
            or parsed.query
            or any(char.isspace() or ord(char) < 32 for char in url)
        ):
            raise ValueError
        fields = parsed.fragment.split("&")
        if fields.count("") != manifest.empty_url_fields:
            raise ValueError
        # Only this manifest's explicitly approved empty separators may be removed.
        params = parse_qs(
            "&".join(field for field in fields if field),
            keep_blank_values=True,
            strict_parsing=True,
        )
        if any(len(values) != 1 for values in params.values()):
            raise ValueError
    except ValueError:
        issue("identity_source", "Unapproved Giovanni reproduction URL or parameter structure.")

    end_day = monthrange(manifest.end.year, manifest.end.month)[1]
    expected_start = f"{manifest.start.isoformat()}T00:00:00Z"
    expected_end = f"{manifest.end.year:04}-{manifest.end.month:02}-{end_day:02}T23:59:59Z"
    for key, expected in (
        ("service", manifest.service),
        ("shape", manifest.shape_id),
        ("data", SPECS[manifest.variable].data_id),
        ("starttime", expected_start),
        ("endtime", expected_end),
    ):
        if params.get(key) != [expected]:
            issue(f"identity_{key}", f"URL '{key}' must occur once and equal {expected!r}.")
    for key, expected in (("User Start Date", expected_start), ("User End Date", expected_end)):
        if metadata.get(key) != expected:
            issue("identity_period", f"'{key}' must equal {expected!r}.")
    if manifest.selection_bbox is None:
        if "bbox" in params or metadata.get("User Bounding Box") != "":
            issue("identity_bbox", "This approved export has no URL or user selection bounds.")
    else:
        for label, values in (
            ("URL bbox", params.get("bbox", [])),
            ("User Bounding Box", [metadata.get("User Bounding Box", "")]),
        ):
            try:
                if len(values) != 1:
                    raise ValueError
                if tuple(float(part) for part in values[0].split(",")) != manifest.selection_bbox:
                    raise ValueError
            except ValueError:
                issue("identity_bbox", f"{label} does not match approved selection bounds.")
    if metadata.get("Data Bounding Box") != "":
        issue("identity_data_bbox", "Approved export declares an empty data bounding box.")
    if source_sha256 != manifest.source_sha256:
        issue(
            "identity_sha256",
            f"Source SHA-256 mismatch: expected {manifest.source_sha256}; "
            f"observed {source_sha256}. Restore original bytes; new exports need review.",
        )
    return issues


def import_variable(path: Path, manifest: DatasetManifest) -> VariableSource:
    """No gap filling, duplicate averaging, clipping or unit guessing is performed."""
    if manifest.variable == "T2M":
        raise ValueError("T2M must use the approved legacy importer and identity validator.")
    spec = SPECS[manifest.variable]
    expected = month_range(manifest.start, manifest.end)
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise DatasetUnavailableError(
            "dataset_missing",
            f"Approved {manifest.variable} CSV is missing. Restore it and restart.",
        ) from exc
    except OSError as exc:
        raise DatasetUnavailableError(
            "dataset_unavailable", f"Cannot read {manifest.variable} CSV. Check mount permissions."
        ) from exc
    checksum = hashlib.sha256(raw).hexdigest()
    issues: list[ValidationIssue] = []
    entries: list[MetadataEntry] = []
    observations: list[SourcePoint] = []
    timestamps: list[date] = []
    observed_rows = invalid_count = fill_count = header_start = 0
    header_found = False

    def issue(code: str, message: str, line: int | None = None, period: str | None = None):
        issues.append(ValidationIssue(code=code, message=message, line=line, period=period))

    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = ""
        issue("encoding", "CSV must be UTF-8.")
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
                if stripped == ["time", spec.value_column]:
                    header_found = True
                    header_start = row_start
                elif len(row) == 2 and stripped[0].endswith(":"):
                    entries.append(MetadataEntry(key=row[0], value=row[1]))
                else:
                    issue(
                        "metadata_or_header",
                        "Unexpected metadata or value column.",
                        reader.line_num,
                    )
                continue
            observed_rows += 1
            line = reader.line_num
            if len(row) != 2:
                issue("row_width", "Expected exactly two data columns.", line)
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
                issue("timestamp", "Expected YYYY-MM-01 00:00:00 timestamp.", line)
            try:
                value = float(stripped[1])
            except ValueError:
                value = math.nan
            if value == manifest.fill_value:
                fill_count += 1
                issue("fill_value", "Declared fill value is a missing measurement.", line)
            elif not math.isfinite(value) or not spec.minimum <= value <= spec.maximum:
                invalid_count += 1
                issue(
                    "invalid_value",
                    f"Expected finite {manifest.variable} in inclusive engineering screen "
                    f"{spec.minimum}..{spec.maximum} {spec.exported_units}; check export units.",
                    line,
                )
            elif timestamp is not None:
                observations.append(SourcePoint(timestamp, value))
    except csv.Error:
        issue("csv_syntax", "Malformed CSV.", reader.line_num)

    if not header_found:
        issue("header_missing", f"Required header time, {spec.value_column} was not found.")
    metadata = {entry.key.strip().removesuffix(":"): entry.value.strip() for entry in entries}
    if len(metadata) != len(entries):
        issue("duplicate_metadata", "Metadata keys must be unique.")
    if not metadata.get("Title"):
        issue("metadata_title", "Required Giovanni Title is missing or empty.")
    try:
        if float(metadata.get(f"Fill Value ({spec.value_column})", "")) != manifest.fill_value:
            raise ValueError
    except ValueError:
        issue("metadata_fill", "Fill declaration does not match this dataset's approved sentinel.")
    issues.extend(identity_issues(metadata, manifest, checksum))
    counts = Counter(timestamps)
    missing = tuple(f"{month:%Y-%m}" for month in expected if month not in counts)
    duplicates = tuple(f"{month:%Y-%m}" for month in sorted(counts) if counts[month] > 1)
    unexpected = tuple(f"{month:%Y-%m}" for month in sorted(set(counts) - set(expected)))
    for code, periods in (
        ("missing_month", missing),
        ("duplicate_month", duplicates),
        ("unexpected_month", unexpected),
    ):
        for period in periods:
            issue(
                code,
                f"{code.replace('_', ' ')} {period}; no imputation or averaging.",
                period=period,
            )
    if observed_rows != len(expected):
        issue("row_count", f"Expected {len(expected)} rows; found {observed_rows}.")
    ordered = timestamps == sorted(timestamps)
    summary = ValidationSummary(
        valid=not issues,
        expected_observations=len(expected),
        observed_rows=observed_rows,
        valid_observations=len(observations),
        expected_start=manifest.start,
        expected_end=manifest.end,
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
    return VariableSource(
        tuple(sorted(observations, key=lambda point: point.time)),
        path.name,
        checksum,
        "".join(lines[:header_start]),
        tuple(entries),
        summary,
    )
