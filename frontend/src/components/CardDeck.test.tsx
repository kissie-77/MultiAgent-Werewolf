import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import CardDeck from "./CardDeck";
import { useGameStore } from "../store";
import { GamePhase, GameStateResponse } from "../types";

function setState(partial: Partial<GameStateResponse>, revealView: "god" | "suspense" = "suspense") {
  const base: GameStateResponse = {
    status: "running", error: null, play_state: "playing", speed: 1,
    phase: GamePhase.night, sub_phase: null, round: 1, current_actor_seat: null,
    winner: null, sheriff_seat: null, alive_count: 1, dead_count: 0,
    last_night: null, votes: null, cursor: 0,
    players: [{ seat: 1, name: "Alice", role: "狼人", camp: "wolf", is_alive: true, is_sheriff: false, model: "deepseek-chat", status_flags: ["alive"] }],
  };
  useGameStore.setState({ gameState: { ...base, ...partial }, revealView });
}

afterEach(() => useGameStore.getState().exitToSetup());

describe("CardDeck reveal", () => {
  it("hides role in suspense mode mid-game", () => {
    setState({ phase: GamePhase.night });
    render(<CardDeck />);
    expect(screen.getByText("未知秘匿")).toBeInTheDocument();
    expect(screen.queryByText("狼人")).not.toBeInTheDocument();
  });

  it("reveals role when phase === 'ended' (no snapshot.winner)", () => {
    setState({ phase: GamePhase.ended, winner: "wolf" });
    render(<CardDeck />);
    expect(screen.getByText("狼人")).toBeInTheDocument();
  });
});
