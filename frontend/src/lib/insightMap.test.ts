import { describe, it, expect } from "vitest";
import {
  mapBeliefEvent,
  mapVoteEvent,
  rosterToInsightPlayers,
  mapSpeakerSeat,
  selectExposureRow,
  mapWolfCampEvent,
} from "./insightMap";

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

describe("mapSpeakerSeat", () => {
  const snaps = [
    { observer_id: "player_1", observer_seat: 1, first_order: [] },
    { observer_id: "player_3", observer_seat: 3, first_order: [] },
  ];
  it("returns the speaker's seat on after_speech", () => {
    expect(mapSpeakerSeat({ speaker_id: "player_3", snapshots: snaps })).toBe(3);
  });
  it("returns null when speaker_id is empty (initial anchor)", () => {
    expect(mapSpeakerSeat({ speaker_id: "", snapshots: snaps })).toBeNull();
  });
  it("returns null when speaker not among snapshots, or data missing", () => {
    expect(mapSpeakerSeat({ speaker_id: "player_9", snapshots: snaps })).toBeNull();
    expect(mapSpeakerSeat({})).toBeNull();
    expect(mapSpeakerSeat(undefined)).toBeNull();
  });
});

describe("selectExposureRow", () => {
  const beliefs = [
    {
      observer_seat: 3,
      second_order: [
        { observer_seat: 2, suspects_me_as_wolf: 0.3, reason: "b", note: null },
        { observer_seat: 5, suspects_me_as_wolf: 0.7, reason: "a", note: null },
      ],
    },
  ] as any;
  it("returns the speaker's B2 sorted by suspicion desc", () => {
    expect(selectExposureRow(beliefs, 3)).toEqual([
      { observer_seat: 5, suspicion: 0.7, reason: "a" },
      { observer_seat: 2, suspicion: 0.3, reason: "b" },
    ]);
  });
  it("returns [] for null speaker / missing observer / null beliefs", () => {
    expect(selectExposureRow(beliefs, null)).toEqual([]);
    expect(selectExposureRow(beliefs, 9)).toEqual([]);
    expect(selectExposureRow(null, 3)).toEqual([]);
  });
});

describe("mapWolfCampEvent", () => {
  it("keys per-wolf records by owner_seat", () => {
    const data = {
      round: 2,
      minds: [
        { schema: "wolf_camp_mind_v2", owner_seat: 3, round: 2, contributor_seat: 3, god_role_intel: {}, exposure_radar: {} },
        { schema: "wolf_camp_mind_v2", owner_seat: 4, round: 2, contributor_seat: 4, god_role_intel: {}, exposure_radar: {} },
      ],
    };
    const out = mapWolfCampEvent(data);
    expect(Object.keys(out).sort()).toEqual(["3", "4"]);
    expect(out[3].owner_seat).toBe(3);
  });

  it("returns {} for missing / malformed payloads", () => {
    expect(mapWolfCampEvent(null)).toEqual({});
    expect(mapWolfCampEvent({})).toEqual({});
    expect(mapWolfCampEvent({ minds: "nope" })).toEqual({});
    expect(mapWolfCampEvent({ minds: [{ god_role_intel: {} }] })).toEqual({});
  });
});
