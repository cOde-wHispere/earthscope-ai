"""Explicit, finite JSON response contracts, also used by the importer CLI."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class ValidationIssue(Model):
    code: str
    message: str
    line: int | None = None
    period: str | None = None


class ValidationSummary(Model):
    valid: bool
    expected_observations: int
    observed_rows: int
    valid_observations: int
    expected_start: date
    expected_end: date
    missing_months: tuple[str, ...] = ()
    duplicate_months: tuple[str, ...] = ()
    unexpected_months: tuple[str, ...] = ()
    invalid_value_count: int = 0
    fill_value_count: int = 0
    input_was_sorted: bool = True
    issues: tuple[ValidationIssue, ...] = ()
    warnings: tuple[str, ...] = ()
    interpolated_observations: Literal[0] = 0


class MetadataEntry(Model):
    key: str
    value: str


class DatasetMetadata(Model):
    source_name: str
    source_sha256: str
    product: str = "MERRA-2 M2IMNXASM v5.12.4"
    variable: str = "T2M (2-meter air temperature)"
    region: str = "Unverified geographic support (no approved dataset identity applied)"
    frequency: Literal["monthly"] = "monthly"
    native_units: Literal["K"] = "K"
    units_basis: str = "NASA T2M product specification; CSV has no explicit units field"
    output_units: Literal["degC"] = "degC"
    conversion: Literal["C = K - 273.15"] = "C = K - 273.15"
    value_column: str
    fill_value: float
    raw_preamble: str
    source_metadata: tuple[MetadataEntry, ...]
    validation: ValidationSummary


class ErrorResponse(Model):
    code: str
    message: str
    validation: ValidationSummary | None = None


class HealthResponse(Model):
    status: Literal["ok", "degraded"]
    service: str = "earthscope-backend"
    dataset_status: Literal["ready", "missing", "invalid", "unavailable", "analysis_unavailable"]
    error: ErrorResponse | None = None


class MonthlyPoint(Model):
    time: date
    temperature_kelvin: float
    temperature_celsius: float
    climatology_celsius: float
    anomaly_celsius: float


class MonthlyResponse(Model):
    source_sha256: str
    units: Literal["degC"] = "degC"
    baseline_start: date
    baseline_end: date
    observations: tuple[MonthlyPoint, ...]


class AnnualPoint(Model):
    year: int
    mean_celsius: float
    months: Literal[12] = 12


class AnnualResponse(Model):
    source_sha256: str
    units: Literal["degC"] = "degC"
    method: str = "Arithmetic mean of 12 monthly means; months have equal weight"
    observations: tuple[AnnualPoint, ...]


class ClimatologyPoint(Model):
    month: int = Field(ge=1, le=12)
    mean_celsius: float
    observations: int


class ClimatologyResponse(Model):
    source_sha256: str
    units: Literal["degC"] = "degC"
    baseline_start: date
    baseline_end: date
    method: str = "Month-of-year arithmetic means over the full validated record"
    observations: tuple[ClimatologyPoint, ...]


class ConfidenceInterval(Model):
    lower: float
    upper: float
    level: Literal[0.95] = 0.95


class TrendStatistics(Model):
    slope_celsius_per_decade: float
    standard_error_celsius_per_decade: float
    confidence_interval_celsius_per_decade: ConfidenceInterval
    p_value: float = Field(ge=0, le=1)
    n_observations: int
    start: date
    end: date
    method: str = "OLS temperature ~ intercept + elapsed calendar months + 11 month indicators"
    seasonality: str = "Month fixed effects; January is the reference month"
    covariance: str = "HAC/Newey-West"
    hac_maxlags_months: int
    kernel: Literal["Bartlett"] = "Bartlett"
    small_sample_correction: bool = True
    inference: str = "Two-sided Student-t reference with n - 13 residual degrees of freedom"
    residual_degrees_of_freedom: int


class TrendInterpretation(Model):
    significant: bool
    significance_level: Literal[0.05] = 0.05
    conclusion: Literal[
        "statistically significant warming trend detected",
        "statistically significant cooling trend detected",
        "no statistically significant trend detected",
    ]
    causation: str = "This temporal association does not identify a cause."


class TrendResponse(Model):
    source_sha256: str
    observations: TrendStatistics
    interpretation: TrendInterpretation
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
