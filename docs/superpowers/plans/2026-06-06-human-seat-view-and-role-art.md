# Human Seat View Fixes + Role Art Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the human-vs-AI seat view render like spectate (player cards + speech bubbles + event timeline) and make setup/in-game role art map precisely for all 22 roles — by fixing the data contract and asset wiring, reusing existing components.

**Architecture:** Backend sends a *redacted* seat roster (self role only; wolf teammates too if the human is a wolf); the shared `reduceEvent` tags the human seat `isUser`, hides others' roles, maps public dialogue/event types into `speechLogs` + a new `eventLog` timeline; assets are deployed into `public/` under canonical PascalCase stems and `roles.ts` resolves all 22 roles for both `/material` (in-game) and `/tarot` (setup).

**Tech Stack:** FastAPI (Python, pytest, `asyncio_mode=auto`), React 19 + Zustand + Vite (vitest), Playwright MCP for real-machine regression.

**Pre-flight (repo rule, CLAUDE.md):** Before editing `reduceEvent` (Task 2/3) and `_initial_snapshot`/`_stream_events` (Task 1), run `gitnexus_impact({target:"reduceEvent", direction:"upstream"})` and `gitnexus_impact({target:"_initial_snapshot", direction:"upstream"})`; report blast radius. The GitNexus index is stale since `f5d1d21` — if a tool warns, run `npx gitnexus analyze` first. Both symbols are leaf-ish (reducer is pure, `_initial_snapshot` is called only by `_stream_events`), so risk is expected LOW — but confirm.

**Reference spec:** `docs/superpowers/specs/2026-06-06-human-seat-view-and-role-art-design.md`

---

## File Structure

| File | Responsibility | Task |
|------|----------------|------|
| `src/llm_werewolf/interface/api/routes/actions.py` | add `_redact_roster_for_seat`; seat snapshot carries redacted roster | 1 |
| `tests/interface/test_seat_roster_redaction.py` | unit tests for redaction (create) | 1 |
| `frontend/src/lib/gameReducer.ts` | `selfSeat`→`isUser`, hidden role, `sheriff_candidate_speech` case, `eventLog` | 2,3 |
| `frontend/src/types.ts` | add `GameState.eventLog` | 3 |
| `frontend/src/store.ts` | `connectSeat` injects `selfSeat` into snapshot frame | 2 |
| `frontend/src/lib/gameReducer.test.ts` | reducer tests (extend) | 2,3 |
| `frontend/src/components/ControlPanel.tsx` | no-user ⇒ not dead | 4 |
| `frontend/src/components/SpeechConsole.tsx` | self = `isUser` seat (not hardcoded 1); render `eventLog` when no speeches | 4 |
| `frontend/src/components/CardDeck.tsx` | hidden/unknown role ⇒ 秘匿 (no villager art) | 4 |
| `frontend/public/material/*`, `frontend/public/tarot/*` | deployed 22-role art, canonical PascalCase | 5 |
| `frontend/src/utils/roles.ts` | `stemFor` + `getRoleImage` + `getTarotImage`, all 22 roles | 6 |
| `frontend/src/utils/roles.test.ts` | role-image tests (create) | 6 |
| `frontend/src/components/GameSetup.tsx` | setup card uses `getTarotImage` | 7 |
| `frontend/src/components/SkillReleaseModal.tsx` | tarot via `getTarotImage` | 7 |

---

## Task 1: Backend redacted seat roster

**Files:**
- Modify: `src/llm_werewolf/interface/api/routes/actions.py` (`_initial_snapshot` ~262-272, `_stream_events` ~287)
- Test: `tests/interface/test_seat_roster_redaction.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/interface/test_seat_roster_redaction.py`:

```python
from llm_werewolf.interface.api.routes.actions import _redact_roster_for_seat

ROSTER = [
    {"seat": 1, "name": "P1", "role": "Witch", "camp": "villager", "is_alive": True},
    {"seat": 2, "name": "P2", "role": "Werewolf", "camp": "werewolf", "is_alive": True},
    {"seat": 3, "name": "P3", "role": "Seer", "camp": "villager", "is_alive": False},
    {"seat": 4, "name": "P4", "role": "Alpha Wolf", "camp": "werewolf", "is_alive": True},
]


def test_villager_human_sees_only_own_role():
    out = _redact_roster_for_seat(ROSTER, seat=1)
    by_seat = {r["seat"]: r for r in out}
    # always-public fields kept for everyone
    assert by_seat[2]["name"] == "P2" and by_seat[2]["is_alive"] is True
    assert by_seat[3]["is_alive"] is False
    # only own role/camp revealed
    assert by_seat[1]["role"] == "Witch" and by_seat[1]["camp"] == "villager"
    assert by_seat[2]["role"] is None and by_seat[2]["camp"] is None
    assert by_seat[3]["role"] is None and by_seat[4]["role"] is None


def test_wolf_human_sees_all_wolf_teammates():
    out = _redact_roster_for_seat(ROSTER, seat=2)  # P2 is a Werewolf
    by_seat = {r["seat"]: r for r in out}
    assert by_seat[2]["role"] == "Werewolf"      # self
    assert by_seat[4]["role"] == "Alpha Wolf"    # fellow wolf revealed
    assert by_seat[1]["role"] is None            # villager hidden
    assert by_seat[3]["role"] is None            # villager hidden


def test_empty_or_missing_roster_is_empty_list():
    assert _redact_roster_for_seat(None, seat=1) == []
    assert _redact_roster_for_seat([], seat=1) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONUTF8=1 uv run pytest tests/interface/test_seat_roster_redaction.py -q`
Expected: FAIL — `ImportError: cannot import name '_redact_roster_for_seat'`.

- [ ] **Step 3: Implement `_redact_roster_for_seat` and wire it in**

In `actions.py`, add the function right after `_load_god_roster` (after ~line 259):

```python
def _redact_roster_for_seat(roster: object | None, seat: int | None) -> list[dict]:
    """Seat-view roster: seat/name/is_alive for everyone; role/camp only for the
    human's own seat (and fellow werewolves when the human is a werewolf)."""
    if not isinstance(roster, list) or not roster:
        return []
    self_entry = next((r for r in roster if r.get("seat") == seat), None)
    self_is_wolf = bool(self_entry) and self_entry.get("camp") == "werewolf"
    out: list[dict] = []
    for r in roster:
        reveal = (r.get("seat") == seat) or (self_is_wolf and r.get("camp") == "werewolf")
        out.append({
            "seat": r.get("seat"),
            "name": r.get("name"),
            "is_alive": r.get("is_alive", True),
            "role": r.get("role") if reveal else None,
            "camp": r.get("camp") if reveal else None,
        })
    return out
```

Replace `_initial_snapshot` (lines ~262-272) with a `seat`-aware version:

```python
def _initial_snapshot(run_dir: Path, view: str, seat: int | None = None) -> dict:
    """Build the snapshot first-frame payload. god = full roster; seat = redacted."""
    try:
        snap = extract_game_snapshot(run_dir).model_dump()
    except Exception:  # pragma: no cover - snapshot best-effort
        snap = {}
    roster = _load_god_roster(run_dir)
    if roster is not None:
        if view == "god":
            snap["roster"] = roster
        elif view == "seat":
            snap["roster"] = _redact_roster_for_seat(roster, seat)
    return snap
```

In `_stream_events`, update the snapshot call (line ~287) to pass `seat`:

```python
    snap = _initial_snapshot(run_dir, view, seat)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONUTF8=1 uv run pytest tests/interface/test_seat_roster_redaction.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the interface suite to confirm no regression**

Run: `PYTHONUTF8=1 uv run pytest tests/interface -q`
Expected: all pass (existing stream/visibility tests unaffected — god path unchanged).

- [ ] **Step 6: Commit**

```bash
git add src/llm_werewolf/interface/api/routes/actions.py tests/interface/test_seat_roster_redaction.py
git commit -m "feat(api): seat stream sends redacted roster (self + wolf teammates)"
```

---

## Task 2: Reducer tags `isUser` + hides others' roles

**Files:**
- Modify: `frontend/src/lib/gameReducer.ts` (`SseEvent` interface; `snapshot` case 50-58)
- Modify: `frontend/src/store.ts` (`connectSeat` snapshot listener ~502)
- Test: `frontend/src/lib/gameReducer.test.ts` (extend)

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/lib/gameReducer.test.ts`:

```ts
import { reduceEvent, initialSpectateState } from "./gameReducer";

describe("seat snapshot redaction", () => {
  const snap = {
    event_type: "snapshot",
    selfSeat: 1,
    roster: [
      { seat: 1, name: "P1", role: "Witch", is_alive: true },
      { seat: 2, name: "P2", role: null, is_alive: true },
    ],
  };

  it("tags the self seat and reveals only its role", () => {
    const s = reduceEvent(initialSpectateState(), snap as any);
    expect(s.players).toHaveLength(2);
    expect(s.players[0].isUser).toBe(true);
    expect(s.players[0].role).toBe("Witch");
    expect(s.players[1].isUser).toBe(false);
    expect(s.players[1].role).toBe(""); // hidden -> empty
  });

  it("spectate snapshot (no selfSeat) tags nobody", () => {
    const god = { event_type: "snapshot", roster: [{ seat: 1, name: "P1", role: "Seer", is_alive: true }] };
    const s = reduceEvent(initialSpectateState(), god as any);
    expect(s.players[0].isUser).toBe(false);
    expect(s.players[0].role).toBe("Seer");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/gameReducer.test.ts`
Expected: FAIL — `players[0].isUser` is `false` (reducer hardcodes `isUser:false`) and `players[1].role` is `null` not `""`.

- [ ] **Step 3: Implement reducer + store change**

In `frontend/src/lib/gameReducer.ts`, extend the `SseEvent` interface (lines 3-11): change the roster `role` type and add `selfSeat`:

```ts
export interface SseEvent {
  event_type: string;
  round_number?: number;
  phase?: string;
  message?: string;
  data?: Record<string, any>;
  roster?: { seat: number; name: string; role: string | null; camp?: string | null; is_alive?: boolean }[];
  selfSeat?: number;
  event_id?: number;
}
```

Replace the `snapshot` case (lines 50-58):

```ts
    case "snapshot": {
      if (ev.roster?.length) {
        const selfSeat = ev.selfSeat;
        s.players = ev.roster.map<Player>((r) => ({
          id: r.seat, name: r.name, role: r.role ?? "",
          isUser: selfSeat != null && r.seat === selfSeat,
          isAlive: r.is_alive !== false, avatarSeed: r.name, lastSpeech: "",
          statusNotes: "",
        }));
      }
      break;
    }
```

In `frontend/src/store.ts`, the `connectSeat` snapshot listener (line ~502) injects `selfSeat`:

```ts
            set({ state: reduceEvent(cur, { ...snap, event_type: "snapshot", selfSeat: seat }) });
```

(Leave `connectSpectate`'s snapshot listener unchanged — no `selfSeat`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/gameReducer.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/gameReducer.ts frontend/src/store.ts frontend/src/lib/gameReducer.test.ts
git commit -m "feat(fe): seat snapshot tags isUser and hides others' roles"
```

---

## Task 3: Reducer adds `eventLog` timeline + sheriff speeches

**Files:**
- Modify: `frontend/src/types.ts` (`GameState`)
- Modify: `frontend/src/lib/gameReducer.ts` (`initialSpectateState`, `reduceEvent`)
- Test: `frontend/src/lib/gameReducer.test.ts` (extend)

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/lib/gameReducer.test.ts`:

```ts
describe("public dialogue + event timeline", () => {
  it("maps sheriff_candidate_speech into speechLogs", () => {
    let s = initialSpectateState();
    s = reduceEvent(s, { event_type: "snapshot", selfSeat: 1,
      roster: [{ seat: 5, name: "P5", role: null, is_alive: true }] } as any);
    s = reduceEvent(s, { event_type: "sheriff_candidate_speech", message: "我竞选警长",
      round_number: 1, phase: "sheriff_election", data: { player_id: "player_5" } } as any);
    expect(s.speechLogs).toHaveLength(1);
    expect(s.speechLogs[0].content).toBe("我竞选警长");
  });

  it("accumulates any messaged event into eventLog and dedupes adjacent repeats", () => {
    let s = initialSpectateState();
    s = reduceEvent(s, { event_type: "message", message: "天黑请闭眼" } as any);
    s = reduceEvent(s, { event_type: "message", message: "天黑请闭眼" } as any); // dup
    s = reduceEvent(s, { event_type: "werewolf_killed", message: "Player3 被狼人杀害" } as any);
    expect(s.eventLog.map((e) => e.message)).toEqual(["天黑请闭眼", "Player3 被狼人杀害"]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/gameReducer.test.ts`
Expected: FAIL — `s.eventLog` is `undefined` and `sheriff_candidate_speech` produces no speechLog.

- [ ] **Step 3: Implement**

In `frontend/src/types.ts`, add to `GameState` (after `speechLogs`, line ~20):

```ts
  eventLog: { round: number; phase: string; type: string; message: string }[];
```

In `frontend/src/lib/gameReducer.ts`, add `eventLog: []` to `initialSpectateState()` return (inside the object, e.g. after `speechLogs: []`):

```ts
    speechLogs: [], eventLog: [], narration: "", winner: null,
```

In `reduceEvent`, extend the working-copy clone (line 43) to also copy `eventLog`:

```ts
  const s: GameState = { ...prev, players: prev.players.map((p) => ({ ...p })), speechLogs: [...prev.speechLogs], eventLog: [...prev.eventLog] };
```

Immediately after the phase/day update (after line 47, before the `switch`), append the timeline accumulator:

```ts
  if (ev.message) {
    const last = s.eventLog[s.eventLog.length - 1];
    if (!last || last.message !== ev.message) {
      s.eventLog.push({ round: ev.round_number ?? s.dayNumber, phase: ev.phase ?? "", type: ev.event_type, message: ev.message });
    }
  }
```

Add `sheriff_candidate_speech` to the speech case labels (line 60-61):

```ts
    case "player_speech":
    case "player_discussion":
    case "sheriff_candidate_speech": {
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/gameReducer.test.ts`
Expected: PASS (all reducer tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types.ts frontend/src/lib/gameReducer.ts frontend/src/lib/gameReducer.test.ts
git commit -m "feat(fe): reducer event timeline + sheriff candidate speeches"
```

---

## Task 4: View guards (no-user not dead, self-seat, hidden art, night timeline)

**Files:**
- Modify: `frontend/src/components/ControlPanel.tsx:282`
- Modify: `frontend/src/components/SpeechConsole.tsx` (self seat ~125, typing banner 238/245, empty state 116-120)
- Modify: `frontend/src/components/CardDeck.tsx` (portrait branch ~183, roleColor ~146)

> View glue — behavioral coverage is the Playwright regression in Task 8. No new unit test (no extractable pure logic worth isolating). Run `npx tsc --noEmit` after edits.

- [ ] **Step 1: ControlPanel — empty roster is not "dead"**

`frontend/src/components/ControlPanel.tsx` line 282, change:

```ts
  const isDead = user ? !user.isAlive : false;
```

(was `: true` — which forced the false "你已死/观战" banner when `players` was empty.)

- [ ] **Step 2: SpeechConsole — self is the `isUser` seat, not hardcoded 1**

`frontend/src/components/SpeechConsole.tsx`: after line 10 add:

```ts
  const selfSeat = gameState?.players.find((p) => p.isUser)?.id ?? null;
```

Line ~125 change `const isSelf = log.playerId === 1;` to:

```ts
              const isSelf = log.playerId === selfSeat;
```

Lines 238 and 245 change the typing-banner condition `currentSpeakerId !== 1` to `currentSpeakerId !== selfSeat` (both occurrences).

- [ ] **Step 3: SpeechConsole — render eventLog when there are no speeches**

`frontend/src/components/SpeechConsole.tsx`, replace the empty-state block (lines 116-120) so that when there are no speeches but there ARE timeline events, the center shows the chronicle instead of "风平浪静":

```tsx
        {speechLogs.length === 0 ? (
          (gameState?.eventLog?.length ?? 0) > 0 ? (
            <div className="flex flex-col gap-2 py-6 px-2">
              {gameState!.eventLog.map((e, i) => (
                <div key={i} className="text-center font-mono text-[11px] text-indigo-300/80 leading-relaxed">
                  <span className="text-red-500/70 mr-2">[D-{e.round}{e.phase ? " · " + e.phase : ""}]</span>
                  {e.message}
                </div>
              ))}
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-zinc-600 gap-2 py-8">
              <span className="font-serif text-4xl text-zinc-800 animate-pulse">☠</span>
              <span className="font-mono text-xs tracking-widest text-zinc-700 uppercase font-black">风平浪静 虚无之地</span>
            </div>
          )
        ) : (
```

(The closing `) : (` already precedes the speech-bubble `AnimatePresence`; only the empty branch changes.)

- [ ] **Step 4: CardDeck — hidden/unknown role shows 秘匿, never villager art**

`frontend/src/components/CardDeck.tsx` line 141, require a known role to expose identity:

```ts
            const isExposed = (p.isUser || !p.isAlive || phase === "GAME_OVER" || (gameState?.gameMode === "llmOnly" && llmExposeAll)) && !!p.role;
```

Line 146 `if (isExposed) {` already guards roleColor — with `&& !!p.role` folded into `isExposed`, hidden roles keep the neutral color and the existing 秘匿 placeholder (the `isExposed ? <portrait> : <placeholder>` branch at ~183) renders correctly.

- [ ] **Step 5: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ControlPanel.tsx frontend/src/components/SpeechConsole.tsx frontend/src/components/CardDeck.tsx
git commit -m "fix(fe): seat view guards — alive human, self seat, hidden role art, night timeline"
```

---

## Task 5: Deploy 22-role art into `public/` (canonical PascalCase)

**Files:**
- Create: `frontend/public/material/*.png` (22), `frontend/public/tarot/*.png` (22)

- [ ] **Step 1: Deploy via script (rm-first to avoid case collisions)**

Run from repo root:

```bash
cd frontend
rm -rf public/material public/tarot
mkdir -p public/material public/tarot

mat="Werewolf:wolf.png AlphaWolf:AlphaWolf.png WhiteWolf:WhiteWolf.png WolfBeauty:wolfbeauty.png GuardianWolf:GuardianWolf.png HiddenWolf:HiddenWolf.png BloodMoonApostle:BloodMoonApostle.png NightmareWolf:NightmareWolf.png Villager:villager.png Seer:seer.png Witch:witch.png Hunter:hunter.png Guard:Guard.png Idiot:idiot.png Elder:Elder.png Knight:knight.png Magician:magician.png Cupid:cupid.png Raven:raven.png GraveyardKeeper:GraveyardKeeper.png Thief:Thief.png Lover:Lover.png"
for pair in $mat; do cp "material/${pair#*:}" "public/material/${pair%%:*}.png"; done

tar="Werewolf:wolf.png AlphaWolf:AlphaWolf.png WhiteWolf:WhiteWolf.png WolfBeauty:WolfBeauty.png GuardianWolf:GuardianWolf.png HiddenWolf:HiddenWolf.png BloodMoonApostle:BloodMoonApostle.png NightmareWolf:NightmareWolf.png Villager:villager.png Seer:seer.png Witch:witch.png Hunter:hunter.png Guard:Guard.png Idiot:idiot.png Elder:Elder.png Knight:Knight.png Magician:Magician.png Cupid:Cupid.png Raven:Raven.png GraveyardKeeper:GraveyardKeeper.png Thief:Thief.png Lover:Lover.png"
for pair in $tar; do cp "tarot/${pair#*:}" "public/tarot/${pair%%:*}.png"; done
```

- [ ] **Step 2: Verify 22/22 each and PNG validity**

Run:

```bash
cd frontend
echo "material: $(ls public/material | wc -l)  tarot: $(ls public/tarot | wc -l)"
# every served PNG starts with the PNG magic bytes (137 80 78 71)
for f in public/material/*.png public/tarot/*.png; do
  head -c4 "$f" | od -An -tu1 | grep -q "137  80  78  71" || echo "CORRUPT: $f"
done
echo "done"
```

Expected: `material: 22  tarot: 22`, no `CORRUPT:` lines, prints `done`.

- [ ] **Step 3: Commit**

```bash
git add frontend/public/material frontend/public/tarot
git commit -m "assets: deploy 22-role material + tarot art to public/ (canonical PascalCase)"
```

---

## Task 6: Rewrite `roles.ts` — all 22 roles, material + tarot

**Files:**
- Modify: `frontend/src/utils/roles.ts` (full rewrite)
- Test: `frontend/src/utils/roles.test.ts` (create)

- [ ] **Step 1: Write the failing test**

Create `frontend/src/utils/roles.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { getRoleImage, getTarotImage } from "./roles";

describe("role image resolution", () => {
  it("Chinese setup roles -> tarot", () => {
    expect(getTarotImage("白痴")).toBe("/tarot/Idiot.png");
    expect(getTarotImage("预言家")).toBe("/tarot/Seer.png");
    expect(getTarotImage("村民")).toBe("/tarot/Villager.png");
  });
  it("English roster roles -> material", () => {
    expect(getRoleImage("Witch")).toBe("/material/Witch.png");
    expect(getRoleImage("Werewolf")).toBe("/material/Werewolf.png");
  });
  it("strips spaces in English names", () => {
    expect(getRoleImage("Alpha Wolf")).toBe("/material/AlphaWolf.png");
    expect(getTarotImage("Graveyard Keeper")).toBe("/tarot/GraveyardKeeper.png");
  });
  it("idiot is distinct from villager (the original bug)", () => {
    expect(getTarotImage("白痴")).not.toBe(getTarotImage("村民"));
    expect(getRoleImage("白痴")).toBe("/material/Idiot.png");
  });
  it("unknown wolf-ish -> Werewolf, else Villager", () => {
    expect(getRoleImage("狼人")).toBe("/material/Werewolf.png");
    expect(getRoleImage("???")).toBe("/material/Villager.png");
    expect(getRoleImage("")).toBe("/material/Villager.png");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/utils/roles.test.ts`
Expected: FAIL — `getTarotImage` is not exported; `getRoleImage("白痴")` returns `/material/villiger.png`.

- [ ] **Step 3: Rewrite `frontend/src/utils/roles.ts`**

Replace the whole file with:

```ts
// Role art is served from `frontend/public/{material,tarot}/<PascalCase>.png`
// (canonical stems matching the backend role names). Reference as plain absolute
// URLs — do NOT `import` from `public/` (Vite returns SPA-fallback HTML).
// `material` = in-game portrait, `tarot` = setup arcana card.

// role string (English roster name, space-stripped, OR Chinese display name) -> canonical stem
const ROLE_STEM: Record<string, string> = {
  // --- English (backend roster role_name, spaces stripped by stemFor) ---
  Werewolf: "Werewolf", AlphaWolf: "AlphaWolf", WhiteWolf: "WhiteWolf", WolfBeauty: "WolfBeauty",
  GuardianWolf: "GuardianWolf", HiddenWolf: "HiddenWolf", BloodMoonApostle: "BloodMoonApostle",
  NightmareWolf: "NightmareWolf",
  Villager: "Villager", Seer: "Seer", Witch: "Witch", Hunter: "Hunter", Guard: "Guard",
  Idiot: "Idiot", Elder: "Elder", Knight: "Knight", Magician: "Magician", Cupid: "Cupid",
  Raven: "Raven", GraveyardKeeper: "GraveyardKeeper", Thief: "Thief", Lover: "Lover",
  // --- Chinese (in-UI display names / setup dropdown values) ---
  狼人: "Werewolf", 狼王: "AlphaWolf", 白狼: "WhiteWolf", 狼美人: "WolfBeauty", 守卫狼: "GuardianWolf",
  隐狼: "HiddenWolf", 血月使徒: "BloodMoonApostle", 梦魇狼: "NightmareWolf",
  村民: "Villager", 平民: "Villager", 预言家: "Seer", 女巫: "Witch", 猎人: "Hunter", 守卫: "Guard",
  白痴: "Idiot", 长老: "Elder", 骑士: "Knight", 魔术师: "Magician", 丘比特: "Cupid", 乌鸦: "Raven",
  守墓人: "GraveyardKeeper", 盗贼: "Thief", 恋人: "Lover",
};

function stemFor(role: string): string {
  const raw = role ?? "";
  const key = raw.replace(/\s+/g, ""); // "Alpha Wolf" -> "AlphaWolf"
  if (ROLE_STEM[key]) return ROLE_STEM[key];
  if (ROLE_STEM[raw]) return ROLE_STEM[raw];
  if (key.toLowerCase().includes("wolf") || raw.includes("狼")) return "Werewolf";
  return "Villager";
}

export const getRoleImage = (role: string) => `/material/${stemFor(role)}.png`;
export const getTarotImage = (role: string) => `/tarot/${stemFor(role)}.png`;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/utils/roles.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/roles.ts frontend/src/utils/roles.test.ts
git commit -m "feat(fe): roles.ts resolves all 22 roles for material + tarot"
```

---

## Task 7: Wire setup + skill modal to tarot

**Files:**
- Modify: `frontend/src/components/GameSetup.tsx` (import line 10, img line 475)
- Modify: `frontend/src/components/SkillReleaseModal.tsx` (lines 39-48)

- [ ] **Step 1: GameSetup uses `getTarotImage`**

`frontend/src/components/GameSetup.tsx` line 10, change the import:

```ts
import { getTarotImage } from "../utils/roles";
```

Line 475, change the setup card image source:

```tsx
                          src={getTarotImage(userRole)}
```

(`getRoleImage` was only used here in this file; removing the import is correct.)

- [ ] **Step 2: SkillReleaseModal uses `getTarotImage`**

`frontend/src/components/SkillReleaseModal.tsx`: add the import after line 5:

```ts
import { getTarotImage } from "../utils/roles";
```

Replace the hardcoded map + `imageSrc` (lines 39-48) with:

```ts
  const imageSrc = getTarotImage(userRole);
```

- [ ] **Step 3: Type-check + build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: no type errors; build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/GameSetup.tsx frontend/src/components/SkillReleaseModal.tsx
git commit -m "fix(fe): setup card + skill modal use per-role tarot art"
```

---

## Task 8: Full verification + real-machine regression

**Files:** none (verification only)

- [ ] **Step 1: Full automated suites**

```bash
cd frontend && npx vitest run && npx tsc --noEmit && npm run build
cd .. && PYTHONUTF8=1 uv run pytest tests/interface -q
```

Expected: vitest all green (incl. new gameReducer + roles tests), tsc clean, build OK, pytest interface all pass.

- [ ] **Step 2: Real-machine regression (Playwright MCP)**

Ensure backend (`:8010`, keyed) + Vite (`:5183`) are running (restart Vite so new `public/` assets are served). Drive the browser and verify:

1. **Setup art (#2):** open setup → human mode; switch SELECT ARCANA across 白痴/预言家/女巫/狼人/猎人/村民/守卫/长老 — the card image matches each role (白痴 shows Idiot art, **not** villager). Confirm `<img src>` = `/tarot/<Role>.png`.
2. **Seat cards (#1):** start human-vs-AI (6p, seat 1) → left panel shows **6 cards**; the human's own card shows the real role + 本人; the other 5 show 秘匿; **no** "你已死/观战" red banner while alive.
3. **Dialogue (#3):** advance to day → public speeches render as bubbles with correct seat names (not `P{n}`); the human's bubble is right-aligned with 本人 badge; night/sheriff phase center shows the **event timeline** (天黑请闭眼 / deaths / 警长选举) instead of blank.
4. **Anti-cheat:** confirm a non-wolf human sees no wolf-night-chat bubbles, and other AI roles stay 秘匿.

Capture screenshots to `frontend/diag_redesign/after-*.png`.

- [ ] **Step 3: Final commit (evidence note, if any docs updated)**

If you update `docs/frontend/ROADMAP.md` change-log, commit:

```bash
git add docs/frontend/ROADMAP.md
git commit -m "docs(frontend): note seat-view + role-art fixes"
```

---

## Self-Review

**Spec coverage:** §4.1 redacted roster → Task 1. §4.2 isUser/hidden + dialogue cases + eventLog → Tasks 2,3. §4.3 false-dead banner → Task 4. §4.4 assets+roles+wiring → Tasks 5,6,7. §6 tests → Tasks 1,2,3,6 (unit) + Task 8 (Playwright). All covered.

**Type consistency:** `selfSeat` (camelCase) consistent across reducer interface, snapshot case, and store injection. `eventLog` item shape `{round,phase,type,message}` identical in types.ts, initialSpectateState, reduceEvent push, and SpeechConsole render. `stemFor`/`getRoleImage`/`getTarotImage` names consistent across Tasks 6,7. Camp string `"werewolf"` matches `Camp.WEREWOLF` (`enums.py:7`).

**Placeholder scan:** none — every code step shows complete code; the one runtime unknown (does `god_roster.json.role` arrive spaced like `"Alpha Wolf"`) is absorbed by `stemFor`'s space-strip + wolf-substring fallback, so no behavior depends on confirming it.
