"""Approved dataset identities, independent of the generic Giovanni CSV parser."""

from dataclasses import replace
from datetime import date
from importlib.resources import files
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import Field, model_validator

from earthscope_backend.config import EXPECTED_END, EXPECTED_START
from earthscope_backend.importer import (
    Dataset,
    DatasetValidationError,
    import_giovanni,
    month_range,
)
from earthscope_backend.schemas import Model, ValidationIssue, ValidationSummary

BASELINE_MANIFEST = "manifests/gambia_merra2_1991_2025.json"


class DatasetIdentity(Model):
    """Trusted, reviewed configuration; never derived from or supplied by the CSV/client."""

    dataset_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    collection: str = Field(min_length=1)
    version: str = Field(min_length=1)
    variable: str = Field(min_length=1)
    native_units: Literal["K"]
    source_origin: str
    source_path: str
    service: str
    shape_id: str
    selection_bbox: tuple[float, float, float, float]
    region: str = Field(min_length=1)
    start: date
    end: date
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @property
    def data_id(self) -> str:
        return f"{self.collection}_{self.version.replace('.', '_')}_{self.variable}"

    @model_validator(mode="after")
    def valid_coverage(self):
        month_range(self.start, self.end)
        return self


def load_baseline_identity() -> DatasetIdentity:
    """Read the manifest shipped with the backend, not an untrusted CSV sidecar."""
    try:
        raw = files("earthscope_backend").joinpath(BASELINE_MANIFEST).read_text(encoding="utf-8")
        return DatasetIdentity.model_validate_json(raw)
    except (OSError, ValueError) as exc:
        raise DatasetValidationError(
            ValidationSummary(
                valid=False,
                expected_observations=len(month_range(EXPECTED_START, EXPECTED_END)),
                observed_rows=0,
                valid_observations=0,
                expected_start=EXPECTED_START,
                expected_end=EXPECTED_END,
                issues=(
                    ValidationIssue(
                        code="manifest_invalid",
                        message="Approved baseline manifest is missing or malformed. Restore the "
                        "reviewed backend package, including its manifest, and restart.",
                    ),
                ),
            )
        ) from exc


def validate_identity(dataset: Dataset, identity: DatasetIdentity) -> Dataset:
    """Bind parsed measurements to one explicitly approved scientific identity."""
    issues: list[ValidationIssue] = []

    def issue(code: str, message: str):
        issues.append(ValidationIssue(code=code, message=message))

    metadata = {
        entry.key.strip().removesuffix(":"): entry.value.strip()
        for entry in dataset.metadata.source_metadata
    }
    url = metadata.get("URL to Reproduce Results", "")
    params: dict[str, list[str]] = {}
    try:
        parsed = urlsplit(url)
        if (
            f"{parsed.scheme}://{parsed.netloc}" != identity.source_origin
            or parsed.path != identity.source_path
            or parsed.query
            or any(char.isspace() or ord(char) < 32 for char in url)
        ):
            raise ValueError
        params = parse_qs(parsed.fragment, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        issue(
            "identity_source",
            "Giovanni reproduction URL is missing or has an unapproved "
            "origin, path or parameter location. Restore the approved source export.",
        )

    def parameter(key: str) -> str | None:
        values = params.get(key, [])
        return values[0] if len(values) == 1 else None

    for key, expected, code in (
        ("service", identity.service, "identity_service"),
        ("shape", identity.shape_id, "identity_shape"),
    ):
        if parameter(key) != expected:
            issue(
                code,
                f"Giovanni '{key}' must occur once and equal {expected!r} "
                f"for approved identity {identity.dataset_id!r}.",
            )
    data_id = parameter("data")
    prefix = f"{identity.collection}_{identity.version.replace('.', '_')}_"
    if data_id is None or not data_id.startswith(prefix):
        issue(
            "identity_collection",
            f"Giovanni collection/version must be "
            f"{identity.collection} v{identity.version}; expected data={identity.data_id}.",
        )
    if data_id is None or data_id.rsplit("_", 1)[-1] != identity.variable:
        issue("identity_variable", f"Giovanni variable must be {identity.variable!r}.")
    if data_id != identity.data_id:
        issue("identity_data", f"Giovanni 'data' must occur once and equal {identity.data_id!r}.")
    if dataset.metadata.value_column != f"mean_{identity.data_id}":
        issue(
            "identity_column", "CSV value column does not match the approved collection/variable."
        )
    for label, value in (
        ("URL bbox", parameter("bbox")),
        ("User Bounding Box", metadata.get("User Bounding Box")),
    ):
        try:
            bbox = tuple(float(part) for part in (value or "").split(","))
            if bbox != identity.selection_bbox:
                raise ValueError
        except ValueError:
            issue(
                "identity_bbox",
                f"{label} must match the approved selection bounds "
                f"{identity.selection_bbox}; do not substitute a different spatial support.",
            )
    summary = dataset.metadata.validation
    if (summary.expected_start, summary.expected_end) != (identity.start, identity.end):
        issue("identity_period", "Parsed coverage does not match the approved identity period.")
    if dataset.metadata.source_sha256 != identity.source_sha256:
        issue(
            "identity_sha256",
            f"Source SHA-256 does not match approved identity "
            f"{identity.dataset_id!r}. Expected {identity.source_sha256}; "
            f"observed {dataset.metadata.source_sha256}. Restore the approved CSV; "
            "new snapshots require a separately reviewed identity.",
        )
    if issues:
        raise DatasetValidationError(
            summary.model_copy(
                update={
                    "valid": False,
                    "issues": (*summary.issues, *issues),
                }
            )
        )
    return replace(
        dataset, metadata=dataset.metadata.model_copy(update={"region": identity.region})
    )


def load_verified_dataset(path: Path, identity: DatasetIdentity) -> Dataset:
    """New approved snapshots can use separate identities without relaxing the baseline."""
    dataset = import_giovanni(path, expected_start=identity.start, expected_end=identity.end)
    return validate_identity(dataset, identity)
