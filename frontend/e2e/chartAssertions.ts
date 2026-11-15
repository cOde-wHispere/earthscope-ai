import { expect, type Locator } from "@playwright/test";

export async function expectAxisLabelsToFit(record: Locator) {
  await expect(record.locator("svg .axis-label")).not.toHaveCount(0);
  const clippedLabels = await record
    .locator("svg .axis-label")
    .evaluateAll((labels) =>
      labels.flatMap((label) => {
        const text = label as SVGTextElement;
        const bounds = text.getBBox();
        const viewport = text.ownerSVGElement!.viewBox.baseVal;
        return bounds.x < viewport.x ||
          bounds.x + bounds.width > viewport.x + viewport.width
          ? [text.textContent]
          : [];
      }),
    );
  expect(
    clippedLabels,
    "Chart axis labels fit inside the SVG viewport",
  ).toEqual([]);
}
