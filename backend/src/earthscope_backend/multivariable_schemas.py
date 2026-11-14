"""Additive /v2 contracts; the approved temperature schemas remain unchanged."""

from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from earthscope_backend.importer import month_range
from earthscope_backend.schemas import ErrorResponse, MetadataEntry, Model, ValidationSummary
from earthscope_backend.variables import Aggregation, Variable


class DatasetManifest(Model):
    dataset_id: str = Field(min_length=1)
    filename: str
    provider: str
    collection: str
    version: Literal["5.12.4"]
    variable: Variable
    product_native_units: str
    exported_units: str
    units_basis: str
    source_origin: Literal["https://giovanni.gsfc.nasa.gov"]
    source_path: Literal["/giovanni/"]
    service: Literal["ArAvTs"]
    shape_id: str = Field(min_length=1)
    selection_bbox: tuple[float, float, float, float] | None
    data_bbox: None = None
    empty_url_fields: Literal[0, 1] = 0
    region: str = Field(min_length=1)
    start: date
    end: date
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    fill_value: float

    @model_validator(mode="after")
    def ordered_months(self):
        month_range(self.start, self.end)
        return self


class VariableMetadata(Model):
    dataset_id: str
    variable: Variable
    label: str
    identity: DatasetManifest
    source_name: str
    source_sha256: str
    frequency: Literal["monthly"] = "monthly"
    product_native_units: str
    exported_units: str
    monthly_units: str
    annual_units: str
    units_basis: str
    conversion: str
    annual_aggregation: Aggregation
    annual_method: str
    value_column: str
    fill_value: float
    validation_screen: str
    raw_preamble: str
    source_metadata: tuple[MetadataEntry, ...]
    validation: ValidationSummary
    limitations: tuple[str, ...]
    statistical_inference: Literal["Not provided by /v2"] = "Not provided by /v2"


class DescriptiveMonthlyPoint(Model):
    time: date
    source_value: float
    value: float
    days_in_month: int = Field(ge=28, le=31)


class DescriptiveMonthlyResponse(Model):
    dataset_id: str
    variable: Variable
    source_sha256: str
    units: str
    source_units: str
    conversion: str
    observations: tuple[DescriptiveMonthlyPoint, ...]


class DescriptiveAnnualPoint(Model):
    year: int
    value: float
    months: Literal[12] = 12


class DescriptiveAnnualResponse(Model):
    dataset_id: str
    variable: Variable
    source_sha256: str
    units: str
    aggregation: Aggregation
    method: str
    observations: tuple[DescriptiveAnnualPoint, ...]


class DatasetCatalogItem(Model):
    id: Variable
    dataset_id: str | None
    label: str
    status: Literal["ready", "missing", "invalid", "unavailable"]
    expected_source_sha256: str | None
    monthly_units: str
    annual_units: str
    metadata_url: str
    monthly_url: str
    annual_url: str
    statistical_inference: Literal["Not provided by /v2"] = "Not provided by /v2"
    approved_legacy_trend_url: Literal["/trend"] | None = None
    error: ErrorResponse | None = None


class DatasetCatalog(Model):
    datasets: tuple[DatasetCatalogItem, ...]
