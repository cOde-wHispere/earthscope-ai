import { ApiError, loadDashboard, request, resource } from "./client";
import type { DashboardData, Resource } from "./client";
import {
  catalogSchema,
  variableMetadataSchema,
  variableMonthlySchema,
  variableAnnualSchema,
} from "./variableSchemas";
import type {
  CatalogItem,
  VariableMetadata,
  VariableMonthly,
  VariableAnnual,
} from "./variableSchemas";

export interface VariableDashboard {
  item: CatalogItem;
  metadata: Resource<VariableMetadata>;
  monthly: Resource<VariableMonthly>;
  annual: Resource<VariableAnnual>;
  temperature?: DashboardData;
}
export const loadCatalog = (signal?: AbortSignal) =>
  request("/v2/datasets", catalogSchema, signal);

function failure<T>(code: string, message: string): Resource<T> {
  return { status: "error", error: new ApiError(code, message) };
}
function bind<
  T extends { source_sha256: string; dataset_id: string; variable: string },
>(value: Resource<T>, item: CatalogItem): Resource<T> {
  if (value.status === "error") return value;
  return value.data.source_sha256 === item.expected_source_sha256 &&
    value.data.dataset_id === item.dataset_id &&
    value.data.variable === item.id
    ? value
    : failure(
        "source_mismatch",
        "Dataset identity or SHA-256 differs from the selected catalog snapshot. Reload to request a consistent record.",
      );
}
function bindSeries<
  T extends { source_sha256: string; dataset_id: string; variable: string },
>(
  value: Resource<T>,
  metadata: Resource<VariableMetadata>,
  item: CatalogItem,
): Resource<T> {
  if (metadata.status === "error")
    return failure(
      "provenance_unavailable",
      "Verified source metadata is unavailable. Scientific output is withheld until provenance can be checked.",
    );
  return bind(value, item);
}
function bindLegacy<T extends { source_sha256: string }>(
  value: Resource<T>,
  metadata: Resource<VariableMetadata>,
  item: CatalogItem,
): Resource<T> {
  if (metadata.status === "error")
    return failure(
      "provenance_unavailable",
      "Verified temperature provenance is unavailable.",
    );
  if (value.status === "error") return value;
  return value.data.source_sha256 === item.expected_source_sha256
    ? value
    : failure(
        "source_mismatch",
        "The approved temperature analysis refers to a different source snapshot.",
      );
}

export async function loadVariableDashboard(
  item: CatalogItem,
  signal?: AbortSignal,
): Promise<VariableDashboard> {
  if (item.status !== "ready")
    throw new ApiError(
      item.error?.code || "dataset_unavailable",
      item.error?.message ||
        `${item.id} is ${item.status}. Restore the approved backend source and reload.`,
    );
  // Catalog URLs are validated as exact local v2 routes. Never follow arbitrary URLs.
  const [rawMetadata, rawMonthly, rawAnnual, legacy] = await Promise.all([
    resource(request(item.metadata_url, variableMetadataSchema, signal)),
    resource(request(item.monthly_url, variableMonthlySchema, signal)),
    resource(request(item.annual_url, variableAnnualSchema, signal)),
    item.id === "T2M" ? loadDashboard(signal) : Promise.resolve(undefined),
  ]);
  const metadata = bind(rawMetadata, item);
  let monthly = bindSeries(rawMonthly, metadata, item);
  let annual = bindSeries(rawAnnual, metadata, item);
  if (metadata.status === "ready") {
    if (
      monthly.status === "ready" &&
      (monthly.data.source_units !== metadata.data.exported_units ||
        monthly.data.conversion !== metadata.data.conversion)
    )
      monthly = failure(
        "source_mismatch",
        "Monthly source units or conversion differ from the verified metadata.",
      );
    if (
      annual.status === "ready" &&
      annual.data.method !== metadata.data.annual_method
    )
      annual = failure(
        "source_mismatch",
        "Annual aggregation method differs from the verified metadata.",
      );
  }
  const temperature = legacy && {
    health: legacy.health,
    metadata: bindLegacy(legacy.metadata, metadata, item),
    monthly: bindLegacy(legacy.monthly, metadata, item),
    annual: bindLegacy(legacy.annual, metadata, item),
    climatology: bindLegacy(legacy.climatology, metadata, item),
    trend: bindLegacy(legacy.trend, metadata, item),
  };
  return { item, metadata, monthly, annual, temperature };
}
