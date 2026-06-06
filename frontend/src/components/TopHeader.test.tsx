import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import TopHeader from "./TopHeader";
import { useGameStore } from "../store";
import { GamePhase, GameStateResponse } from "../types";

function setState(partial: Partial<GameStateResponse>) {
  const base: GameStateResponse = {
    status: "running", error: null, play_state: "playing", speed: 1,
    phase: GamePhase.day_discussion, sub_phase: null, round: 1, current_actor_seat: null,
    winner: null, sheriff_seat: null, alive_count: 6, dead_count: 0,
    last_night: null, votes: null, cursor: 0, players: [],
  };
  useGameStore.setState({ gameState: { ...base, ...partial }, status: "running" });
}

afterEach(() => useGameStore.getState().exitToSetup());

describe("TopHeader", () => {
  it("shows the night title when phase is night (no .startsWith match)", () => {
    setState({ phase: GamePhase.night, round: 2 });
    render(<TopHeader />);
    expect(screen.getByText(/第 2 晚/)).toBeInTheDocument();
  });

  it("shows the day-discussion phase label and round", () => {
    setState({ phase: GamePhase.day_discussion, round: 3 });
    render(<TopHeader />);
    expect(screen.getByText(/第 3 日/)).toBeInTheDocument();
    expect(screen.getByText("白天讨论")).toBeInTheDocument();
  });

  it("renders the sub-phase highlight when present and renders no fake countdown", () => {
    setState({ phase: GamePhase.night, sub_phase: "werewolf_chat", round: 1 });
    render(<TopHeader />);
    expect(screen.getByText("狼人夜聊中")).toBeInTheDocument();
    // The fake "00:30" countdown must be gone.
    expect(screen.queryByText(/00:\d\d/)).not.toBeInTheDocument();
  });
});
