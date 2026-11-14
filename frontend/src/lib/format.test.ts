import { describe, expect, it } from "vitest";
import { monthLabel, pValue, signed } from "./format";

describe("scientific display formatting", () => {
  it("preserves tiny p-values instead of rounding them to zero", () => {
    expect(pValue(1.234e-16)).toBe("1.23e-16");
    expect(pValue(0)).toBe("Below numerical precision");
    expect(pValue(0.5)).toBe("0.5000");
  });
  it("keeps the slope sign and uses a date without local timezone shifts", () => {
    expect(signed(-0.123456)).toBe("-0.123");
    expect(signed(0.123456)).toBe("+0.123");
    expect(monthLabel("1991-01-01")).toBe("Jan 1991");
  });
});
