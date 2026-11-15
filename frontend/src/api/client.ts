import { z } from "zod";
import {
  annualSchema,
  climatologySchema,
  errorSchema,
  healthSchema,
  metadataSchema,
  monthlySchema,
  trendSchema,
} from "./schemas";
import type {
  Annual,
  Climatology,
  Health,
  Metadata,
  Monthly,
  Trend,
} from "./schemas";

export class ApiError extends Error {
  readonly code: string;
  readonly status?: number;
  constructor(code: string, message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

export type Resource<T> =
  { status: "ready"; data: T } | { status: "error"; error: ApiError };
export interface DashboardData {
  health: Resource<Health>;
  metadata: Resource<Metadata>;
  monthly: Resource<Monthly>;
  annual: Resource<Annual>;
  climatology: Resource<Climatology>;
  trend: Resource<Trend>;
}

export const API_BASE = (
  import.meta.env.VITE_API_BASE_URL?.trim() || "/api"
).replace(/\/+$/, "");

export async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  signal?: AbortSignal,
  timeoutMs = 12000,
): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  signal?.addEventListener("abort", abort, { once: true });
  if (signal?.aborted) controller.abort();
  const timer = setTimeout(abort, timeoutMs);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { Accept: "application/json" },
      signal: controller.signal,
      credentials: "omit",
      cache: "no-store",
    });
    let body: unknown;
    try {
      body = await response.json();
    } catch (error) {
      if (controller.signal.aborted) throw error;
      throw new ApiError(
        "invalid_response",
        "The service returned an unreadable response.",
        response.status,
      );
    }
    if (!response.ok) {
      const error = errorSchema.safeParse(body);
      throw new ApiError(
        error.success ? error.data.code : "http_error",
        error.success
          ? error.data.message
          : `The service returned HTTP ${response.status}.`,
        response.status,
      );
    }
    const parsed = schema.safeParse(body);
    if (!parsed.success)
      throw new ApiError(
        "invalid_response",
        "The response does not match the verified scientific API contract.",
      );
    return parsed.data;
  } catch (error) {
    if (signal?.aborted)
      throw new DOMException("Request cancelled", "AbortError");
    if (error instanceof ApiError) throw error;
    if (controller.signal.aborted)
      throw new ApiError(
        "timeout",
        "The service took too long to respond. Try again.",
      );
    throw new ApiError(
      "network_error",
      "The scientific service could not be reached. Check that the backend is running, then try again.",
    );
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", abort);
  }
}

export async function resource<T>(promise: Promise<T>): Promise<Resource<T>> {
  try {
    return { status: "ready", data: await promise };
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    return {
      status: "error",
      error:
        error instanceof ApiError
          ? error
          : new ApiError("unknown_error", "The data could not be loaded."),
    };
  }
}

function matchSource<T extends { source_sha256: string }>(
  value: Resource<T>,
  metadata: Resource<Metadata>,
): Resource<T> {
  if (value.status === "error") return value;
  if (metadata.status === "error")
    return {
      status: "error",
      error: new ApiError(
        "provenance_unavailable",
        "Verified source metadata is unavailable. Scientific output is withheld until provenance can be checked.",
      ),
    };
  if (value.data.source_sha256 !== metadata.data.source_sha256)
    return {
      status: "error",
      error: new ApiError(
        "source_mismatch",
        "Responses refer to different source snapshots. Reload to request a consistent record.",
      ),
    };
  return value;
}

export async function loadDashboard(
  signal?: AbortSignal,
): Promise<DashboardData> {
  const [health, metadata, monthly, annual, climatology, trend] =
    await Promise.all([
      resource(request("/health", healthSchema, signal)),
      resource(request("/metadata", metadataSchema, signal)),
      resource(request("/timeseries/monthly", monthlySchema, signal)),
      resource(request("/timeseries/annual", annualSchema, signal)),
      resource(request("/climatology", climatologySchema, signal)),
      resource(request("/trend", trendSchema, signal)),
    ]);
  return {
    health,
    metadata,
    monthly: matchSource(monthly, metadata),
    annual: matchSource(annual, metadata),
    climatology: matchSource(climatology, metadata),
    trend: matchSource(trend, metadata),
  };
}
