import { afterEach, describe, expect, it, vi } from "vitest";
import { loadDashboard, request } from "./client";
import { monthlySchema, trendSchema } from "./schemas";
import { hash, metadata, monthly, respond, trend } from "../test/fixtures";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});
describe("read-only typed scientific client", () => {
  it("loads all six endpoints without modifying scientific results", async () => {
    const fetch = vi.fn<typeof globalThis.fetch>(respond());
    vi.stubGlobal("fetch", fetch);
    const data = await loadDashboard();
    expect(fetch).toHaveBeenCalledTimes(6);
    expect(data.trend).toEqual({ status: "ready", data: trend });
    expect(data.monthly).toEqual({ status: "ready", data: monthly });
    expect(
      fetch.mock.calls.every(
        ([, options]) =>
          (options as RequestInit | undefined)?.credentials === "omit",
      ),
    ).toBe(true);
  });
  it("rejects malformed or nonfinite scientific values", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({
          ...trend,
          observations: {
            ...trend.observations,
            slope_celsius_per_decade: "0.5",
          },
        }),
      ),
    );
    await expect(request("/trend", trendSchema)).rejects.toMatchObject({
      code: "invalid_response",
    });
    expect(
      trendSchema.safeParse({
        ...trend,
        observations: { ...trend.observations, p_value: Infinity },
      }).success,
    ).toBe(false);
  });
  it("withholds mismatched snapshots while retaining matched endpoints", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(respond({ "/trend": { ...trend, source_sha256: "b".repeat(64) } })),
    );
    const data = await loadDashboard();
    expect(data.trend).toMatchObject({
      status: "error",
      error: { code: "source_mismatch" },
    });
    expect(data.monthly.status).toBe("ready");
  });
  it("withholds scientific outputs when source validation fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        respond({
          "/metadata": {
            ...metadata,
            validation: { ...metadata.validation, valid: false },
          },
        }),
      ),
    );
    const data = await loadDashboard();
    expect(data.metadata.status).toBe("error");
    expect(data.annual).toMatchObject({
      status: "error",
      error: { code: "provenance_unavailable" },
    });
  });
  it("preserves structured 503 errors and descriptive data for trend-only failures", async () => {
    const success = respond();
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) =>
        input.endsWith("/trend")
          ? Promise.resolve(
              Response.json(
                {
                  code: "analysis_unavailable",
                  message: "Uncertainty is not estimable.",
                },
                { status: 503 },
              ),
            )
          : success(input),
      ),
    );
    const data = await loadDashboard();
    expect(data.trend).toMatchObject({
      status: "error",
      error: { code: "analysis_unavailable", status: 503 },
    });
    expect(data.annual.status).toBe("ready");
  });
  it("handles network failure and HTML fallback responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );
    await expect(request("/trend", trendSchema)).rejects.toMatchObject({
      code: "network_error",
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("<html>SPA fallback</html>")),
    );
    await expect(request("/trend", trendSchema)).rejects.toMatchObject({
      code: "invalid_response",
    });
  });
  it("returns a timeout and supports request cancellation", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url: string, init: RequestInit) =>
          new Promise((_resolve, reject) =>
            init.signal?.addEventListener("abort", () =>
              reject(new DOMException("Aborted", "AbortError")),
            ),
          ),
      ),
    );
    const pending = expect(
      request("/trend", trendSchema, undefined, 50),
    ).rejects.toMatchObject({ code: "timeout" });
    await vi.advanceTimersByTimeAsync(51);
    await pending;
    const controller = new AbortController();
    const cancelled = expect(
      request("/trend", trendSchema, controller.signal),
    ).rejects.toMatchObject({ name: "AbortError" });
    controller.abort();
    await cancelled;
  });
  it("accepts empty arrays without substituting observations", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({ ...monthly, source_sha256: hash, observations: [] }),
      ),
    );
    expect(
      (await request("/timeseries/monthly", monthlySchema)).observations,
    ).toEqual([]);
  });
});
