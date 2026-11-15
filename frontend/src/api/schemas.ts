import { z } from "zod";

// Mirrors backend/src/earthscope_backend/schemas.py. Parse every network response
// before it can enter a chart; TypeScript assertions alone cannot validate JSON.
const finite = z.number().finite();
const count = z.number().int().nonnegative();
const date = z.iso.date();
const hash = z.string().regex(/^[a-f0-9]{64}$/);
const units = z.literal("degC");
const issue = z.object({
  code: z.string(),
  message: z.string(),
  line: z.number().int().nullable().optional(),
  period: z.string().nullable().optional(),
});
export const validation = z.object({
  valid: z.boolean(),
  expected_observations: count,
  observed_rows: count,
  valid_observations: count,
  expected_start: date,
  expected_end: date,
  missing_months: z.array(z.string()),
  duplicate_months: z.array(z.string()),
  unexpected_months: z.array(z.string()),
  invalid_value_count: count,
  fill_value_count: count,
  input_was_sorted: z.boolean(),
  issues: z.array(issue),
  warnings: z.array(z.string()),
  interpolated_observations: z.literal(0),
});
export const errorSchema = z.object({
  code: z.string(),
  message: z.string(),
  validation: validation.nullable().optional(),
});
export const healthSchema = z.object({
  status: z.enum(["ok", "degraded"]),
  service: z.literal("earthscope-backend"),
  dataset_status: z.enum([
    "ready",
    "missing",
    "invalid",
    "unavailable",
    "analysis_unavailable",
  ]),
  error: errorSchema.nullable(),
});
export const metadataSchema = z.object({
  source_name: z.string(),
  source_sha256: hash,
  product: z.string(),
  variable: z.string(),
  region: z.string(),
  frequency: z.literal("monthly"),
  native_units: z.literal("K"),
  units_basis: z.string(),
  output_units: units,
  conversion: z.literal("C = K - 273.15"),
  value_column: z.string(),
  fill_value: finite,
  raw_preamble: z.string(),
  source_metadata: z.array(z.object({ key: z.string(), value: z.string() })),
  validation: validation.refine(
    (value) => value.valid,
    "Source validation must pass",
  ),
});
export const monthlySchema = z.object({
  source_sha256: hash,
  units,
  baseline_start: date,
  baseline_end: date,
  observations: z.array(
    z.object({
      time: date,
      temperature_kelvin: finite,
      temperature_celsius: finite,
      climatology_celsius: finite,
      anomaly_celsius: finite,
    }),
  ),
});
export const annualSchema = z.object({
  source_sha256: hash,
  units,
  method: z.string(),
  observations: z.array(
    z.object({
      year: z.number().int(),
      mean_celsius: finite,
      months: z.literal(12),
    }),
  ),
});
export const climatologySchema = z.object({
  source_sha256: hash,
  units,
  baseline_start: date,
  baseline_end: date,
  method: z.string(),
  observations: z.array(
    z.object({
      month: z.number().int().min(1).max(12),
      mean_celsius: finite,
      observations: count,
    }),
  ),
});
export const trendSchema = z.object({
  source_sha256: hash,
  observations: z.object({
    slope_celsius_per_decade: finite,
    standard_error_celsius_per_decade: finite.positive(),
    confidence_interval_celsius_per_decade: z
      .object({ lower: finite, upper: finite, level: z.literal(0.95) })
      .refine((value) => value.lower <= value.upper),
    p_value: finite.min(0).max(1),
    n_observations: count,
    start: date,
    end: date,
    method: z.string(),
    seasonality: z.string(),
    covariance: z.string(),
    hac_maxlags_months: count,
    kernel: z.literal("Bartlett"),
    small_sample_correction: z.boolean(),
    inference: z.string(),
    residual_degrees_of_freedom: count,
  }),
  interpretation: z.object({
    significant: z.boolean(),
    significance_level: z.literal(0.05),
    conclusion: z.enum([
      "statistically significant warming trend detected",
      "statistically significant cooling trend detected",
      "no statistically significant trend detected",
    ]),
    causation: z.string(),
  }),
  assumptions: z.array(z.string()),
  limitations: z.array(z.string()),
});
export type Metadata = z.infer<typeof metadataSchema>;
export type Monthly = z.infer<typeof monthlySchema>;
export type Annual = z.infer<typeof annualSchema>;
export type Climatology = z.infer<typeof climatologySchema>;
export type Trend = z.infer<typeof trendSchema>;
export type Health = z.infer<typeof healthSchema>;
