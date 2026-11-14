"""Independent, immutable per-dataset startup snapshots for descriptive /v2 output."""

import os
from calendar import monthrange
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from math import fsum
from pathlib import Path
from types import MappingProxyType

from earthscope_backend.config import EXPECTED_END, EXPECTED_START, REPOSITORY_ROOT
from earthscope_backend.identity import load_baseline_identity, validate_identity
from earthscope_backend.importer import (
    Dataset,
    DatasetUnavailableError,
    DatasetValidationError,
    month_range,
)
from earthscope_backend.multivariable_importer import SourcePoint, VariableSource, import_variable
from earthscope_backend.multivariable_schemas import (
    DatasetCatalog,
    DatasetCatalogItem,
    DatasetManifest,
    DescriptiveAnnualPoint,
    DescriptiveAnnualResponse,
    DescriptiveMonthlyPoint,
    DescriptiveMonthlyResponse,
    VariableMetadata,
)
from earthscope_backend.schemas import ErrorResponse, ValidationIssue, ValidationSummary
from earthscope_backend.variables import SPECS, VariableSpec

PRODUCT_SPECIFICATION = (
    "https://gmao.gsfc.nasa.gov/media/publications/zbly36ziNFDFbmYmvhQeVqPhUo/Bosilovich785.pdf"
)
LIMITATIONS = (
    "MERRA-2 is model/observation reanalysis, not a direct country-wide measurement record.",
    "Giovanni country masking, grid resolution and spatial weighting limit local interpretation.",
    "CSV units are not explicitly declared. Reviewed product/export unit assumptions are recorded.",
    "Selection bounds are not data grid bounds; absent export bounds remain unknown.",
    "Monthly area averages do not resolve daily extremes, events or local operational conditions.",
    "Descriptive summaries provide no trend inference, attribution or sector recommendations.",
    "Source retrieval time and spatial weights are not supplied by these CSV exports.",
)
ANNUAL_METHODS = {
    "equal_month_mean": "Arithmetic mean of 12 monthly means; months have equal weight",
    "calendar_day_weighted_mean": "Sum(monthly mean * calendar days) / days in complete year",
    "sum": "Sum of 12 monthly water-equivalent precipitation totals; no annual averaging",
}


def v2_data_directory() -> Path:
    configured = Path(os.environ.get("EARTHSCOPE_V2_DATA_DIR", "data/raw"))
    return configured if configured.is_absolute() else REPOSITORY_ROOT / configured


def manifest_failure(message: str) -> DatasetValidationError:
    return DatasetValidationError(
        ValidationSummary(
            valid=False,
            expected_observations=len(month_range(EXPECTED_START, EXPECTED_END)),
            observed_rows=0,
            valid_observations=0,
            expected_start=EXPECTED_START,
            expected_end=EXPECTED_END,
            issues=(ValidationIssue(code="manifest_invalid", message=message),),
        )
    )


def load_manifest(variable: str) -> DatasetManifest:
    """Only reviewed packaged manifests; no request, environment or CSV sidecar override."""
    spec = SPECS[variable]
    try:
        if variable == "T2M":
            baseline = load_baseline_identity()
            fields = baseline.model_dump(exclude={"native_units"})
            manifest = DatasetManifest(
                **fields,
                filename=spec.filename,
                product_native_units="K",
                exported_units="K",
                units_basis="NASA product specification ("
                + PRODUCT_SPECIFICATION
                + "); CSV has no explicit units field",
                fill_value=spec.fill_value,
            )
        else:
            resource = f"manifests/gambia_merra2_{variable.lower()}_1991_2025.json"
            raw = files("earthscope_backend").joinpath(resource).read_text(encoding="utf-8")
            manifest = DatasetManifest.model_validate_json(raw)
        if (
            manifest.variable != variable
            or manifest.filename != spec.filename
            or manifest.collection != spec.collection
            or manifest.fill_value != spec.fill_value
            or manifest.product_native_units != spec.product_native_units
            or manifest.exported_units != spec.exported_units
            or (manifest.start, manifest.end) != (EXPECTED_START, EXPECTED_END)
            or not manifest.units_basis.strip()
        ):
            raise ValueError("Manifest does not match the reviewed variable semantics/coverage.")
        return manifest
    except (OSError, ValueError) as exc:
        raise manifest_failure(
            f"Approved {variable} manifest is missing, malformed or inconsistent. "
            "Restore the reviewed backend package and restart."
        ) from exc


def temperature_source(dataset: Dataset) -> VariableSource:
    """Reuse exactly the legacy startup snapshot, checked against its production identity."""
    verified = validate_identity(dataset, load_baseline_identity())
    metadata = verified.metadata
    return VariableSource(
        tuple(SourcePoint(point.time, point.kelvin) for point in verified.observations),
        metadata.source_name,
        metadata.source_sha256,
        metadata.raw_preamble,
        metadata.source_metadata,
        metadata.validation,
    )


def descriptive_series(
    source: VariableSource, manifest: DatasetManifest
) -> tuple[DescriptiveMonthlyResponse, DescriptiveAnnualResponse]:
    spec = SPECS[manifest.variable]
    points = tuple(
        DescriptiveMonthlyPoint(
            time=point.time,
            source_value=point.value,
            value=spec.convert(point.value, point.time),
            days_in_month=monthrange(point.time.year, point.time.month)[1],
        )
        for point in source.observations
    )
    groups: dict[int, list[DescriptiveMonthlyPoint]] = defaultdict(list)
    for point in points:
        groups[point.time.year].append(point)
    annual = []
    for year, months in sorted(groups.items()):
        if len(months) != 12 or {point.time.month for point in months} != set(range(1, 13)):
            raise DatasetValidationError(
                source.validation.model_copy(
                    update={
                        "valid": False,
                        "issues": (
                            ValidationIssue(
                                code="annual_incomplete",
                                message=f"{year} requires all 12 distinct months.",
                            ),
                        ),
                    }
                )
            )
        if spec.annual_aggregation == "sum":
            value = fsum(point.value for point in months)
        elif spec.annual_aggregation == "equal_month_mean":
            value = fsum(point.value for point in months) / 12
        else:
            value = fsum(point.value * point.days_in_month for point in months) / sum(
                point.days_in_month for point in months
            )
        annual.append(DescriptiveAnnualPoint(year=year, value=value))
    return (
        DescriptiveMonthlyResponse(
            dataset_id=manifest.dataset_id,
            variable=manifest.variable,
            source_sha256=source.source_sha256,
            units=spec.monthly_units,
            source_units=spec.exported_units,
            conversion=spec.conversion,
            observations=points,
        ),
        DescriptiveAnnualResponse(
            dataset_id=manifest.dataset_id,
            variable=manifest.variable,
            source_sha256=source.source_sha256,
            units=spec.annual_units,
            aggregation=spec.annual_aggregation,
            method=ANNUAL_METHODS[spec.annual_aggregation],
            observations=tuple(annual),
        ),
    )


def variable_metadata(source: VariableSource, manifest: DatasetManifest) -> VariableMetadata:
    spec = SPECS[manifest.variable]
    return VariableMetadata(
        dataset_id=manifest.dataset_id,
        variable=manifest.variable,
        label=spec.label,
        identity=manifest,
        source_name=source.source_name,
        source_sha256=source.source_sha256,
        product_native_units=spec.product_native_units,
        exported_units=spec.exported_units,
        monthly_units=spec.monthly_units,
        annual_units=spec.annual_units,
        units_basis=manifest.units_basis,
        conversion=spec.conversion,
        annual_aggregation=spec.annual_aggregation,
        annual_method=ANNUAL_METHODS[spec.annual_aggregation],
        value_column=spec.value_column,
        fill_value=manifest.fill_value,
        validation_screen=f"Finite values in inclusive engineering screen "
        f"{spec.minimum}..{spec.maximum} {spec.exported_units}; not a climatological bound",
        raw_preamble=source.raw_preamble,
        source_metadata=source.source_metadata,
        validation=source.validation,
        limitations=(*LIMITATIONS, spec.limitation),
    )


@dataclass(frozen=True)
class RegistryEntry:
    catalog: DatasetCatalogItem
    metadata: VariableMetadata | None = None
    monthly: DescriptiveMonthlyResponse | None = None
    annual: DescriptiveAnnualResponse | None = None


@dataclass(frozen=True)
class DatasetRegistry:
    entries: Mapping[str, RegistryEntry]

    @property
    def catalog(self) -> DatasetCatalog:
        return DatasetCatalog(datasets=tuple(entry.catalog for entry in self.entries.values()))


def catalog_item(
    spec: VariableSpec, manifest: DatasetManifest | None, error: ErrorResponse | None
) -> DatasetCatalogItem:
    status = "ready"
    if error is not None:
        status = {"dataset_missing": "missing", "dataset_invalid": "invalid"}.get(
            error.code, "unavailable"
        )
    root = f"/v2/datasets/{spec.variable}"
    return DatasetCatalogItem(
        id=spec.variable,
        dataset_id=manifest.dataset_id if manifest else None,
        label=spec.label,
        status=status,
        expected_source_sha256=manifest.source_sha256 if manifest else None,
        monthly_units=spec.monthly_units,
        annual_units=spec.annual_units,
        metadata_url=f"{root}/metadata",
        monthly_url=f"{root}/timeseries/monthly",
        annual_url=f"{root}/timeseries/annual",
        approved_legacy_trend_url="/trend" if spec.variable == "T2M" else None,
        error=error,
    )


def load_registry(
    directory: Path, temperature: Dataset | None, temperature_error: ErrorResponse | None
) -> DatasetRegistry:
    entries: dict[str, RegistryEntry] = {}
    for variable, spec in SPECS.items():
        manifest = None
        try:
            manifest = load_manifest(variable)
            if variable == "T2M" and temperature is None:
                error = temperature_error or ErrorResponse(
                    code="dataset_unavailable", message="Approved T2M startup snapshot unavailable."
                )
                entries[variable] = RegistryEntry(catalog_item(spec, manifest, error))
                continue
            source = (
                temperature_source(temperature)
                if variable == "T2M"
                else import_variable(directory / manifest.filename, manifest)
            )
            monthly, annual = descriptive_series(source, manifest)
            entries[variable] = RegistryEntry(
                catalog_item(spec, manifest, None),
                variable_metadata(source, manifest),
                monthly,
                annual,
            )
        except DatasetUnavailableError as exc:
            error = ErrorResponse(code=exc.code, message=str(exc))
            entries[variable] = RegistryEntry(catalog_item(spec, manifest, error))
        except DatasetValidationError as exc:
            error = ErrorResponse(
                code="dataset_invalid",
                message=f"{variable} source or manifest validation failed. "
                "Restore the approved package and source; then restart.",
                validation=exc.summary,
            )
            entries[variable] = RegistryEntry(catalog_item(spec, manifest, error))
    return DatasetRegistry(MappingProxyType(entries))
