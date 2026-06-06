import { describe, it, expect } from "vitest";
import {
  mapRunInfo,
  mapTimeline,
  mapMvpRanking,
  mapTurningPoints,
  mapReplayPage,
} from "./replayMap";
import type {
  BackendRunDetail,
  BackendReplayEventItem,
  BackendMvpRankItem,
  BackendReplayPageData,
} from "../api/types";

function run(overrides: Partial<BackendRunDetail> = {}): BackendRunDetail {
  return {
    run_id: "6p-deepseek-20260606-122318",
    source: "runs",
    path: "/x",
    created_at: "2026-06-06T12:23:18",
    player_count: 6,
    winner_camp: "villager",
    has_post_game: true,
    has_replay: true,
    roster: [],
    ...overrides,
  };
}

function ev(overrides: Partial<BackendReplayEventItem> = {}): BackendReplayEventItem {
  return {
    index: 0,
    event_type: "message",
    round_number: 1,
    phase: "night",
    message: "msg",
    data: {},
    ...overrides,
  };
}

describe("mapRunInfo", () => {
  it("maps id<-run_id, date<-created_at, initial_players<-player_count", () => {
    const info = mapRunInfo(run());
    expect(info.id).toBe("6p-deepseek-20260606-122318");
    expect(info.date).toBe("2026-06-06T12:23:18");
    expect(info.initial_players).toBe(6);
  });

  it("maps winner_camp werewolf->WOLVES and villager->VILLAGERS", () => {
    expect(mapRunInfo(run({ winner_camp: "werewolf" })).winner_camp).toBe("WOLVES");
    expect(mapRunInfo(run({ winner_camp: "villager" })).winner_camp).toBe("VILLAGERS");
  });

  it("defends against null/missing run with safe defaults", () => {
    const info = mapRunInfo(null);
    expect(info.id).toBe("");
    expect(info.initial_players).toBe(0);
    expect(info.winner_camp).toBe("VILLAGERS");
  });
});

describe("mapTimeline", () => {
  it("derives id<-String(index), day<-round_number", () => {
    const out = mapTimeline([ev({ index: 3, round_number: 2 })]);
    expect(out[0].id).toBe("3");
    expect(out[0].day).toBe(2);
  });

  it("isNight is true for night phases (case-insensitive) and false for day phases", () => {
    expect(mapTimeline([ev({ phase: "night" })])[0].isNight).toBe(true);
    expect(mapTimeline([ev({ phase: "NIGHT_WOLF" })])[0].isNight).toBe(true);
    expect(mapTimeline([ev({ phase: "day_discussion" })])[0].isNight).toBe(false);
  });

  it("derives event type from event_type", () => {
    const types = (et: string) => mapTimeline([ev({ event_type: et })])[0].type;
    expect(types("player_speech")).toBe("speech");
    expect(types("player_discussion")).toBe("speech");
    expect(types("werewolf_killed")).toBe("kill");
    expect(types("player_died")).toBe("kill");
    expect(types("player_eliminated")).toBe("kill");
    expect(types("witch_poison_used")).toBe("kill");
    expect(types("seer_checked")).toBe("check");
    expect(types("witch_saved")).toBe("save");
    expect(types("vote_cast")).toBe("vote");
    expect(types("vote_result")).toBe("vote");
    expect(types("game_started")).toBe("system");
    expect(types("phase_changed")).toBe("system");
  });

  it("FILTERS OUT belief_snapshot and vote_intention_snapshot (god-injected) events", () => {
    const out = mapTimeline([
      ev({ index: 0, event_type: "player_speech" }),
      ev({ index: 1, event_type: "belief_snapshot" }),
      ev({ index: 2, event_type: "vote_intention_snapshot" }),
      ev({ index: 3, event_type: "vote_cast" }),
    ]);
    expect(out).toHaveLength(2);
    expect(out.map((e) => e.type)).toEqual(["speech", "vote"]);
  });

  it("carries the message as description and exposes playerId/targetId from data", () => {
    const out = mapTimeline([
      ev({
        event_type: "seer_checked",
        message: "🔮 预言家查验了 Player4: 狼人",
        data: { player_id: "player_6", target_id: "player_4", result: "werewolf" },
      }),
    ]);
    expect(out[0].description).toContain("预言家查验");
    expect(out[0].playerId).toBe("player_6");
    expect(out[0].targetId).toBe("player_4");
    expect(out[0].result).toBe("werewolf");
  });

  it("prefers data.speech for the speech message", () => {
    const out = mapTimeline([
      ev({
        event_type: "player_speech",
        message: "⚠️[兜底] Player1: 我推4号",
        data: { player_id: "player_1", speech: "我推4号" },
      }),
    ]);
    expect(out[0].message).toBe("我推4号");
    expect(out[0].playerId).toBe("player_1");
  });

  it("tolerates null/undefined input", () => {
    expect(mapTimeline(null)).toEqual([]);
    expect(mapTimeline(undefined)).toEqual([]);
  });
});

describe("mapMvpRanking", () => {
  function mvp(overrides: Partial<BackendMvpRankItem> = {}): BackendMvpRankItem {
    return {
      rank: 1,
      player_id: "player_5",
      player_name: "Player5",
      role_name: "Witch",
      total_score: 0.0,
      ai_model: "deepseek",
      ...overrides,
    };
  }

  it("maps playerId from int(player_id) stripping the prefix", () => {
    expect(mapMvpRanking([mvp({ player_id: "player_5" })])[0].playerId).toBe(5);
    expect(mapMvpRanking([mvp({ player_id: "12" })])[0].playerId).toBe(12);
  });

  it("sets isMvp only for rank === 1 and defaults contributionDesc to empty", () => {
    const out = mapMvpRanking([mvp({ rank: 1 }), mvp({ rank: 2, player_id: "player_2" })]);
    expect(out[0].isMvp).toBe(true);
    expect(out[1].isMvp).toBe(false);
    expect(out[0].contributionDesc).toBe("");
  });

  it("maps the remaining MvpRankItem fields (role/score/name)", () => {
    const out = mapMvpRanking([mvp({ role_name: "Witch", total_score: 0, player_name: "Player5" })]);
    expect(out[0].role).toBe("Witch");
    expect(out[0].score).toBe(0); // known backend bug: total_score is 0.0; filled in a later slice
    expect(out[0].playerName).toBe("Player5");
  });

  it("tolerates null/undefined input", () => {
    expect(mapMvpRanking(null)).toEqual([]);
    expect(mapMvpRanking(undefined)).toEqual([]);
  });
});

describe("mapTurningPoints", () => {
  it("maps a string[] into {day:0,title:line,desc:line}", () => {
    const out = mapTurningPoints(["首夜女巫救人", "首日放逐狼人"]);
    expect(out).toEqual([
      { day: 0, title: "首夜女巫救人", desc: "首夜女巫救人" },
      { day: 0, title: "首日放逐狼人", desc: "首日放逐狼人" },
    ]);
  });

  it("tolerates null/undefined input", () => {
    expect(mapTurningPoints(null)).toEqual([]);
    expect(mapTurningPoints(undefined)).toEqual([]);
  });
});

describe("mapReplayPage", () => {
  function page(overrides: Partial<BackendReplayPageData> = {}): BackendReplayPageData {
    return {
      run: run(),
      timeline: [ev({ index: 0, event_type: "player_speech" })],
      turning_points: ["x"],
      mvp_ranking: [
        { rank: 1, player_id: "player_5", player_name: "P5", total_score: 0, role_name: "Witch" },
      ],
      report_markdown: "# Report",
      coach_excerpt: "good game",
      ...overrides,
    };
  }

  it("composes run/timeline/turning_points/mvp_ranking", () => {
    const out = mapReplayPage(page());
    expect(out.run.id).toBe("6p-deepseek-20260606-122318");
    expect(out.timeline).toHaveLength(1);
    expect(out.turning_points[0].title).toBe("x");
    expect(out.mvp_ranking[0].isMvp).toBe(true);
    expect(out.report_markdown).toBe("# Report");
    expect(out.coach_excerpt).toBe("good game");
  });

  it("defaults the not-yet-mapped panels to empty collections", () => {
    const out = mapReplayPage(page());
    expect(out.scores).toEqual([]);
    expect(out.phase_summary).toEqual([]);
    expect(out.belief_snapshots).toEqual([]);
    expect(out.wolf_camp_snapshots).toEqual([]);
    expect(out.belief_heatmap).toEqual([]);
    expect(out.belief_matrix_anchors).toEqual([]);
    expect(out.vote_swing_summary).toEqual([]);
  });

  it("defaults null markdown/coach to empty strings and missing arrays to []", () => {
    const out = mapReplayPage({ run: run(), timeline: [] });
    expect(out.report_markdown).toBe("");
    expect(out.coach_excerpt).toBe("");
    expect(out.turning_points).toEqual([]);
    expect(out.mvp_ranking).toEqual([]);
    expect(out.timeline).toEqual([]);
  });

  it("tolerates null/undefined input", () => {
    const out = mapReplayPage(null);
    expect(out.timeline).toEqual([]);
    expect(out.run.winner_camp).toBe("VILLAGERS");
  });
});
