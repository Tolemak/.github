import { describe, expect, it } from "vitest";
import { formatPln, total } from "./price.js";

describe("total", () => {
  it("sums line items", () => {
    expect(total([{ unitPrice: 250, quantity: 2 }, { unitPrice: 100, quantity: 1 }])).toBe(600);
  });

  it("applies a discount", () => {
    expect(total([{ unitPrice: 1000, quantity: 1 }], 15)).toBe(850);
  });

  it("rejects an invalid discount", () => {
    expect(() => total([], 101)).toThrow(RangeError);
    expect(() => total([], -1)).toThrow(RangeError);
  });
});

describe("formatPln", () => {
  it("formats minor units", () => {
    expect(formatPln(12345)).toBe("123.45 zł");
  });
});
