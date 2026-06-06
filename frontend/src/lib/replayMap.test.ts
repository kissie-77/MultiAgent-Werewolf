import { describe, it, expect } from "vitest";
import {
  mapRunInfo,
  mapTimeline,
  mapMvpRanking,
  mapTurningPoints,
  mapReplayPage,
  mapPlayerScores,
  mapVoteSwing,
  mapBeliefAnchors,
  mapBeliefColumns,
  mapWolfCampSnapshots,
} from "./replayMap";
import type {
  BackendRunDetail,
  BackendReplayEventItem,
  BackendMvpRankItem,
  BackendReplayPageData,
  BackendScoreBlock,
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
    expect(out[0].score).toBe(0); // known backend bug: total_score is 0.0; falls back when no mvp block
    expect(out[0].playerName).toBe("Player5");
  });

  it("uses mvp_total from the mvp score players (fixes the 0.0 total_score bug) when provided", () => {
    const players = [
      { player_id: "player_5", mvp_total: 87.5 },
      { player_id: "player_2", mvp_total: 64 },
    ];
    const out = mapMvpRanking(
      [mvp({ player_id: "player_5", total_score: 0 }), mvp({ rank: 2, player_id: "player_2", total_score: 0 })],
      players,
    );
    expect(out[0].score).toBe(87.5);
    expect(out[1].score).toBe(64);
  });

  it("falls back to total_score when the player has no mvp_total entry", () => {
    const out = mapMvpRanking([mvp({ player_id: "player_9", total_score: 3.3 })], [
      { player_id: "player_5", mvp_total: 87.5 },
    ]);
    expect(out[0].score).toBe(3.3);
  });

  it("tolerates null/undefined input", () => {
    expect(mapMvpRanking(null)).toEqual([]);
    expect(mapMvpRanking(undefined)).toEqual([]);
  });
});

// --- Slice C: scores / vote-swing / belief ------------------------------

function mvpScoreBlock(overrides: any = {}): BackendScoreBlock {
  return {
    kind: "mvp",
    title: "MVP 评分",
    payload: {
      data: {
        schema: "mvp_scores_v2",
        players: [
          {
            player_id: "player_5",
            player_name: "Player5",
            role_name: "Witch",
            camp: "villager",
            mvp_total: 87.5,
            breakdown_norm: { persuasion: 12, strategy: 8, outcome: 20, wolf_night: 0 },
            rank: 1,
          },
          {
            player_id: "player_2",
            player_name: "Player2",
            role_name: "Werewolf",
            camp: "werewolf",
            mvp_total: 64,
            breakdown_norm: { persuasion: 5, strategy: 10, outcome: 3, wolf_night: 15 },
            rank: 2,
          },
        ],
        ...overrides,
      },
    },
  };
}

function swingScoreBlock(overrides: any = {}): BackendScoreBlock {
  return {
    kind: "swing",
    title: "投票摇摆",
    payload: {
      data: {
        schema: "vote_swing_v1",
        speeches: [
          {
            speaker_id: "player_2",
            speaker_name: "Player2",
            round_number: 1,
            phase: "day_discussion",
            channel: "public",
            public_speech: "出五号",
            swing_count: 1,
            influence_score: 10,
            before_summary: "before",
            after_summary: "after",
            swings: [
              {
                player_id: "player_1",
                player_name: "A",
                from_seat: 0,
                to_seat: 5,
                from_target_name: "B",
                to_target_name: "C",
              },
            ],
          },
        ],
        ...overrides,
      },
    },
  };
}

function beliefRow(overrides: any = {}): any {
  return {
    round: 1,
    phase: "day_discussion",
    anchor: "initial",
    observer_id: "player_1",
    observer_seat: 1,
    vote_intention: { seat: 4, reason: "r" },
    first_order: [{ target_seat: 2, wolf_probability: 0.5, reason: "sus", note: null }],
    ...overrides,
  };
}

describe("mapPlayerScores", () => {
  it("maps breakdown_norm dims, mvp_total and the roster alive join", () => {
    const backend = {
      run: run({
        roster: [
          { player_id: "player_5", player_name: "Player5", is_alive: false },
          { player_id: "player_2", player_name: "Player2", is_alive: true },
        ] as any,
      }),
      scores: [mvpScoreBlock()],
    };
    const out = mapPlayerScores(backend);
    expect(out).toHaveLength(2);
    const p5 = out[0];
    expect(p5.playerId).toBe(5);
    expect(p5.playerName).toBe("Player5");
    expect(p5.role).toBe("Witch");
    expect(p5.isAlive).toBe(false);
    expect(p5.logicSpeechScore).toBe(12); // persuasion
    expect(p5.cooperationRate).toBe(8); // strategy
    expect(p5.gameSurvivalScore).toBe(20); // outcome
    expect(p5.deceptionMisleaderScore).toBe(0); // wolf_night
    expect(p5.totalScore).toBe(87.5); // mvp_total
  });

  it("defaults isAlive to true when the player is not in the roster", () => {
    const backend = { run: run({ roster: [] }), scores: [mvpScoreBlock()] };
    const out = mapPlayerScores(backend);
    expect(out[0].isAlive).toBe(true);
  });

  it("returns [] when there is no mvp score block", () => {
    expect(mapPlayerScores({ run: run(), scores: [swingScoreBlock()] })).toEqual([]);
    expect(mapPlayerScores({ run: run(), scores: [] })).toEqual([]);
  });

  it("tolerates null/undefined input", () => {
    expect(mapPlayerScores(null)).toEqual([]);
    expect(mapPlayerScores(undefined)).toEqual([]);
  });
});

describe("mapVoteSwing", () => {
  it("maps id/round/edges and joins speaker role+camp from the mvp players", () => {
    const out = mapVoteSwing({ scores: [mvpScoreBlock(), swingScoreBlock()] });
    expect(out).toHaveLength(1);
    const s = out[0];
    expect(s.id).toBe("player_2-1");
    expect(s.round).toBe(1);
    expect(s.speaker_id).toBe("player_2");
    expect(s.speaker_role).toBe("Werewolf"); // joined from mvp players
    expect(s.speaker_camp).toBe("werewolf");
    expect(s.influence_score).toBe(10);
    expect(s.swing_count).toBe(1);
    expect(s.before_summary).toBe("before");
    expect(s.after_summary).toBe("after");
    expect(s.public_speech).toBe("出五号");
    expect(s.swings).toEqual([{ voter_id: "player_1", from_target: "B", to_target: "C" }]);
  });

  it("defaults speaker role/camp to empty string when no mvp join is available", () => {
    const out = mapVoteSwing({ scores: [swingScoreBlock()] });
    expect(out[0].speaker_role).toBe("");
    expect(out[0].speaker_camp).toBe("");
  });

  it("returns [] when there is no swing score block", () => {
    expect(mapVoteSwing({ scores: [mvpScoreBlock()] })).toEqual([]);
    expect(mapVoteSwing({ scores: [] })).toEqual([]);
  });

  it("tolerates null/undefined input", () => {
    expect(mapVoteSwing(null)).toEqual([]);
    expect(mapVoteSwing(undefined)).toEqual([]);
  });
});

describe("mapBeliefAnchors", () => {
  it("groups rows by anchor and rebuilds observers/targets with P{n} seats", () => {
    const rows = [
      beliefRow({ anchor: "initial", observer_seat: 1 }),
      beliefRow({ anchor: "initial", observer_seat: 2, first_order: [{ target_seat: 1, wolf_probability: 0.8, reason: null, note: "已死" }] }),
      beliefRow({ anchor: "after_speech", observer_seat: 1 }),
    ];
    const out = mapBeliefAnchors(rows);
    expect(out).toHaveLength(2);
    const initial = out.find((a) => a.anchor_id === "initial")!;
    expect(initial.round).toBe(1);
    expect(initial.observers.map((o) => o.observer_id)).toEqual(["P1", "P2"]);
    const p1 = initial.observers.find((o) => o.observer_id === "P1")!;
    expect(p1.targets[0].target_seat).toBe("P2");
    expect(p1.targets[0].wolf_probability).toBe(0.5); // kept 0..1
    expect(p1.targets[0].reason).toBe("sus");
    const p2 = initial.observers.find((o) => o.observer_id === "P2")!;
    expect(p2.targets[0].note).toBe("已死");
  });

  it("tolerates null/undefined input", () => {
    expect(mapBeliefAnchors(null)).toEqual([]);
    expect(mapBeliefAnchors(undefined)).toEqual([]);
  });
});

describe("mapBeliefColumns", () => {
  it("groups by day(round), builds playerBeliefs per observer and scales prob to 0..100", () => {
    const rows = [
      beliefRow({ round: 1, observer_seat: 1, first_order: [{ target_seat: 2, wolf_probability: 0.5, reason: null, note: null }] }),
      beliefRow({ round: 1, observer_seat: 2, first_order: [{ target_seat: 1, wolf_probability: 0.8, reason: null, note: null }] }),
      beliefRow({ round: 2, observer_seat: 1, first_order: [{ target_seat: 3, wolf_probability: 1.0, reason: null, note: null }] }),
    ];
    const out = mapBeliefColumns(rows);
    const d1 = out.find((d) => d.day === 1)!;
    expect(d1.playerBeliefs).toHaveLength(2);
    const obs1 = d1.playerBeliefs.find((p) => p.playerId === 1)!;
    expect(obs1.playerName).toBe("P1");
    expect(obs1.targetBeliefs[0]).toEqual({
      targetPlayerId: 2,
      targetPlayerName: "P2",
      wolfProbability: 50,
    });
    const obs2 = d1.playerBeliefs.find((p) => p.playerId === 2)!;
    expect(obs2.targetBeliefs[0].wolfProbability).toBe(80);
    const d2 = out.find((d) => d.day === 2)!;
    expect(d2.playerBeliefs).toHaveLength(1);
  });

  it("keeps the last anchor per observer within a day", () => {
    const rows = [
      beliefRow({ round: 1, anchor: "initial", observer_seat: 1, first_order: [{ target_seat: 2, wolf_probability: 0.3, reason: null, note: null }] }),
      beliefRow({ round: 1, anchor: "after_speech", observer_seat: 1, first_order: [{ target_seat: 2, wolf_probability: 0.9, reason: null, note: null }] }),
    ];
    const out = mapBeliefColumns(rows);
    const d1 = out.find((d) => d.day === 1)!;
    expect(d1.playerBeliefs).toHaveLength(1);
    expect(d1.playerBeliefs[0].targetBeliefs[0].wolfProbability).toBe(90);
  });

  it("tolerates null/undefined input", () => {
    expect(mapBeliefColumns(null)).toEqual([]);
    expect(mapBeliefColumns(undefined)).toEqual([]);
  });
});

describe("mapWolfCampSnapshots", () => {
  it("maps wolf_camp_mind rows into replay wolf camp snapshots", () => {
    const out = mapWolfCampSnapshots([
      {
        schema: "wolf_camp_mind_v1",
        round: 1,
        contributor_seat: 6,
        god_role_intel: {
          "5": {
            target_seat: 5,
            role_distribution: { Seer: 0.8, Witch: 0.2, Guard: 0, Hunter: 0, Villager: 0 },
            threat_score: 0.42,
            priority: "watch",
            evidence: ["5号被救，疑似神职"],
          },
        },
        exposure_radar: {
          "2": {
            wolf_seat: 2,
            overall_exposure: 0.5,
            suggested_stance: "counter",
            top_suspectors: [{ seat: 4, suspicion: 0.5 }],
          },
          "6": {
            wolf_seat: 6,
            overall_exposure: 0,
            suggested_stance: "hide",
            top_suspectors: [],
          },
        },
      },
    ]);
    expect(out).toHaveLength(1);
    expect(out[0].day).toBe(1);
    expect(out[0].targetSelectionId).toBe(5);
    expect(out[0].targetSelectionName).toBe("P5");
    expect(out[0].campStrategy).toContain("贡献者 P6");
    expect(out[0].campStrategy).toContain("P5 威胁 0.42");
    expect(out[0].campStrategy).toContain("P2 暴露 0.50");
    expect(out[0].wolfVotes).toEqual([
      { wolfPlayerId: 2, wolfPlayerName: "P2", votedForId: 5, votedForName: "P5" },
      { wolfPlayerId: 6, wolfPlayerName: "P6", votedForId: 5, votedForName: "P5" },
    ]);
  });

  it("tolerates missing wolf camp rows", () => {
    expect(mapWolfCampSnapshots()).toEqual([]);
    expect(mapWolfCampSnapshots(null)).toEqual([]);
  });
});

describe("mapReplayPage (Slice C enriched panels)", () => {
  it("composes scores, vote_swing_summary and belief panels from the backend blocks", () => {
    const out = mapReplayPage({
      run: run({
        roster: [{ player_id: "player_5", player_name: "Player5", is_alive: true }] as any,
      }),
      timeline: [],
      mvp_ranking: [
        { rank: 1, player_id: "player_5", player_name: "Player5", total_score: 0, role_name: "Witch" },
      ],
      scores: [mvpScoreBlock(), swingScoreBlock()],
      belief_snapshots: [beliefRow()],
      wolf_camp_snapshots: [
        {
          round: 1,
          contributor_seat: 2,
          god_role_intel: {},
          exposure_radar: {
            "2": { wolf_seat: 2, overall_exposure: 0, suggested_stance: "hide", top_suspectors: [] },
          },
        },
      ],
    } as Partial<BackendReplayPageData>);

    expect(out.scores).toHaveLength(2);
    expect(out.scores[0].totalScore).toBe(87.5);
    expect(out.vote_swing_summary).toHaveLength(1);
    expect(out.belief_matrix_anchors).toHaveLength(1);
    expect(out.belief_snapshots).toHaveLength(1);
    expect(out.wolf_camp_snapshots).toHaveLength(1);
    // mvp_ranking.score must now read mvp_total (0.0 bug fixed)
    expect(out.mvp_ranking[0].score).toBe(87.5);
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
