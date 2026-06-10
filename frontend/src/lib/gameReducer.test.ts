import { describe, it, expect } from "vitest";
import { initialSpectateState, reduceEvent } from "./gameReducer";

const snapshot = {
  event_type: "snapshot",
  phase: "night",
  round_number: 1,
  roster: [
    { seat: 1, name: "P1", role: "Seer", camp: "villager", is_alive: true },
    { seat: 2, name: "P2", role: "Werewolf", camp: "werewolf", is_alive: true },
  ],
};

describe("gameReducer", () => {
  it("builds players + phase from a god snapshot", () => {
    const s = reduceEvent(initialSpectateState(), snapshot as any);
    expect(s.players.map((p) => p.id)).toEqual([1, 2]);
    expect(s.players[0].role).toBe("Seer");
    expect(s.phase).toBe("NIGHT_WOLF");
    expect(s.dayNumber).toBe(1);
  });

  it("appends speech and sets current speaker", () => {
    let s = reduceEvent(initialSpectateState(), snapshot as any);
    s = reduceEvent(s, {
      event_type: "player_speech", round_number: 2, phase: "day_discussion",
      message: "我是预言家", data: { player_id: "player_1", reasoning: "因为..." },
    } as any);
    expect(s.phase).toBe("DAY_DEBATE");
    expect(s.currentSpeakerId).toBe(1);
    expect(s.speechLogs.at(-1)).toMatchObject({ playerId: 1, content: "我是预言家" });
  });

  it("marks a player dead on player_died", () => {
    let s = reduceEvent(initialSpectateState(), snapshot as any);
    s = reduceEvent(s, {
      event_type: "player_died", round_number: 2, phase: "night",
      message: "P2 倒下", data: { player_id: "player_2" },
    } as any);
    expect(s.players.find((p) => p.id === 2)!.isAlive).toBe(false);
  });

  it("ends the game on game_ended", () => {
    let s = reduceEvent(initialSpectateState(), snapshot as any);
    s = reduceEvent(s, {
      event_type: "game_ended", round_number: 3, phase: "ended",
      message: "狼人胜", data: { winner_camp: "werewolf" },
    } as any);
    expect(s.phase).toBe("GAME_OVER");
    expect(s.winner).toBe("WOLVES");
  });
});

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

  it("strips other players' reasoning in seat view", () => {
    let s = reduceEvent(initialSpectateState(), {
      event_type: "snapshot",
      selfSeat: 1,
      roster: [
        { seat: 1, name: "P1", role: "Seer", is_alive: true },
        { seat: 2, name: "P2", role: null, is_alive: true },
      ],
    } as any);
    s = reduceEvent(s, {
      event_type: "player_speech",
      round_number: 1,
      phase: "day_discussion",
      message: "hi",
      selfSeat: 1,
      data: { player_id: "player_2", reasoning: "wolf plan", content: "hi" },
    } as any);
    expect(s.speechLogs.at(-1)?.reasoning).toBeUndefined();
  });
});

describe("human seer check annotates the target's seat card", () => {
  const seerSeatSnap = {
    event_type: "snapshot",
    selfSeat: 1,
    roster: [
      { seat: 1, name: "P1", role: "Seer", is_alive: true },
      { seat: 2, name: "P2", role: null, is_alive: true },
      { seat: 3, name: "P3", role: null, is_alive: true },
    ],
  };

  it("writes the wolf verdict into the checked player's statusNotes (seat view)", () => {
    let s = reduceEvent(initialSpectateState(), seerSeatSnap as any);
    s = reduceEvent(s, {
      event_type: "seer_checked", round_number: 1, phase: "night", selfSeat: 1,
      data: { player_id: "player_1", target_id: "player_2", result: "werewolf" },
    } as any);
    const target = s.players.find((p) => p.id === 2)!;
    expect(target.statusNotes).toContain("查验");
    expect(target.statusNotes).toContain("狼人");
    // The seer learns the camp, not the exact card — role stays redacted.
    expect(target.role).toBe("");
  });

  it("maps a human/villager result to 好人", () => {
    let s = reduceEvent(initialSpectateState(), seerSeatSnap as any);
    s = reduceEvent(s, {
      event_type: "seer_checked", round_number: 2, phase: "night", selfSeat: 1,
      data: { player_id: "player_1", target_id: "player_3", result: "villager" },
    } as any);
    expect(s.players.find((p) => p.id === 3)!.statusNotes).toContain("好人");
  });

  it("leaves statusNotes empty in spectate/god view (no selfSeat)", () => {
    let s = reduceEvent(initialSpectateState(), snapshot as any);
    s = reduceEvent(s, {
      event_type: "seer_checked", round_number: 1, phase: "night",
      data: { player_id: "player_1", target_id: "player_2", result: "werewolf" },
    } as any);
    expect(s.players.find((p) => p.id === 2)!.statusNotes).toBe("");
  });
});

describe("seat-view night thinking is anonymized (no identity leak)", () => {
  const seatSnap = {
    event_type: "snapshot",
    selfSeat: 1,
    roster: [
      { seat: 1, name: "P1", role: "Villager", is_alive: true },
      { seat: 4, name: "Player4", role: null, is_alive: true },
    ],
  };

  it("withholds another seat's identity for night thinking (seat view)", () => {
    let s = reduceEvent(initialSpectateState(), seatSnap as any);
    s = reduceEvent(s, {
      event_type: "actor_thinking",
      phase: "night",
      selfSeat: 1,
      data: { player_id: "player_4", player_name: "Player4", context: "werewolf_chat" },
    } as any);
    // seat=null is the "identity withheld" marker honored by dock / 3D ring / header
    expect(s.liveCue.thinking?.seat).toBeNull();
    expect(s.liveCue.thinking?.playerName ?? "").not.toContain("Player4");
    expect(s.liveCue.thinking?.role).toBe("");
  });

  it("keeps the actor identity for daytime thinking (about-to-speak is public)", () => {
    let s = reduceEvent(initialSpectateState(), seatSnap as any);
    s = reduceEvent(s, {
      event_type: "actor_thinking",
      phase: "day_discussion",
      selfSeat: 1,
      data: { player_id: "player_4", player_name: "Player4", context: "day_speech" },
    } as any);
    expect(s.liveCue.thinking?.seat).toBe(4);
  });

  it("keeps own night thinking identifiable (it's the human themselves)", () => {
    let s = reduceEvent(initialSpectateState(), seatSnap as any);
    s = reduceEvent(s, {
      event_type: "actor_thinking",
      phase: "night",
      selfSeat: 1,
      data: { player_id: "player_1", player_name: "P1", context: "night_skill" },
    } as any);
    expect(s.liveCue.thinking?.seat).toBe(1);
  });

  it("keeps full identity in pure-LLM/god view (no selfSeat) — LLM battle unchanged", () => {
    let s = reduceEvent(initialSpectateState(), {
      event_type: "snapshot",
      roster: [{ seat: 4, name: "Player4", role: "Werewolf", is_alive: true }],
    } as any);
    s = reduceEvent(s, {
      event_type: "actor_thinking",
      phase: "night",
      data: { player_id: "player_4", player_name: "Player4", role: "Werewolf", context: "werewolf_chat" },
    } as any);
    // Spectate is untouched: seat, name and role-for-flavor all preserved.
    expect(s.liveCue.thinking?.seat).toBe(4);
    expect(s.liveCue.thinking?.playerName).toBe("Player4");
    expect(s.liveCue.thinking?.role).toBe("Werewolf");
  });
});
