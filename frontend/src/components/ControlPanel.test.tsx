import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ControlPanel from "./ControlPanel";
import { useGameStore } from "../store";

afterEach(() => { useGameStore.getState().exitToSetup(); vi.restoreAllMocks(); });

describe("ControlPanel", () => {
  it("pause button calls controlGame('pause') when playing", () => {
    const spy = vi.fn();
    useGameStore.setState({ status: "running", playState: "playing", runId: "r1", controlGame: spy as never });
    render(<ControlPanel />);
    fireEvent.click(screen.getByText("暂停"));
    expect(spy).toHaveBeenCalledWith("pause");
  });

  it("shows 继续 and calls controlGame('resume') when paused", () => {
    const spy = vi.fn();
    useGameStore.setState({ status: "paused", playState: "paused", runId: "r1", controlGame: spy as never });
    render(<ControlPanel />);
    fireEvent.click(screen.getByText("继续"));
    expect(spy).toHaveBeenCalledWith("resume");
  });

  it("single-step button calls stepGame()", () => {
    const spy = vi.fn();
    useGameStore.setState({ status: "running", playState: "playing", runId: "r1", stepGame: spy as never });
    render(<ControlPanel />);
    fireEvent.click(screen.getByText("单步"));
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("speed buttons are 1x/2x/4x and call setSpeed", () => {
    const spy = vi.fn();
    useGameStore.setState({ status: "running", playState: "playing", runId: "r1", speed: 1, setSpeed: spy as never });
    render(<ControlPanel />);
    fireEvent.click(screen.getByText("4x"));
    expect(spy).toHaveBeenCalledWith(4);
    expect(screen.queryByText("瞬间")).not.toBeInTheDocument();
  });
});
