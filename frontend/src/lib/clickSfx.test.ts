import { describe, it, expect } from "vitest";
import { resolveClickSfx } from "./clickSfx";

/** 最小 DOM 节点 mock：实现 resolveClickSfx 需要的 closest/getAttribute/hasAttribute/disabled + 父链。 */
class El {
  tag: string;
  attrs: Record<string, string>;
  disabled: boolean;
  parent: El | null = null;
  constructor(tag: string, attrs: Record<string, string> = {}, opts: { disabled?: boolean } = {}) {
    this.tag = tag.toUpperCase();
    this.attrs = attrs;
    this.disabled = !!opts.disabled;
  }
  getAttribute(name: string): string | null {
    return name in this.attrs ? this.attrs[name] : null;
  }
  hasAttribute(name: string): boolean {
    return name in this.attrs;
  }
  private matches(sel: string): boolean {
    if (sel.includes("data-sfx")) {
      return "data-sfx" in this.attrs || "data-sfx-silent" in this.attrs;
    }
    // 'button, a[href], [role="button"]'
    if (this.tag === "BUTTON") return true;
    if (this.tag === "A" && "href" in this.attrs) return true;
    return this.attrs["role"] === "button";
  }
  closest(sel: string): El | null {
    let n: El | null = this;
    while (n) {
      if (n.matches(sel)) return n;
      n = n.parent;
    }
    return null;
  }
}
/** 把外→内的节点串成父链，返回最内层（点击目标）。 */
function nest(...els: El[]): El {
  for (let i = 1; i < els.length; i++) els[i].parent = els[i - 1];
  return els[els.length - 1];
}
const resolve = (el: El | null) => resolveClickSfx(el as unknown as Element | null);

describe("resolveClickSfx", () => {
  it("defaults plain button / link / role=button to ui_click", () => {
    expect(resolve(new El("button"))).toBe("ui_click");
    expect(resolve(new El("a", { href: "/x" }))).toBe("ui_click");
    expect(resolve(new El("div", { role: "button" }))).toBe("ui_click");
  });

  it("returns null for non-activatable elements and null target", () => {
    expect(resolve(new El("div"))).toBeNull();
    expect(resolve(new El("a"))).toBeNull(); // <a> 无 href 不算
    expect(resolve(null)).toBeNull();
  });

  it("climbs from an inner icon/span to its button", () => {
    const target = nest(new El("button"), new El("span"));
    expect(resolve(target)).toBe("ui_click");
  });

  it("maps data-sfx variants", () => {
    expect(resolve(new El("button", { "data-sfx": "submit" }))).toBe("ui_submit");
    expect(resolve(new El("button", { "data-sfx": "error" }))).toBe("ui_error");
    expect(resolve(new El("button", { "data-sfx": "tick" }))).toBe("ui_tick");
    expect(resolve(new El("button", { "data-sfx": "click" }))).toBe("ui_click");
    expect(resolve(new El("button", { "data-sfx": "weird" }))).toBe("ui_click"); // 未知→默认
  });

  it("silences data-sfx off/none", () => {
    expect(resolve(new El("button", { "data-sfx": "off" }))).toBeNull();
    expect(resolve(new El("button", { "data-sfx": "none" }))).toBeNull();
  });

  it("silences anything under a data-sfx-silent ancestor (in-game root)", () => {
    const target = nest(new El("div", { "data-sfx-silent": "" }), new El("button"));
    expect(resolve(target)).toBeNull();
  });

  it("honors an off marker on an ancestor (e.g. AudioControls root)", () => {
    const target = nest(new El("div", { "data-sfx": "off" }), new El("button"));
    expect(resolve(target)).toBeNull();
  });

  it("nearest mark wins: data-sfx on the button overrides a silent ancestor", () => {
    const target = nest(new El("div", { "data-sfx-silent": "" }), new El("button", { "data-sfx": "submit" }));
    expect(resolve(target)).toBe("ui_submit");
  });

  it("returns null for disabled / aria-disabled buttons", () => {
    expect(resolve(new El("button", {}, { disabled: true }))).toBeNull();
    expect(resolve(new El("button", { "aria-disabled": "true" }))).toBeNull();
  });
});
