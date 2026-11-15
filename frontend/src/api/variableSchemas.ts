import { z } from "zod";
import { errorSchema, validation } from "./schemas";

export const variables = [
  "T2M",
  "PRECTOTCORR",
  "QV2M",
  "U10M",
  "V10M",
  "PS",
] as const;
export const variableSchema = z.enum(variables);
export type Variable = z.infer<typeof variableSchema>;
const hash = z.string().regex(/^[a-f0-9]{64}$/);
const text = z.string().min(1);
const finite = z.number().finite();
const date = z.iso.date();
const units = z.enum(["degC", "mm/month", "mm/year", "g/kg", "m/s", "hPa"]);
const aggregation = z.enum([
  "equal_month_mean",
  "calendar_day_weighted_mean",
  "sum",
]);
export const expectedUnits: Record<
  Variable,
  readonly [z.infer<typeof units>, z.infer<typeof units>]
> = {
  T2M: ["degC", "degC"],
  PRECTOTCORR: ["mm/month", "mm/year"],
  QV2M: ["g/kg", "g/kg"],
  U10M: ["m/s", "m/s"],
  V10M: ["m/s", "m/s"],
  PS: ["hPa", "hPa"],
};
export const expectedAggregation = (id: Variable) =>
  id === "T2M"
    ? "equal_month_mean"
    : id === "PRECTOTCORR"
      ? "sum"
      : "calendar_day_weighted_mean";
export const displayUnits = (unit: string) => (unit === "degC" ? "°C" : unit);

const catalogItem = z
  .object({
    id: variableSchema,
    dataset_id: text.nullable(),
    label: text,
    status: z.enum(["ready", "missing", "invalid", "unavailable"]),
    expected_source_sha256: hash.nullable(),
    monthly_units: units,
    annual_units: units,
    metadata_url: text,
    monthly_url: text,
    annual_url: text,
    statistical_inference: z.literal("Not provided by /v2"),
    approved_legacy_trend_url: z.literal("/trend").nullable(),
    error: errorSchema.nullable(),
  })
  .refine((item) => {
    const root = `/v2/datasets/${item.id}`;
    return (
      item.monthly_units === expectedUnits[item.id][0] &&
      item.annual_units === expectedUnits[item.id][1] &&
      item.metadata_url === `${root}/metadata` &&
      item.monthly_url === `${root}/timeseries/monthly` &&
      item.annual_url === `${root}/timeseries/annual` &&
      item.approved_legacy_trend_url ===
        (item.id === "T2M" ? "/trend" : null) &&
      (item.status !== "ready" ||
        (item.dataset_id !== null &&
          item.expected_source_sha256 !== null &&
          item.error === null))
    );
  }, "Catalog identity, routes and units must agree");
export const catalogSchema = z
  .object({ datasets: z.array(catalogItem).length(6) })
  .refine(
    (catalog) => new Set(catalog.datasets.map((item) => item.id)).size === 6,
    "Expected six unique variables",
  );

const identity = z.object({
  dataset_id: text,
  filename: text,
  provider: text,
  collection: text,
  version: z.literal("5.12.4"),
  variable: variableSchema,
  product_native_units: text,
  exported_units: text,
  units_basis: text,
  source_origin: z.literal("https://giovanni.gsfc.nasa.gov"),
  source_path: z.literal("/giovanni/"),
  service: z.literal("ArAvTs"),
  shape_id: text,
  selection_bbox: z.tuple([finite, finite, finite, finite]).nullable(),
  data_bbox: z.null(),
  empty_url_fields: z.union([z.literal(0), z.literal(1)]),
  region: text,
  start: date,
  end: date,
  source_sha256: hash,
  fill_value: finite,
});
export const variableMetadataSchema = z
  .object({
    dataset_id: text,
    variable: variableSchema,
    label: text,
    identity,
    source_name: text,
    source_sha256: hash,
    frequency: z.literal("monthly"),
    product_native_units: text,
    exported_units: text,
    monthly_units: units,
    annual_units: units,
    units_basis: text,
    conversion: text,
    annual_aggregation: aggregation,
    annual_method: text,
    value_column: text,
    fill_value: finite,
    validation_screen: text,
    raw_preamble: z.string(),
    source_metadata: z.array(z.object({ key: z.string(), value: z.string() })),
    validation: validation.refine(
      (value) => value.valid,
      "Source validation must pass",
    ),
    limitations: z.array(text),
    statistical_inference: z.literal("Not provided by /v2"),
  })
  .refine(
    (value) =>
      value.dataset_id === value.identity.dataset_id &&
      value.variable === value.identity.variable &&
      value.source_sha256 === value.identity.source_sha256 &&
      value.monthly_units === expectedUnits[value.variable][0] &&
      value.annual_units === expectedUnits[value.variable][1] &&
      value.annual_aggregation === expectedAggregation(value.variable) &&
      value.exported_units === value.identity.exported_units &&
      value.product_native_units === value.identity.product_native_units &&
      value.validation.expected_start === value.identity.start &&
      value.validation.expected_end === value.identity.end,
    "Metadata identity and units must agree",
  );
const binding = {
  dataset_id: text,
  variable: variableSchema,
  source_sha256: hash,
  units,
};
export const variableMonthlySchema = z
  .object({
    ...binding,
    source_units: text,
    conversion: text,
    observations: z.array(
      z.object({
        time: date.refine(
          (value) => value.endsWith("-01"),
          "Expected month start",
        ),
        source_value: finite,
        value: finite,
        days_in_month: z.number().int().min(28).max(31),
      }),
    ),
  })
  .refine(
    (value) => value.units === expectedUnits[value.variable][0],
    "Monthly units must agree",
  );
export const variableAnnualSchema = z
  .object({
    ...binding,
    aggregation,
    method: text,
    observations: z.array(
      z.object({
        year: z.number().int(),
        value: finite,
        months: z.literal(12),
      }),
    ),
  })
  .refine(
    (value) =>
      value.units === expectedUnits[value.variable][1] &&
      value.aggregation === expectedAggregation(value.variable),
    "Annual units and aggregation must agree",
  );
export type Catalog = z.infer<typeof catalogSchema>;
export type CatalogItem = Catalog["datasets"][number];
export type VariableMetadata = z.infer<typeof variableMetadataSchema>;
export type VariableMonthly = z.infer<typeof variableMonthlySchema>;
export type VariableAnnual = z.infer<typeof variableAnnualSchema>;
