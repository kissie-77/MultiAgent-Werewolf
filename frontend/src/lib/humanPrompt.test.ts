import { describe, it, expect } from "vitest";
import { hintForInput, titleForInput, isRoleRevealed } from "./humanPrompt";

describe("humanPrompt helpers", () => {
  it("uses backend title when provided", () => {
    expect(titleForInput({ kind: "seat", prompt: "", title: "投票放逐" })).toBe("投票放逐");
  });

  it("infers wolf kill title from legacy prompt", () => {
    expect(titleForInput({ kind: "seat", prompt: "狼人请睁眼，今晚你要刀谁" })).toBe("狼人刀人");
  });

  it("uses backend ui_hint when provided", () => {
    expect(hintForInput({ kind: "seat", ui_hint: "自定义提示", allow_skip: true })).toBe("自定义提示");
  });

  it("isRoleRevealed rejects empty and placeholder roles", () => {
    expect(isRoleRevealed("预言家")).toBe(true);
    expect(isRoleRevealed("")).toBe(false);
    expect(isRoleRevealed("秘匿")).toBe(false);
  });
});
