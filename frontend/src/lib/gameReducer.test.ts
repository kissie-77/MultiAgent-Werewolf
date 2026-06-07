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

  it("prefers data.speech over formatted message for speech logs", () => {
    let s = reduceEvent(initialSpectateState(), snapshot as any);
    s = reduceEvent(s, {
      event_type: "player_speech", round_number: 2, phase: "day_discussion",
      message: "Player1: 我是预言家", data: { player_id: "player_1", speech: "我是预言家" },
    } as any);
    expect(s.speechLogs.at(-1)?.content).toBe("我是预言家");
  });

  it("builds players from role_acting when snapshot is absent", () => {
    const s = reduceEvent(initialSpectateState(), {
      event_type: "role_acting", round_number: 1, phase: "night",
      data: { player_id: "player_3", player_name: "C", role: "Witch" },
    } as any);
    expect(s.players).toHaveLength(1);
    expect(s.players[0]).toMatchObject({ id: 3, role: "Witch", name: "C" });
  });

  it("maps phase_changed.data.phase into game phase", () => {
    const s = reduceEvent(initialSpectateState(), {
      event_type: "phase_changed",
      round_number: 1,
      phase: "night",
      data: { phase: "day_discussion" },
    } as any);
    expect(s.phase).toBe("DAY_DEBATE");
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

  it("sets thinking cue on actor_thinking and clears on speech", () => {
    let s = reduceEvent(initialSpectateState(), snapshot as any);
    s = reduceEvent(s, {
      event_type: "actor_thinking",
      round_number: 2,
      phase: "day_discussion",
      data: {
        player_id: "player_2",
        player_name: "P2",
        role: "Werewolf",
        context: "day_speech",
      },
    } as any);
    expect(s.liveCue.thinking).toMatchObject({
      seat: 2,
      playerName: "P2",
      context: "day_speech",
    });
    expect(s.currentSpeakerId).toBeNull();

    s = reduceEvent(s, {
      event_type: "player_speech",
      round_number: 2,
      phase: "day_discussion",
      data: { player_id: "player_2", player_name: "P2", speech: "过" },
    } as any);
    expect(s.liveCue.thinking).toBeNull();
    expect(s.currentSpeakerId).toBe(2);
  });

  it("handles sheriff candidate speech and campaign stage", () => {
    let s = reduceEvent(initialSpectateState(), snapshot as any);
    s = reduceEvent(s, {
      event_type: "sheriff_campaign_started",
      round_number: 1,
      phase: "sheriff_election",
      message: "警长竞选开始",
    } as any);
    expect(s.phase).toBe("DAY_SHERIFF_RUN");
    expect(s.liveCue.sheriffStage).toBe("campaign");

    s = reduceEvent(s, {
      event_type: "actor_thinking",
      phase: "sheriff_election",
      data: {
        player_id: "player_1",
        player_name: "P1",
        role: "Seer",
        context: "sheriff_speech",
      },
    } as any);
    expect(s.liveCue.thinking?.context).toBe("sheriff_speech");

    s = reduceEvent(s, {
      event_type: "sheriff_candidate_speech",
      phase: "sheriff_election",
      data: { player_id: "player_1", player_name: "P1", role: "Seer", speech: "我上警" },
    } as any);
    expect(s.liveCue.thinking).toBeNull();
    expect(s.speechLogs.at(-1)?.speechContext).toBe("sheriff");
  });

  it("tracks night sub_phase and skill placeholder", () => {
    let s = reduceEvent(initialSpectateState(), snapshot as any);
    s = reduceEvent(s, {
      event_type: "sub_phase",
      phase: "night",
      data: { name: "witch_decide" },
    } as any);
    expect(s.liveCue.nightSubPhase).toBe("witch_decide");
    expect(s.phase).toBe("NIGHT_WITCH");

    s = reduceEvent(s, {
      event_type: "role_acting",
      phase: "night",
      data: {
        player_id: "player_4",
        player_name: "Witch",
        role: "Witch",
        context: "night_skill",
        sub_phase: "witch_decide",
      },
    } as any);
    expect(s.liveCue.nightSkill).toMatchObject({
      seat: 4,
      role: "Witch",
      subPhase: "witch_decide",
    });
  });
});
