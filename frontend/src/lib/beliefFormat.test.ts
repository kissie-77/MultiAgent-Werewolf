import { describe, it, expect } from "vitest";
import { matrixScale, formatWolfProb, heatColor } from "./beliefFormat";

describe("matrixScale", () => {
  it("scales cell/font down by player count tiers", () => {
    expect(matrixScale(6)).toEqual({ cell: 34, font: 10 });
    expect(matrixScale(7)).toEqual({ cell: 28, font: 9 });
    expect(matrixScale(9)).toEqual({ cell: 28, font: 9 });
    expect(matrixScale(10)).toEqual({ cell: 22, font: 8 });
    expect(matrixScale(12)).toEqual({ cell: 22, font: 8 });
    expect(matrixScale(13)).toEqual({ cell: 17, font: 7 });
    expect(matrixScale(16)).toEqual({ cell: 17, font: 7 });
  });
});

describe("formatWolfProb", () => {
  it("renders rounded integer percent", () => {
    expect(formatWolfProb(0)).toBe("0%");
    expect(formatWolfProb(0.05)).toBe("5%");
    expect(formatWolfProb(0.333)).toBe("33%");
    expect(formatWolfProb(0.25)).toBe("25%");
    expect(formatWolfProb(1)).toBe("100%");
  });
});

describe("heatColor", () => {
  it("interpolates blue->amber->crimson", () => {
    expect(heatColor(0)).toBe("rgb(15,50,100)");
    expect(heatColor(0.5)).toBe("rgb(217,119,6)");
    expect(heatColor(1)).toBe("rgb(153,27,27)");
  });
});
