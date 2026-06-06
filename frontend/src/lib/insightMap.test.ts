import { describe, it, expect } from "vitest";
import { mapBeliefEvent, mapVoteEvent, rosterToInsightPlayers } from "./insightMap";

describe("insightMap", () => {
  it("mapBeliefEvent returns the snapshots array (already BeliefSnapshot-shaped)", () => {
    const data = {
      round: 2, phase: "day_discussion", anchor: "after_speech:player_2",
      snapshots: [
        { round: 2, phase: "day_discussion", anchor: "x", observer_id: "player_1", observer_seat: 1,
          vote_intention: { seat: 4, reason: "r" }, first_order: [{ target_seat: 2, wolf_probability: 0.5, reason: null, note: null }] },
      ],
    };
    const out = mapBeliefEvent(data);
    expect(out).toHaveLength(1);
    expect(out[0].observer_seat).toBe(1);
    expect(out[0].first_order[0].wolf_probability).toBe(0.5);
  });

  it("mapBeliefEvent tolerates missing snapshots", () => {
    expect(mapBeliefEvent({})).toEqual([]);
    expect(mapBeliefEvent(undefined)).toEqual([]);
  });

  it("mapVoteEvent defaults influence_score and swing_count", () => {
    const v = mapVoteEvent({
      round_number: 2, phase: "day_discussion", speaker_id: "player_2", speaker_name: "P2",
      public_speech: "推4", before: {}, after: {}, swings: [{ player_id: "player_1" }],
    });
    expect(v.swing_count).toBe(1);
    expect(typeof v.influence_score).toBe("number");
    expect(v.speaker_name).toBe("P2");
  });

  it("rosterToInsightPlayers merges live alive status over roster", () => {
    const roster = [
      { seat: 1, name: "P1", role: "Seer", camp: "villager", is_alive: true },
      { seat: 2, name: "P2", role: "Werewolf", camp: "werewolf", is_alive: true },
    ];
    const players = rosterToInsightPlayers(roster, { 2: false });
    expect(players[0]).toMatchObject({ seat: 1, id: "player_1", camp: "villager", alive: true });
    expect(players[1].alive).toBe(false); // live override
  });

  it("rosterToInsightPlayers tolerates null roster", () => {
    expect(rosterToInsightPlayers(null, {})).toEqual([]);
  });
});
