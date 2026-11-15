import { afterEach, describe, expect, it, vi } from "vitest";
import { loadCatalog, loadVariableDashboard } from "./variables";
import {
  catalogSchema,
  variableAnnualSchema,
  variableMetadataSchema,
  variableMonthlySchema,
  variables,
} from "./variableSchemas";
import { catalog, respond, variableFixtures } from "../test/fixtures";

afterEach(() => vi.unstubAllGlobals());
describe("v2 scientific contracts and identity binding", () => {
  it.each(variables)(
    "loads %s with exact values and only approved analysis requests",
    async (id) => {
      const fetch = vi.fn(respond());
      vi.stubGlobal("fetch", fetch);
      const discovered = await loadCatalog();
      const data = await loadVariableDashboard(
        discovered.datasets.find((item) => item.id === id)!,
      );
      const fixture = variableFixtures(id);
      expect(data.metadata).toEqual({
        status: "ready",
        data: fixture.metadata,
      });
      expect(data.monthly).toEqual({ status: "ready", data: fixture.monthly });
      expect(data.annual).toEqual({ status: "ready", data: fixture.annual });
      expect(data.temperature !== undefined).toBe(id === "T2M");
      expect(fetch).toHaveBeenCalledTimes(id === "T2M" ? 10 : 4);
      if (id !== "T2M")
        expect(
          fetch.mock.calls.every(([url]) => String(url).startsWith("/api/v2/")),
        ).toBe(true);
    },
  );
  it("rejects incomplete, duplicated, misrouted or unpinned catalogs", () => {
    const item = catalog.datasets[0];
    for (const patch of [
      { monthly_url: "https://example.org/data" },
      { expected_source_sha256: null },
      { dataset_id: null },
      { monthly_units: "hPa" },
    ]) {
      expect(
        catalogSchema.safeParse({
          datasets: [{ ...item, ...patch }, ...catalog.datasets.slice(1)],
        }).success,
      ).toBe(false);
    }
    expect(
      catalogSchema.safeParse({ datasets: catalog.datasets.slice(1) }).success,
    ).toBe(false);
    expect(
      catalogSchema.safeParse({ datasets: catalog.datasets.map(() => item) })
        .success,
    ).toBe(false);
  });
  it.each(["dataset_id", "variable", "source_sha256"])(
    "withholds a monthly response with a mismatched %s",
    async (field) => {
      const fixture = variableFixtures("QV2M");
      const replacement = {
        dataset_id: "other-snapshot",
        variable: "T2M",
        source_sha256: "b".repeat(64),
      }[field];
      vi.stubGlobal(
        "fetch",
        vi.fn(
          respond({
            "/v2/datasets/QV2M/timeseries/monthly": {
              ...fixture.monthly,
              [field]: replacement,
              ...(field === "variable" ? { units: "degC" } : {}),
            },
          }),
        ),
      );
      const data = await loadVariableDashboard(catalog.datasets[2]);
      expect(data.monthly).toMatchObject({
        status: "error",
        error: { code: "source_mismatch" },
      });
      expect(data.annual.status).toBe("ready");
    },
  );
  it("rejects metadata from another catalog identity and withholds every scientific output", async () => {
    const fixture = variableFixtures("T2M").metadata;
    vi.stubGlobal(
      "fetch",
      vi.fn(
        respond({
          "/v2/datasets/T2M/metadata": {
            ...fixture,
            dataset_id: "other",
            identity: { ...fixture.identity, dataset_id: "other" },
          },
        }),
      ),
    );
    const data = await loadVariableDashboard(catalog.datasets[0]);
    expect(data.metadata).toMatchObject({
      status: "error",
      error: { code: "source_mismatch" },
    });
    for (const result of [
      data.monthly,
      data.annual,
      data.temperature?.trend,
      data.temperature?.monthly,
      data.temperature?.climatology,
    ])
      expect(result).toMatchObject({
        status: "error",
        error: { code: "provenance_unavailable" },
      });
  });
  it("withholds legacy temperature analysis with a different checksum", async () => {
    const success = respond();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        const response = await success(url);
        const body = await response.json();
        return Response.json(
          url.startsWith("/api/v2/") || url.endsWith("/health")
            ? body
            : { ...body, source_sha256: "b".repeat(64) },
        );
      }),
    );
    const data = await loadVariableDashboard(catalog.datasets[0]);
    expect(data.monthly.status).toBe("ready");
    expect(data.temperature?.trend).toMatchObject({
      status: "error",
      error: { code: "source_mismatch" },
    });
  });
  it("checks source units, conversion and annual method across responses", async () => {
    const fixture = variableFixtures("PS");
    vi.stubGlobal(
      "fetch",
      vi.fn(
        respond({
          "/v2/datasets/PS/timeseries/monthly": {
            ...fixture.monthly,
            source_units: "Pa",
          },
          "/v2/datasets/PS/timeseries/annual": {
            ...fixture.annual,
            method: "Unexpected averaging",
          },
        }),
      ),
    );
    const data = await loadVariableDashboard(catalog.datasets[5]);
    expect(data.monthly).toMatchObject({
      status: "error",
      error: { code: "source_mismatch" },
    });
    expect(data.annual).toMatchObject({
      status: "error",
      error: { code: "source_mismatch" },
    });
  });
  it("validates finite values, units, complete years and nested identity", () => {
    const fixture = variableFixtures("PRECTOTCORR");
    expect(
      variableMonthlySchema.safeParse({
        ...fixture.monthly,
        observations: [{ ...fixture.monthly.observations[0], value: NaN }],
      }).success,
    ).toBe(false);
    expect(
      variableMonthlySchema.safeParse({ ...fixture.monthly, units: "mm/year" })
        .success,
    ).toBe(false);
    expect(
      variableAnnualSchema.safeParse({
        ...fixture.annual,
        observations: [{ ...fixture.annual.observations[0], months: 11 }],
      }).success,
    ).toBe(false);
    expect(
      variableAnnualSchema.safeParse({
        ...fixture.annual,
        aggregation: "equal_month_mean",
      }).success,
    ).toBe(false);
    expect(
      variableMetadataSchema.safeParse({
        ...fixture.metadata,
        identity: {
          ...fixture.metadata.identity,
          source_sha256: "b".repeat(64),
        },
      }).success,
    ).toBe(false);
  });
  it("does not request unavailable datasets", async () => {
    const fetch = vi.fn(respond());
    vi.stubGlobal("fetch", fetch);
    await expect(
      loadVariableDashboard({
        ...catalog.datasets[2],
        status: "missing",
        error: { code: "dataset_missing", message: "Source missing" },
      }),
    ).rejects.toMatchObject({ code: "dataset_missing" });
    expect(fetch).not.toHaveBeenCalled();
  });
  it("preserves empty observations and isolates a failed endpoint", async () => {
    const fixture = variableFixtures("QV2M");
    const success = respond({
      "/v2/datasets/QV2M/timeseries/monthly": {
        ...fixture.monthly,
        observations: [],
      },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) =>
        url.endsWith("QV2M/timeseries/annual")
          ? Promise.resolve(
              Response.json(
                { code: "dataset_unavailable", message: "Unavailable" },
                { status: 503 },
              ),
            )
          : success(url),
      ),
    );
    const data = await loadVariableDashboard(catalog.datasets[2]);
    expect(data.monthly).toMatchObject({
      status: "ready",
      data: { observations: [] },
    });
    expect(data.annual).toMatchObject({
      status: "error",
      error: { code: "dataset_unavailable", status: 503 },
    });
  });
});
