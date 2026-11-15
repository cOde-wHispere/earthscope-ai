// Synthetic contract fixtures for tests only. Never imported by production code.
import type {
  Annual,
  Climatology,
  Health,
  Metadata,
  Monthly,
  Trend,
} from "../api/schemas";
import {
  expectedAggregation,
  expectedUnits,
  variables,
} from "../api/variableSchemas";
import type {
  Catalog,
  Variable,
  VariableMetadata,
  VariableMonthly,
  VariableAnnual,
} from "../api/variableSchemas";

export const hash = "a".repeat(64);
export const metadata: Metadata = {
  source_name: "synthetic-test.csv",
  source_sha256: hash,
  product: "MERRA-2 M2IMNXASM v5.12.4",
  variable: "T2M (2-meter air temperature)",
  region: "The Gambia (synthetic test fixture)",
  frequency: "monthly",
  native_units: "K",
  units_basis: "Synthetic test units",
  output_units: "degC",
  conversion: "C = K - 273.15",
  value_column: "mean_M2IMNXASM_5_12_4_T2M",
  fill_value: 1e15,
  raw_preamble: "SYNTHETIC TEST DATA",
  source_metadata: [
    { key: "Title", value: "Synthetic fixture, not NASA observations" },
  ],
  validation: {
    valid: true,
    expected_observations: 24,
    observed_rows: 24,
    valid_observations: 24,
    expected_start: "1991-01-01",
    expected_end: "1992-12-01",
    missing_months: [],
    duplicate_months: [],
    unexpected_months: [],
    invalid_value_count: 0,
    fill_value_count: 0,
    input_was_sorted: true,
    issues: [],
    warnings: [],
    interpolated_observations: 0,
  },
};
export const monthly: Monthly = {
  source_sha256: hash,
  units: "degC",
  baseline_start: "1991-01-01",
  baseline_end: "1992-12-01",
  observations: Array.from({ length: 24 }, (_, i) => ({
    time: `${1991 + Math.floor(i / 12)}-${String((i % 12) + 1).padStart(2, "0")}-01`,
    temperature_kelvin: 299.15 + i / 10,
    temperature_celsius: 26 + i / 10,
    climatology_celsius: 27,
    anomaly_celsius: i / 10 - 1,
  })),
};
export const annual: Annual = {
  source_sha256: hash,
  units: "degC",
  method: "Arithmetic mean of 12 monthly means; months have equal weight",
  observations: [
    { year: 1991, mean_celsius: 26.55, months: 12 },
    { year: 1992, mean_celsius: 27.75, months: 12 },
  ],
};
export const climatology: Climatology = {
  source_sha256: hash,
  units: "degC",
  baseline_start: "1991-01-01",
  baseline_end: "1992-12-01",
  method: "Month-of-year arithmetic means over the full validated record",
  observations: Array.from({ length: 12 }, (_, i) => ({
    month: i + 1,
    mean_celsius: 27 + i / 10,
    observations: 2,
  })),
};
export const trend: Trend = {
  source_sha256: hash,
  observations: {
    slope_celsius_per_decade: -0.123456,
    standard_error_celsius_per_decade: 0.1,
    confidence_interval_celsius_per_decade: {
      lower: -0.3,
      upper: 0.05,
      level: 0.95,
    },
    p_value: 0.25,
    n_observations: 24,
    start: "1991-01-01",
    end: "1992-12-01",
    method:
      "OLS temperature ~ intercept + elapsed calendar months + 11 month indicators",
    seasonality: "Month fixed effects; January is the reference month",
    covariance: "HAC/Newey-West",
    hac_maxlags_months: 12,
    kernel: "Bartlett",
    small_sample_correction: true,
    inference:
      "Two-sided Student-t reference with n - 13 residual degrees of freedom",
    residual_degrees_of_freedom: 11,
  },
  interpretation: {
    significant: false,
    significance_level: 0.05,
    conclusion: "no statistically significant trend detected",
    causation: "This temporal association does not identify a cause.",
  },
  assumptions: ["Synthetic assumption"],
  limitations: ["Synthetic limitation"],
};
export const health: Health = {
  status: "ok",
  service: "earthscope-backend",
  dataset_status: "ready",
  error: null,
};
const labels = [
  "2-meter air temperature",
  "Bias-corrected total precipitation",
  "2-meter specific humidity",
  "10-meter eastward wind component",
  "10-meter northward wind component",
  "Surface pressure",
];
export const catalog: Catalog = {
  datasets: variables.map((id, index) => ({
    id,
    dataset_id: `synthetic-${id}`,
    label: labels[index],
    status: "ready",
    expected_source_sha256: hash,
    monthly_units: expectedUnits[id][0],
    annual_units: expectedUnits[id][1],
    metadata_url: `/v2/datasets/${id}/metadata`,
    monthly_url: `/v2/datasets/${id}/timeseries/monthly`,
    annual_url: `/v2/datasets/${id}/timeseries/annual`,
    statistical_inference: "Not provided by /v2",
    approved_legacy_trend_url: id === "T2M" ? "/trend" : null,
    error: null,
  })),
};
export function variableFixtures(id: Variable) {
  const item = catalog.datasets.find((value) => value.id === id)!;
  const exportedUnits = {
    T2M: "K",
    PRECTOTCORR: "kg m-2 s-1",
    QV2M: "kg/kg",
    U10M: "m/s",
    V10M: "m/s",
    PS: "hPa",
  }[id];
  const method =
    id === "T2M"
      ? annual.method
      : id === "PRECTOTCORR"
        ? "Sum of 12 monthly water-equivalent precipitation totals; no annual averaging"
        : "Sum(monthly mean * calendar days) / days in complete year";
  const conversion =
    id === "T2M" ? metadata.conversion : `Synthetic ${id} conversion`;
  const meta: VariableMetadata = {
    dataset_id: item.dataset_id!,
    variable: id,
    label: item.label,
    identity: {
      dataset_id: item.dataset_id!,
      filename: "synthetic-test.csv",
      provider: "Synthetic test fixture",
      collection: "M2IMNXASM",
      version: "5.12.4",
      variable: id,
      product_native_units: exportedUnits,
      exported_units: exportedUnits,
      units_basis: "Synthetic units",
      source_origin: "https://giovanni.gsfc.nasa.gov",
      source_path: "/giovanni/",
      service: "ArAvTs",
      shape_id: "synthetic-shape",
      selection_bbox: null,
      data_bbox: null,
      empty_url_fields: 0,
      region: "The Gambia (synthetic test fixture)",
      start: "1991-01-01",
      end: "1992-12-01",
      source_sha256: hash,
      fill_value: 1e15,
    },
    source_name: metadata.source_name,
    source_sha256: hash,
    frequency: "monthly",
    product_native_units: exportedUnits,
    exported_units: exportedUnits,
    monthly_units: item.monthly_units,
    annual_units: item.annual_units,
    units_basis: "Synthetic units",
    conversion,
    annual_aggregation: expectedAggregation(id),
    annual_method: method,
    value_column: `synthetic-${id}`,
    fill_value: 1e15,
    validation_screen: "Synthetic test screen",
    raw_preamble: metadata.raw_preamble,
    source_metadata: metadata.source_metadata,
    validation: metadata.validation,
    limitations: ["Synthetic fixture, not NASA observations"],
    statistical_inference: "Not provided by /v2",
  };
  const months: VariableMonthly = {
    dataset_id: item.dataset_id!,
    variable: id,
    source_sha256: hash,
    units: item.monthly_units,
    source_units: exportedUnits,
    conversion,
    observations: monthly.observations.map((p, index) => ({
      time: p.time,
      source_value: p.temperature_kelvin,
      value:
        id === "T2M"
          ? p.temperature_celsius
          : id === "U10M" || id === "V10M"
            ? (index % 3) - 1
            : index + 1,
      days_in_month: 31,
    })),
  };
  const years: VariableAnnual = {
    dataset_id: item.dataset_id!,
    variable: id,
    source_sha256: hash,
    units: item.annual_units,
    aggregation: expectedAggregation(id),
    method,
    observations: annual.observations.map((p) => ({
      year: p.year,
      value: p.mean_celsius,
      months: 12,
    })),
  };
  return { metadata: meta, monthly: months, annual: years };
}
const variableResponses = Object.fromEntries(
  variables.flatMap((id) => {
    const fixture = variableFixtures(id);
    return [
      [`/v2/datasets/${id}/metadata`, fixture.metadata],
      [`/v2/datasets/${id}/timeseries/monthly`, fixture.monthly],
      [`/v2/datasets/${id}/timeseries/annual`, fixture.annual],
    ];
  }),
);
export const responses: Record<string, unknown> = {
  ...variableResponses,
  "/v2/datasets": catalog,
  "/health": health,
  "/metadata": metadata,
  "/timeseries/monthly": monthly,
  "/timeseries/annual": annual,
  "/climatology": climatology,
  "/trend": trend,
};
export function respond(overrides: Record<string, unknown> = {}) {
  return async (input: string | URL | Request): Promise<Response> => {
    const path = String(input).replace(/^\/api/, "");
    return Response.json({ ...responses, ...overrides }[path]);
  };
}
