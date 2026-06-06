import { describe, it, expect } from "vitest";
import { buildHumanPayload } from "./humanInput";

describe("buildHumanPayload", () => {
  it("maps seat choice", () => {
    expect(buildHumanPayload({ kind: "seat", seat: 3 })).toBe("3");
    expect(buildHumanPayload({ kind: "seat", skip: true })).toBe("0");
  });

  it("maps witch actions", () => {
    expect(buildHumanPayload({ kind: "witch", action: "save" })).toBe("救");
    expect(buildHumanPayload({ kind: "witch", action: "poison", seat: 3 })).toBe("毒 [[3]]");
    expect(buildHumanPayload({ kind: "witch", action: "none" })).toBe("none");
  });

  it("maps yesno and speech", () => {
    expect(buildHumanPayload({ kind: "yesno", yes: true })).toBe("1");
    expect(buildHumanPayload({ kind: "yesno", yes: false })).toBe("0");
    expect(buildHumanPayload({ kind: "speech", text: "我觉得3号有问题" })).toBe("我觉得3号有问题");
  });

  it("maps multi selection", () => {
    expect(buildHumanPayload({ kind: "multi", seats: [3, 5] })).toBe("3 5");
  });
});
