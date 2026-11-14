import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import {
  annual,
  climatology,
  health,
  monthly,
  respond,
  trend,
} from "./test/fixtures";

afterEach(() => {
  vi.unstubAllGlobals();
  window.location.hash = "";
});
describe("scientific dashboard", () => {
  it("shows loading before the service responds", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise(() => {})),
    );
    render(<App />);
    expect(
      screen.getByRole("heading", { name: "Loading the scientific record" }),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Loading" })).toBeDisabled();
    expect(
      screen.getByRole("heading", {
        name: "Earth intelligence across sectors",
      }),
    ).toBeVisible();
  });
  it("renders backend values and a nonsignificant interpretation without assuming warming", async () => {
    vi.stubGlobal("fetch", vi.fn(respond()));
    render(<App />);
    expect(
      await screen.findByText("no statistically significant trend detected."),
    ).toBeVisible();
    expect(screen.getByText("-0.123")).toBeVisible();
    expect(screen.getByText("-0.300 to +0.050")).toBeVisible();
    expect(screen.getByText("0.2500")).toBeVisible();
    expect(screen.getByText("24 monthly observations")).toBeVisible();
    expect(screen.getByText("Unknown in this export")).toBeVisible();
    expect(screen.getAllByText("Planned")).toHaveLength(6);
  });
  it("switches frequency, filters the chart, and explores baseline without changing the trend", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn(respond()));
    render(<App />);
    await screen.findByRole("img", { name: /^Monthly air temperature\b/ });
    await user.click(screen.getByRole("button", { name: "Annual" }));
    expect(
      screen.getByRole("img", { name: /Annual air temperature/ }),
    ).toBeVisible();
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Chart start year" }),
      "1992",
    );
    const record = screen.getByRole("region", { name: "The long view" });
    await user.click(within(record).getByText(/View data table/));
    expect(within(record).getByRole("cell", { name: "27.7500" })).toBeVisible();
    expect(
      within(record).queryByRole("rowheader", { name: "1991" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("24 monthly observations")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Climatology" }));
    expect(
      screen.getByRole("img", { name: /Monthly climatology/ }),
    ).toBeVisible();
    const slider = screen.getByRole("slider", {
      name: "Monthly climatology: observation",
    });
    fireEvent.change(slider, { target: { value: "0" } });
    expect(slider).toHaveValue("0");
    expect(screen.getAllByText("Jan · 2 observations")[0]).toBeVisible();
    expect(
      screen.getByText("no statistically significant trend detected."),
    ).toBeVisible();
  });
  it("preserves charts when only trend estimation is unavailable", async () => {
    const success = respond({
      "/health": {
        ...health,
        status: "degraded",
        dataset_status: "analysis_unavailable",
        error: {
          code: "analysis_unavailable",
          message: "No uncertainty estimate.",
        },
      },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) =>
        url.endsWith("/trend")
          ? Promise.resolve(
              Response.json(
                {
                  code: "analysis_unavailable",
                  message: "No uncertainty estimate.",
                },
                { status: 503 },
              ),
            )
          : success(url),
      ),
    );
    render(<App />);
    expect(
      await screen.findByRole("heading", {
        name: "Trend analysis unavailable",
      }),
    ).toBeVisible();
    expect(
      screen.getByRole("img", { name: /^Monthly air temperature\b/ }),
    ).toBeVisible();
    expect(
      screen.queryByText("no statistically significant trend detected."),
    ).not.toBeInTheDocument();
  });
  it("shows empty states and never invents chart points", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        respond({
          "/timeseries/monthly": { ...monthly, observations: [] },
          "/timeseries/annual": { ...annual, observations: [] },
          "/climatology": { ...climatology, observations: [] },
        }),
      ),
    );
    render(<App />);
    expect(
      await screen.findAllByText("No observations available"),
    ).toHaveLength(2);
    expect(
      screen.queryByRole("img", { name: /^Monthly air temperature\b/ }),
    ).not.toBeInTheDocument();
  });
  it("recovers from service failure using reload", async () => {
    const user = userEvent.setup();
    const fetch = vi.fn().mockRejectedValue(new TypeError("offline"));
    vi.stubGlobal("fetch", fetch);
    render(<App />);
    expect(
      await screen.findByRole("heading", {
        name: "Source metadata unavailable",
      }),
    ).toBeVisible();
    expect(
      screen.queryByRole("img", { name: /^Monthly air temperature\b/ }),
    ).not.toBeInTheDocument();
    fetch.mockImplementation(respond());
    await user.click(screen.getByRole("button", { name: "Reload data" }));
    await waitFor(() =>
      expect(
        screen.getByText("no statistically significant trend detected."),
      ).toBeVisible(),
    );
    expect(
      screen.getByRole("img", { name: /^Monthly air temperature\b/ }),
    ).toBeVisible();
  });
  it("shows backend-provided significant cooling and tiny p-values faithfully", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        respond({
          "/trend": {
            ...trend,
            observations: { ...trend.observations, p_value: 1.234e-12 },
            interpretation: {
              ...trend.interpretation,
              significant: true,
              conclusion: "statistically significant cooling trend detected",
            },
          },
        }),
      ),
    );
    render(<App />);
    expect(
      await screen.findByText(
        "statistically significant cooling trend detected.",
      ),
    ).toBeVisible();
    expect(screen.getByText("1.23e-12")).toBeVisible();
  });
});
