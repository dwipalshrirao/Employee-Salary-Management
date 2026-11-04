import { describe, expect, test } from "vitest";

import { buildDistributionRows } from "./DistributionChart";

const bandKeys = Array.from({ length: 7 }, (_, index) => `band_${index}`);

describe("DistributionChart", () => {
  test("normalizes every group to 100 percent while keeping counts", () => {
    const rows = buildDistributionRows([
      {
        key: "engineering",
        name: "Engineering",
        headcount: 4,
        counts: [1, 3, 0, 0, 0, 0, 0],
      },
      {
        key: "sales",
        name: "Sales",
        headcount: 2,
        counts: [0, 0, 0, 0, 0, 1, 1],
      },
    ]);

    expect(rows[0].band_0).toBe(25);
    expect(rows[0].band_1).toBe(75);
    expect(rows[1].band_5).toBe(50);
    expect(rows[1].band_6).toBe(50);
    expect(rows[0].counts).toEqual([1, 3, 0, 0, 0, 0, 0]);

    rows.forEach((row) => {
      const total = bandKeys.reduce((sum, key) => sum + row[key], 0);
      expect(total).toBeCloseTo(100);
    });
  });

  test("keeps an empty group at zero instead of dividing by zero", () => {
    const [row] = buildDistributionRows([
      {
        key: "empty",
        name: "Empty",
        headcount: 0,
        counts: [0, 0, 0, 0, 0, 0, 0],
      },
    ]);

    bandKeys.forEach((key) => expect(row[key]).toBe(0));
  });
});
