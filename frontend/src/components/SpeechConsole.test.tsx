import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import SpeechConsole from "./SpeechConsole";
import { useGameStore } from "../store";
import { GamePhase, GameStateResponse, RenderLog } from "../types";

function withLogs(logs: RenderLog[], state?: Partial<GameStateResponse>) {
  const base: GameStateResponse = {
    status: "running", error: null, play_state: "playing", speed: 1,
    phase: GamePhase.night, sub_phase: null, round: 1, current_actor_seat: null,
    winner: null, sheriff_seat: null, alive_count: 6, dead_count: 0,
    last_night: null, votes: null, cursor: 0, players: [],
  };
  useGameStore.setState({ logs, gameState: { ...base, ...state } });
}

afterEach(() => useGameStore.getState().exitToSetup());

describe("SpeechConsole structured rendering", () => {
  it("renders a death row distinctly from speech", () => {
    withLogs([{ seq: 1, kind: "death", round: 1, speakerSeat: 7, speakerName: "", text: "出局：7号（wolf_kill）", visibility: "public" }]);
    render(<SpeechConsole />);
    expect(screen.getByText("出局：7号（wolf_kill）")).toBeInTheDocument();
  });

  it("renders a skill row", () => {
    withLogs([{ seq: 2, kind: "skill", round: 1, speakerSeat: 1, speakerName: "", text: "技能：seer_check（1号 → 3号）", visibility: "god" }]);
    render(<SpeechConsole />);
    expect(screen.getByText("技能：seer_check（1号 → 3号）")).toBeInTheDocument();
  });

  it("shows the sub-phase highlight banner", () => {
    withLogs([], { sub_phase: "witch_decide" });
    render(<SpeechConsole />);
    expect(screen.getByText("女巫决策中")).toBeInTheDocument();
  });
});
