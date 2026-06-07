import type { AwaitingInputEvent, HumanInputKind } from "../api/types";

/** Fallback title when backend omits `title` (older runs). */
export function titleForInput(input: Pick<AwaitingInputEvent, "kind" | "prompt" | "title">): string {
  if (input.title?.trim()) return input.title.trim();
  const p = input.prompt ?? "";
  switch (input.kind as HumanInputKind) {
    case "speech":
      if (/狼队友|狼队夜聊/.test(p)) return "狼队夜聊";
      if (/警长|PK/.test(p)) return "警长竞选发言";
      return "公开发言";
    case "witch":
      return "女巫行动";
    case "yesno":
      return /警长|竞选/.test(p) ? "警长抉择" : "是 / 否";
    case "multi":
      return "多选目标";
    case "seat":
      if (/狼人请睁眼|今晚你要刀谁/.test(p)) return "狼人刀人";
      if (/投票|放逐/.test(p)) return "投票放逐";
      if (/查验|预言/.test(p)) return "查验目标";
      return "选择目标";
    default:
      return "轮到你了";
  }
}

/** Fallback hint when backend omits `ui_hint`. */
export function hintForInput(
  input: Pick<AwaitingInputEvent, "kind" | "ui_hint" | "allow_skip" | "allow_witch_save" | "multi_count">,
): string {
  if (input.ui_hint?.trim()) return input.ui_hint.trim();
  switch (input.kind) {
    case "witch":
      return input.allow_witch_save === false
        ? "可用毒药指定座位；不行动请点「不行动」。"
        : "可救人、可毒指定座位，或不行动。";
    case "multi":
      return input.multi_count
        ? `请选择 ${input.multi_count} 个不同座位，确认后提交。`
        : "请选择多个不同座位，确认后提交。";
    case "yesno":
      return "请选择「是」或「否」。";
    case "seat":
      return input.allow_skip
        ? "点选目标座位；弃票/跳过请点「弃票」。"
        : "本回合必须选择一个有效目标。";
    case "speech":
      return "请输入完整中文发言（至少 15 字）。";
    default:
      return "";
  }
}

/** Whether a roster role string is known to this seat (non-empty). */
export function isRoleRevealed(role: string | null | undefined): boolean {
  const r = (role ?? "").trim();
  return r.length > 0 && r !== "秘匿" && r !== "???";
}
