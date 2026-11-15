import { expect, test } from "@playwright/test";
import axe from "axe-core";
import { expectAxisLabelsToFit } from "./chartAssertions";
import {
  catalogSchema,
  displayUnits,
  variableAnnualSchema,
  variableMetadataSchema,
  variableMonthlySchema,
} from "../src/api/variableSchemas";
import { monthLabel, number } from "../src/lib/format";

const backend = "http://127.0.0.1:8000";
// All displayed numbers below come from the real verified local sources.
test("six live v2 contracts preserve identity, checksum, units and legacy temperature values", async ({
  request,
}) => {
  const catalog = catalogSchema.parse(
    await (await request.get(`${backend}/v2/datasets`)).json(),
  );
  for (const item of catalog.datasets) {
    expect(item.status).toBe("ready");
    const metadata = variableMetadataSchema.parse(
      await (await request.get(backend + item.metadata_url)).json(),
    );
    const monthly = variableMonthlySchema.parse(
      await (await request.get(backend + item.monthly_url)).json(),
    );
    const annual = variableAnnualSchema.parse(
      await (await request.get(backend + item.annual_url)).json(),
    );
    for (const value of [metadata, monthly, annual]) {
      expect(value.dataset_id).toBe(item.dataset_id);
      expect(value.variable).toBe(item.id);
      expect(value.source_sha256).toBe(item.expected_source_sha256);
    }
    expect(metadata.identity.source_sha256).toBe(item.expected_source_sha256);
    expect(monthly.units).toBe(metadata.monthly_units);
    expect(annual.units).toBe(metadata.annual_units);
    expect(monthly.source_units).toBe(metadata.exported_units);
    expect(monthly.conversion).toBe(metadata.conversion);
    expect(annual.aggregation).toBe(metadata.annual_aggregation);
    expect(annual.method).toBe(metadata.annual_method);
    expect(monthly.observations).toHaveLength(420);
    expect(annual.observations).toHaveLength(35);
    if (item.id === "T2M") {
      const legacyMonthly = await (
        await request.get(`${backend}/timeseries/monthly`)
      ).json();
      const legacyAnnual = await (
        await request.get(`${backend}/timeseries/annual`)
      ).json();
      expect(monthly.observations.map((p) => [p.time, p.value])).toEqual(
        legacyMonthly.observations.map(
          (p: { time: string; temperature_celsius: number }) => [
            p.time,
            p.temperature_celsius,
          ],
        ),
      );
      expect(annual.observations.map((p) => [p.year, p.value])).toEqual(
        legacyAnnual.observations.map(
          (p: { year: number; mean_celsius: number }) => [
            p.year,
            p.mean_celsius,
          ],
        ),
      );
    } else {
      expect(
        (await request.get(`${backend}/v2/datasets/${item.id}/trend`)).status(),
      ).toBe(404);
    }
  }
});

test("every variable renders real monthly and annual values with accessible units and controls", async ({
  page,
  request,
}, testInfo) => {
  test.setTimeout(240000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByText("Statistical interpretation", { exact: true }),
  ).toBeVisible();
  const catalog = catalogSchema.parse(
    await (await request.get(`${backend}/v2/datasets`)).json(),
  );
  await page.addScriptTag({ content: axe.source });
  for (const item of catalog.datasets) {
    await page.getByLabel("NASA Giovanni dataset").selectOption(item.id);
    const record = page.getByRole("region", {
      name: "The long view",
      exact: true,
    });
    // A real timeout fails this first-attempt check. Recovery is verified in a
    // separate test with a deliberately held metadata request.
    await expect(
      page.getByText(item.expected_source_sha256!, { exact: true }),
    ).toBeVisible();
    const monthly = variableMonthlySchema.parse(
      await (await request.get(backend + item.monthly_url)).json(),
    );
    const annual = variableAnnualSchema.parse(
      await (await request.get(backend + item.annual_url)).json(),
    );
    const title =
      item.id === "T2M"
        ? "Monthly air temperature"
        : `Monthly ${item.label.toLowerCase()}`;
    const slider = record.getByRole("slider", {
      name: `${title}: observation`,
      exact: true,
    });
    await slider.focus();
    await page.keyboard.press("Home");
    const first = monthly.observations[0];
    const signed = item.id === "U10M" || item.id === "V10M";
    const formatted = (value: number, digits = 2) =>
      `${signed && value > 0 ? "+" : ""}${number(value, digits)}`;
    await expect(slider).toHaveAttribute(
      "aria-valuetext",
      `${monthLabel(first.time)}, ${formatted(first.value)} ${monthly.units === "degC" ? "degrees Celsius" : monthly.units}`,
    );
    await expectAxisLabelsToFit(record);
    await page.keyboard.press("ArrowRight");
    await expect(slider).toHaveValue("1");
    await record.getByText("View data table").click();
    await expect(
      record
        .getByRole("row", { name: new RegExp(`^${monthLabel(first.time)}`) })
        .getByRole("cell", { name: formatted(first.value, 4), exact: true })
        .first(),
    ).toBeVisible();
    await expect(
      record.getByRole("columnheader", {
        name: `${item.id === "T2M" ? "Temperature" : item.label} (${displayUnits(monthly.units)})`,
        exact: true,
      }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Annual", exact: true }).click();
    await expect(
      record.getByText(annual.method + ".", { exact: false }),
    ).toBeVisible();
    await record.getByText("View data table").click();
    const firstYear = annual.observations[0];
    await expect(
      record
        .getByRole("row", { name: new RegExp(`^${firstYear.year} `) })
        .getByRole("cell", {
          name: formatted(firstYear.value, 4),
          exact: true,
        }),
    ).toBeVisible();
    await expect(
      record.getByRole("columnheader", {
        name: `${item.id === "T2M" ? "Temperature" : item.label} (${displayUnits(annual.units)})`,
        exact: true,
      }),
    ).toBeVisible();
    await expectAxisLabelsToFit(record);
    if (item.id !== "T2M") {
      await expect(
        page.getByRole("heading", { name: "Full-record trend" }),
      ).toHaveCount(0);
      await expect(page.getByRole("button", { name: "Anomalies" })).toHaveCount(
        0,
      );
      await expect(
        page.getByText(/confidence interval|p-value|significance threshold/i),
      ).toHaveCount(0);
    }
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    const violations = await page.evaluate(
      async () =>
        (
          await window.axe.run(document, {
            runOnly: {
              type: "tag",
              values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"],
            },
          })
        ).violations,
    );
    expect(violations, `${item.id} accessibility`).toEqual([]);
    await record.screenshot({
      path: testInfo.outputPath(`${item.id}-annual.png`),
    });
  }
  expect(errors).toEqual([]);
});

test("metadata timeout withholds output until an explicit reload recovers", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByText("Statistical interpretation", { exact: true }),
  ).toBeVisible();
  const metadataUrl = "**/api/v2/datasets/V10M/metadata";
  let metadataRequests = 0;
  let abortMetadata!: () => Promise<void>;
  await page.route(metadataUrl, (route) => {
    metadataRequests += 1;
    // Leave the response pending until the application's real timeout fires.
    abortMetadata = () => route.abort("timedout");
  });
  await page.getByLabel("NASA Giovanni dataset").selectOption("V10M");
  await expect(page.locator("#provenance .error-state code")).toHaveText(
    "timeout",
  );
  const record = page.getByRole("region", {
    name: "The long view",
    exact: true,
  });
  await expect(record.getByRole("img")).toHaveCount(0);
  await expect(page.getByRole("link", { name: /NASA product/ })).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Monthly record unavailable" }),
  ).toBeVisible();
  expect(metadataRequests).toBe(1);
  // Finish the held route before removing interception; unroute also resumes
  // pending routes in this Playwright version and must not handle it twice.
  await abortMetadata();
  await page.unroute(metadataUrl);
  await page.getByRole("button", { name: "Reload data", exact: true }).click();
  await expect(
    record.getByRole("img", {
      name: /^Monthly 10-meter northward wind component /,
    }),
  ).toBeVisible();
  await expect(page.locator("#provenance .error-state")).toHaveCount(0);
});

test("unavailable catalog entries are disabled and temperature failure leaves other variables usable", async ({
  page,
  request,
}) => {
  const catalog = catalogSchema.parse(
    await (await request.get(`${backend}/v2/datasets`)).json(),
  );
  await page.route("**/api/v2/datasets", async (route) => {
    await route.fulfill({
      json: {
        datasets: catalog.datasets.map((item) =>
          item.id === "T2M" || item.id === "PS"
            ? {
                ...item,
                status: "missing",
                error: {
                  code: "dataset_missing",
                  message: `${item.id} source unavailable for failure verification.`,
                },
              }
            : item,
        ),
      },
    });
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Dataset unavailable", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("option", { name: /PS.*missing/ }),
  ).toBeDisabled();
  await expect(
    page.getByText("4 of 6 datasets available. Selected: T2M."),
  ).toBeVisible();
  await page.unroute("**/api/v2/datasets");
  await page.getByLabel("NASA Giovanni dataset").selectOption("QV2M");
  await expect(
    page.getByRole("img", { name: /^Monthly 2-meter specific humidity / }),
  ).toBeVisible();
});

test("metadata identity mismatch withholds scientific output and reload recovers", async ({
  page,
  request,
}) => {
  const metadata = variableMetadataSchema.parse(
    await (await request.get(`${backend}/v2/datasets/PS/metadata`)).json(),
  );
  await page.goto("/");
  await expect(
    page.getByText("Statistical interpretation", { exact: true }),
  ).toBeVisible();
  await page.route("**/api/v2/datasets/PS/metadata", async (route) => {
    await route.fulfill({
      json: {
        ...metadata,
        dataset_id: "mismatched-review-snapshot",
        identity: {
          ...metadata.identity,
          dataset_id: "mismatched-review-snapshot",
        },
      },
    });
  });
  await page.getByLabel("NASA Giovanni dataset").selectOption("PS");
  await expect(
    page.getByRole("heading", { name: "Source metadata unavailable" }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", { name: /^Monthly surface pressure / }),
  ).toHaveCount(0);
  await expect(page.getByRole("link", { name: /NASA product/ })).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Monthly record unavailable" }),
  ).toBeVisible();
  await page.unroute("**/api/v2/datasets/PS/metadata");
  await page.getByRole("button", { name: "Reload data" }).click();
  await expect(
    page.getByRole("img", { name: /^Monthly surface pressure / }),
  ).toBeVisible();
  await page.getByLabel("NASA Giovanni dataset").selectOption("T2M");
  await page.getByLabel("NASA Giovanni dataset").selectOption("U10M");
  await page.getByLabel("NASA Giovanni dataset").selectOption("PS");
  await expect(
    page.getByRole("img", { name: /^Monthly surface pressure / }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Full-record trend" }),
  ).toHaveCount(0);
});
