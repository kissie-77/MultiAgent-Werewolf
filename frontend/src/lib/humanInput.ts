// 纯载荷映射器：将人类 UI 选择折叠为规范化文本
// 后端桥接期望的格式。这镜像了 HumanInteractiveAgent._normalize（Python）生成的 stdin 人类协议，
// 因此桥接的文本解析路径无需任何更改：
//   seat  -> "3"            （跳过/弃权 -> "0"）
//   witch -> "救" (save) | "毒 [[3]]" (poison seat 3) | "none" (no action)
//   yesno -> "1" (yes) | "0" (no)
//   multi -> "3 5"          (space-joined seats)
//   speech-> the raw text
//
// `kind` matches AwaitingInputEvent.kind / HumanInputBroker kinds.

export type HumanInputKind = "seat" | "multi" | "yesno" | "witch" | "speech";

export type HumanInputSelection =
  | { kind: "seat"; seat?: number; skip?: boolean }
  | { kind: "witch"; action: "save" | "poison" | "none"; seat?: number }
  | { kind: "yesno"; yes: boolean }
  | { kind: "multi"; seats: number[] }
  | { kind: "speech"; text: string };

export function buildHumanPayload(input: HumanInputSelection): string {
  switch (input.kind) {
    case "seat":
      return input.skip || input.seat == null ? "0" : String(input.seat);
    case "witch":
      if (input.action === "save") return "救";
      if (input.action === "poison") {
        return input.seat == null ? "none" : `毒 [[${input.seat}]]`;
      }
      return "none";
    case "yesno":
      return input.yes ? "1" : "0";
    case "multi":
      return input.seats.join(" ");
    case "speech":
      return input.text;
  }
}
