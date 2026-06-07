// Pure payload mapper: folds a human UI selection into the normalized text
// the backend bridge expects. This MIRRORS the stdin human contract produced
// by HumanInteractiveAgent._normalize (Python), so the bridge's text-parsing
// path needs zero changes:
//   seat  -> "3"            (skip / abstain -> "0")
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
