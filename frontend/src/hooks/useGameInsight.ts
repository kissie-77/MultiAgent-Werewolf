import { useState, useEffect } from "react";
import { BeliefSnapshot, VoteIntentionSnapshot } from "../api/insightTypes";

// Mock data as requested
const MOCK_BELIEFS: BeliefSnapshot[] = [
  {
    "round": 2, "phase": "day_discussion", "anchor": "after_speech:player_2", "observer_id": "player_2", "observer_seat": 2,
    "vote_intention": { "seat": 4, "reason": "狼在4/6，先推4回查6" },
    "first_order": [
      { "target_seat": 1, "wolf_probability": 0.0, "note": "金水", "reason": "昨夜验1号好人" },
      { "target_seat": 2, "wolf_probability": 0.0, "note": "本人（好人阵营）", "reason": null },
      { "target_seat": 4, "wolf_probability": 0.5, "reason": null, "note": null },
      { "target_seat": 6, "wolf_probability": 0.5, "reason": null, "note": null }
    ]
  },
  {
    "round": 2, "phase": "day_discussion", "anchor": "after_speech:player_2", "observer_id": "player_1", "observer_seat": 1,
    "vote_intention": { "seat": 4, "reason": "信预言家" },
    "first_order": [
      { "target_seat": 1, "wolf_probability": 0.0, "note": "本人（好人阵营）", "reason": null },
      { "target_seat": 2, "wolf_probability": 0.1, "reason": null, "note": null },
      { "target_seat": 4, "wolf_probability": 0.45, "reason": null, "note": null },
      { "target_seat": 6, "wolf_probability": 0.45, "reason": null, "note": null }
    ]
  },
  {
    "round": 2, "phase": "day_discussion", "anchor": "after_speech:player_2", "observer_id": "player_6", "observer_seat": 6,
    "vote_intention": { "seat": 2, "reason": "反咬预言家" },
    "first_order": [
      { "target_seat": 1, "wolf_probability": 0.3, "reason": null, "note": null },
      { "target_seat": 2, "wolf_probability": 0.6, "reason": "悍跳嫌疑", "note": null },
      { "target_seat": 4, "wolf_probability": 0.0, "note": "队友/保", "reason": null },
      { "target_seat": 6, "wolf_probability": 0.0, "note": "本人", "reason": null }
    ]
  }
];

const MOCK_VOTE_SNAPSHOT: VoteIntentionSnapshot = {
  "round_number": 2, "phase": "day_discussion", "speaker_id": "player_2", "speaker_name": "Player2",
  "public_speech": "1号金水，狼在4和6中，今天先出4号，跟票出4。", "swing_count": 2, "influence_score": 20,
  "before": {
    "player_1": { "player_id": "player_1", "seat": 0, "target_id": null, "target_name": null, "reason": "先观望" },
    "player_2": { "player_id": "player_2", "seat": 4, "target_id": "player_4", "target_name": "Player4", "reason": "推4" },
    "player_4": { "player_id": "player_4", "seat": 6, "target_id": "player_6", "target_name": "Player6", "reason": "推6" },
    "player_6": { "player_id": "player_6", "seat": 0, "target_id": null, "target_name": null, "reason": "观望" }
  },
  "after": {
    "player_1": { "player_id": "player_1", "seat": 4, "target_id": "player_4", "target_name": "Player4", "reason": "跟票4" },
    "player_2": { "player_id": "player_2", "seat": 4, "target_id": "player_4", "target_name": "Player4", "reason": "推4" },
    "player_4": { "player_id": "player_4", "seat": 6, "target_id": "player_6", "target_name": "Player6", "reason": "推6" },
    "player_6": { "player_id": "player_6", "seat": 2, "target_id": "player_2", "target_name": "Player2", "reason": "反咬" }
  },
  "swings": [
    { "player_id": "player_1", "player_name": "Player1", "from_seat": 0, "to_seat": 4, "to_target_name": "Player4" },
    { "player_id": "player_6", "player_name": "Player6", "from_seat": 0, "to_seat": 2, "to_target_name": "Player2" }
  ]
};

export const MOCK_PLAYERS = [
  { seat: 1, id: "player_1", name: "Player1", role: "Witch", camp: "villager", alive: true },
  { seat: 2, id: "player_2", name: "Player2", role: "Seer", camp: "villager", alive: true },
  { seat: 3, id: "player_3", name: "Player3", role: "Werewolf", camp: "werewolf", alive: false },
  { seat: 4, id: "player_4", name: "Player4", role: "Villager", camp: "villager", alive: true },
  { seat: 6, id: "player_6", name: "Player6", role: "Werewolf", camp: "werewolf", alive: true }
];

export function useGameInsight(runId: string | null) {
  const [beliefs, setBeliefs] = useState<BeliefSnapshot[] | null>(null);
  const [voteSnapshot, setVoteSnapshot] = useState<VoteIntentionSnapshot | null>(null);

  useEffect(() => {
    // In the future this will fetch from the real backend endpoint.
    // For now, we simulate a load of the mock data.
    const t = setTimeout(() => {
      setBeliefs(MOCK_BELIEFS);
      setVoteSnapshot(MOCK_VOTE_SNAPSHOT);
    }, 500);
    return () => clearTimeout(t);
  }, [runId]);

  return { beliefs, voteSnapshot, players: MOCK_PLAYERS };
}
