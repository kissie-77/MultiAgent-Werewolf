import { describe, it, expect } from "vitest";
import { nearestStandardConfigId, clampPlayerCount } from "./boardConfig";

describe("boardConfig", () => {
  it("clamps to 4–20", () => {
    expect(clampPlayerCount(3)).toBe(4);
    expect(clampPlayerCount(25)).toBe(20);
    expect(clampPlayerCount(7)).toBe(7);
  });

  it("picks nearest standard yaml base", () => {
    expect(nearestStandardConfigId(5)).toBe("standard-6p");
    expect(nearestStandardConfigId(10)).toBe("standard-12p");
    expect(nearestStandardConfigId(16)).toBe("standard-16p");
  });
});
