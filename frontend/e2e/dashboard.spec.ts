import { expect, test } from "@playwright/test";
import axe from "axe-core";
import {
  monthLabel,
  monthName,
  number,
  pValue,
  signed,
} from "../src/lib/format";
import {
  annualSchema,
  climatologySchema,
  metadataSchema,
  monthlySchema,
  trendSchema,
} from "../src/api/schemas";

declare global {
  interface Window {
    axe: typeof axe;
  }
}

// These smoke tests require the approved local CSV and real unchanged FastAPI
// service. They fail on unavailable data; they never substitute test observations.
test("real API values, interactive views, accessible layout and keyboard controls", async ({
  page,
  request,
}, testInfo) => {
  const consoleErrors: string[] = [];
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  const metadata = metadataSchema.parse(
    await (await request.get("http://127.0.0.1:8000/metadata")).json(),
  );
  const trend = trendSchema.parse(
    await (await request.get("http://127.0.0.1:8000/trend")).json(),
  );
  const annual = annualSchema.parse(
    await (await request.get("http://127.0.0.1:8000/timeseries/annual")).json(),
  );
  const monthly = monthlySchema.parse(
    await (
      await request.get("http://127.0.0.1:8000/timeseries/monthly")
    ).json(),
  );
  const climatology = climatologySchema.parse(
    await (await request.get("http://127.0.0.1:8000/climatology")).json(),
  );
  // Hold discovery to verify loading, then let data requests reach FastAPI
  // directly. Routing the entire request group adds unnecessary browser IPC.
  let releaseRequests!: () => void;
  const requestsHeld = new Promise<void>((resolve) => {
    releaseRequests = resolve;
  });
  await page.route("http://127.0.0.1:5173/api/v2/datasets", async (route) => {
    await requestsHeld;
    await route.continue();
  });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(
    page.getByRole("heading", { name: "Loading the scientific record" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Loading", exact: true }),
  ).toBeDisabled();
  releaseRequests();
  await expect(
    page.getByText(`${trend.interpretation.conclusion}.`, { exact: true }),
  ).toBeVisible();
  await expect(
    page
      .locator(".stat-card")
      .first()
      .getByText(signed(trend.observations.slope_celsius_per_decade)),
  ).toBeVisible();
  await expect(
    page.getByText(pValue(trend.observations.p_value), { exact: true }),
  ).toBeVisible();
  const interval = trend.observations.confidence_interval_celsius_per_decade;
  await expect(
    page.getByText(`${signed(interval.lower)} to ${signed(interval.upper)}`, {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByText(`${number(interval.level * 100, 0)}% confidence interval`, {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByText(metadata.source_sha256, { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", { name: /^Monthly air temperature / }),
  ).toBeVisible();
  const slider = page.getByRole("slider", {
    name: "Monthly air temperature: observation",
    exact: true,
  });
  await slider.focus();
  await page.keyboard.press("ArrowLeft");
  await expect(slider).toHaveValue(String(monthly.observations.length - 2));
  const selectedMonth = monthly.observations.at(-2)!;
  await expect(slider).toHaveAttribute(
    "aria-valuetext",
    `${monthLabel(selectedMonth.time)}, ${number(selectedMonth.temperature_celsius)} degrees Celsius`,
  );
  await page.getByRole("button", { name: "Annual", exact: true }).click();
  await expect(
    page.getByRole("img", { name: /^Annual air temperature / }),
  ).toBeVisible();
  const record = page.getByRole("region", {
    name: "The long view",
    exact: true,
  });
  await record.getByText("View data table").click();
  await expect(
    record.getByRole("rowheader", {
      name: String(annual.observations[0].year),
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    record
      .getByRole("cell", {
        name: number(annual.observations[0].mean_celsius, 4),
        exact: true,
      })
      .first(),
  ).toBeVisible();
  await page
    .getByRole("combobox", { name: "Chart start year" })
    .selectOption(String(annual.observations.at(-1)!.year));
  await record.getByText("View data table").click();
  await expect(
    record.getByRole("rowheader", {
      name: String(annual.observations[0].year),
      exact: true,
    }),
  ).toHaveCount(0);
  await expect(
    page.getByText(`${trend.observations.n_observations} monthly observations`),
  ).toBeVisible();
  const anomalySlider = page.getByRole("slider", {
    name: "Monthly temperature anomalies: observation",
    exact: true,
  });
  await anomalySlider.focus();
  await page.keyboard.press("Home");
  await expect(anomalySlider).toHaveAttribute(
    "aria-valuetext",
    `${monthLabel(monthly.observations[0].time)}, ${number(monthly.observations[0].anomaly_celsius)} degrees Celsius`,
  );
  await page.getByRole("button", { name: "Climatology", exact: true }).click();
  await expect(
    page.getByRole("img", { name: /^Monthly climatology / }),
  ).toBeVisible();
  const climatologySlider = page.getByRole("slider", {
    name: "Monthly climatology: observation",
    exact: true,
  });
  await climatologySlider.focus();
  await page.keyboard.press("Home");
  const firstMonth = climatology.observations[0];
  await expect(climatologySlider).toHaveAttribute(
    "aria-valuetext",
    `${monthName(firstMonth.month)} · ${firstMonth.observations} observations, ${number(firstMonth.mean_celsius)} degrees Celsius`,
  );
  await expect(
    page.getByText(metadata.variable, { exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Methodology", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: "Methodology & limitations",
      exact: true,
    }),
  ).toBeInViewport();
  await page
    .getByText("Inspect the backend statistical specification", { exact: true })
    .click();
  await expect(
    page.getByText(trend.observations.method, { exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Applications", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Earth intelligence across sectors" }),
  ).toBeInViewport();
  expect(await page.locator(".planned-label").count()).toBe(6);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.addScriptTag({ content: axe.source });
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
  expect(violations).toEqual([]);
  expect(consoleErrors).toEqual([]);
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await page.screenshot({
    path: testInfo.outputPath("dashboard.png"),
    fullPage: true,
  });
  await page.screenshot({
    path: testInfo.outputPath("dashboard-overview.png"),
  });
});

test("trend failure preserves descriptive output and retry restores the analysis", async ({
  page,
}) => {
  await page.route("**/api/trend", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        code: "analysis_unavailable",
        message:
          "Analysis temporarily unavailable for browser failure verification.",
      }),
    }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Trend analysis unavailable" }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", { name: /^Monthly air temperature / }),
  ).toBeVisible();
  await page.unroute("**/api/trend");
  await page.getByRole("button", { name: "Reload data" }).click();
  await expect(
    page.getByText("Statistical interpretation", { exact: true }),
  ).toBeVisible();
});

test("narrow layout and missing source show usable errors without scientific charts", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await page.route("http://127.0.0.1:5173/api/**", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        code: "dataset_missing",
        message: "The approved source file is unavailable.",
      }),
    }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Dataset availability unavailable" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Reload data" })).toBeEnabled();
  await expect(
    page.getByRole("img", { name: /^Monthly air temperature / }),
  ).toHaveCount(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
