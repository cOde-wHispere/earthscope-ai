import { describe, expect, it } from "vitest";
import { monthLabel, monthName, number, pValue, signed } from "./format";

describe("scientific display formatting", () => {
  it("retains grouping, decimal precision and calendar labels across reused formatters", () => {
    expect(number(1009.123456, 4)).toBe("1,009.1235");
    expect(number(-0.012345, 4)).toBe("-0.0123");
    expect(number(27.644393633333355, 4)).toBe("27.6444");
    expect(number(0)).toBe("0.00");
    expect(number(10, 1)).toBe("10.0");
    expect(number(1009.123456, 4)).toBe("1,009.1235");
    expect(monthLabel("2025-12-01")).toBe("Dec 2025");
    expect(monthName(2)).toBe("Feb");
  });
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
