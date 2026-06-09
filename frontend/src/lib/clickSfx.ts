import type { SfxId } from "../audio/soundMap";

const VARIANT: Record<string, SfxId> = {
  submit: "ui_submit",
  error: "ui_error",
  tick: "ui_tick",
  click: "ui_click",
};

/**
 * 全局点击委托的判音逻辑（纯函数，便于单测）。
 * 给定点击命中的最内层元素，返回应播放的 UI 交互音 id；null = 不出声。
 *
 * 规则：
 * 1. 先找最近的可激活元素 `button / a[href] / [role=button]`；非激活元素 → null。
 * 2. 禁用（`disabled` 或 `aria-disabled="true"`）→ null。
 * 3. 看最近的 `data-sfx` / `data-sfx-silent` 标记：
 *    - `data-sfx-silent`（对局内根，按钮已内联接音）→ null，避免重复。
 *    - `data-sfx="off"|"none"`（组件自管音效，如 AudioControls）→ null。
 *    - `data-sfx="submit|error|tick|click"` → 对应音。
 * 4. 无任何标记 → 默认 `ui_click`。
 */
export function resolveClickSfx(target: Element | null): SfxId | null {
  if (!target || typeof target.closest !== "function") return null;
  const el = target.closest('button, a[href], [role="button"]') as
    | (Element & { disabled?: boolean })
    | null;
  if (!el) return null;
  if (el.disabled) return null;
  if (el.getAttribute("aria-disabled") === "true") return null;

  const marked = el.closest("[data-sfx],[data-sfx-silent]");
  if (marked) {
    if (marked.hasAttribute("data-sfx-silent")) return null;
    const v = marked.getAttribute("data-sfx") ?? "click";
    if (v === "off" || v === "none") return null;
    return VARIANT[v] ?? "ui_click";
  }
  return "ui_click";
}
