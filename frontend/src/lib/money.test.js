import { describe, expect, it } from "vitest";

import {
  centsToDollarsString,
  formatLocal,
  formatUsd,
  formatUsdCompact,
  parseDollarsToCents,
} from "./money";

describe("formatUsd", () => {
  it("formats whole dollars without decimals", () => {
    expect(formatUsd(4500000)).toBe("$45,000");
  });

  it("formats cents with two decimals", () => {
    expect(formatUsd(123456)).toBe("$1,234.56");
  });

  it("formats zero", () => {
    expect(formatUsd(0)).toBe("$0");
  });
});

describe("formatUsdCompact", () => {
  it("formats millions", () => {
    expect(formatUsdCompact(81230000000)).toBe("$812.3M");
  });

  it("formats thousands", () => {
    expect(formatUsdCompact(8374000)).toBe("$83.7K");
  });
});

describe("formatLocal", () => {
  it("formats local minor units", () => {
    expect(formatLocal(425790000, "INR")).toBe("₹4,257,900");
  });
});

describe("parseDollarsToCents", () => {
  it("parses whole dollars", () => {
    expect(parseDollarsToCents("45000")).toBe(4500000);
  });

  it("parses one decimal", () => {
    expect(parseDollarsToCents("45000.5")).toBe(4500050);
  });

  it("parses two decimals", () => {
    expect(parseDollarsToCents("45000.50")).toBe(4500050);
  });

  it("parses dollar signs and commas", () => {
    expect(parseDollarsToCents("$45,000.50")).toBe(4500050);
  });

  it("does not use float math", () => {
    expect(parseDollarsToCents("0.1") + parseDollarsToCents("0.2")).toBe(30);
  });

  it.each(["", " ", "abc", "-1", "1.234", "1.2.3", "1,23.4.5"])(
    "rejects invalid input %s",
    (input) => {
      expect(() => parseDollarsToCents(input)).toThrow();
    },
  );
});

describe("centsToDollarsString", () => {
  it("round trips through parseDollarsToCents", () => {
    const cents = 4500050;

    expect(centsToDollarsString(cents)).toBe("45000.50");
    expect(parseDollarsToCents(centsToDollarsString(cents))).toBe(cents);
  });

  it("pads cents", () => {
    expect(centsToDollarsString(4500005)).toBe("45000.05");
  });
});
