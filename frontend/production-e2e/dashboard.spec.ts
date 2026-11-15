import { expect, test } from "@playwright/test";
import { catalogSchema } from "../src/api/variableSchemas";
import { expectAxisLabelsToFit } from "../e2e/chartAssertions";

test("built static application loads all six real datasets and preserves temperature analysis", async ({
  page,
  request,
}) => {
  const response = await request.get("/");
  expect(response.ok()).toBe(true);
  const html = await response.text();
  expect(html).toMatch(/\/assets\/index-[\w-]+\.js/);
  expect(html).not.toContain("/src/main.tsx");
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const catalog = catalogSchema.parse(
    await (await request.get("/api/v2/datasets")).json(),
  );
  await page.goto("/");
  for (const item of catalog.datasets) {
    expect(item.status).toBe("ready");
    await expect(page.getByLabel("NASA Giovanni dataset")).toBeEnabled();
    await page.getByLabel("NASA Giovanni dataset").selectOption(item.id);
    await expect(
      page.getByText(item.expected_source_sha256!, { exact: true }),
    ).toBeVisible();
    await expect(
      page
        .getByRole("region", { name: "The long view", exact: true })
        .getByRole("img"),
    ).toBeVisible();
    const record = page.getByRole("region", {
      name: "The long view",
      exact: true,
    });
    await expectAxisLabelsToFit(record);
    await page.getByRole("button", { name: "Annual", exact: true }).click();
    await expect(record.getByRole("img", { name: /^Annual / })).toBeVisible();
    await expectAxisLabelsToFit(record);
    if (item.id !== "T2M")
      await expect(
        page.getByRole("heading", { name: "Full-record trend" }),
      ).toHaveCount(0);
  }
  await page.getByLabel("NASA Giovanni dataset").selectOption("T2M");
  await expect(
    page.getByText("Statistical interpretation", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Anomalies", exact: true }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
