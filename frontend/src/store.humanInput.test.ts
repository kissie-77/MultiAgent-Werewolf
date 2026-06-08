import { describe, it, expect, vi, beforeEach } from "vitest";
import { useGameStore } from "./store";
import { ApiClient } from "./api/client";
import type { AwaitingInputEvent } from "./api/types";

const awaitingSeat: AwaitingInputEvent = {
  event_type: "awaiting_input",
  seat: 1,
  request_id: "r1-1-0",
  kind: "seat",
  prompt: "请只回复目标玩家的全局座位号",
  valid_targets: [2, 3],
  deadline: null,
};

describe("store seat-view human input", () => {
  beforeEach(() => {
    useGameStore.setState({
      pendingInput: null,
      playerToken: null,
      humanSeat: null,
      seatRunId: null,
    });
    vi.restoreAllMocks();
  });

  it("captures an awaiting_input event into pendingInput", () => {
    const handled = useGameStore.getState().ingestSeatEvent(awaitingSeat);
    expect(handled).toBe(true);
    expect(useGameStore.getState().pendingInput).toMatchObject({
      request_id: "r1-1-0",
      kind: "seat",
      valid_targets: [2, 3],
    });
  });

  it("clears pendingInput when the input is acknowledged", () => {
    useGameStore.setState({ pendingInput: awaitingSeat });
    const handled = useGameStore
      .getState()
      .ingestSeatEvent({ event_type: "input_received", request_id: "r1-1-0" });
    expect(handled).toBe(true);
    expect(useGameStore.getState().pendingInput).toBeNull();
  });

  it("does not consume ordinary game events", () => {
    const handled = useGameStore
      .getState()
      .ingestSeatEvent({ event_type: "player_speech", data: { player_id: "player_2" } });
    expect(handled).toBe(false);
  });

  it("submits the normalized payload and clears pendingInput", async () => {
    useGameStore.setState({
      pendingInput: awaitingSeat,
      playerToken: "seat1-r1",
      seatRunId: "r1",
      humanSeat: 1,
    });
    const spy = vi
      .spyOn(ApiClient, "sendInput")
      .mockResolvedValue({ run_id: "r1", accepted: true, message: null });

    await useGameStore.getState().submitHumanInput({ kind: "seat", seat: 2 });

    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith("r1", {
      token: "seat1-r1",
      request_id: "r1-1-0",
      kind: "seat",
      payload: "2",
    });
    expect(useGameStore.getState().pendingInput).toBeNull();
  });

  it("normalizes a witch poison selection", async () => {
    useGameStore.setState({
      pendingInput: { ...awaitingSeat, kind: "witch", request_id: "r1-1-1" },
      playerToken: "seat1-r1",
      seatRunId: "r1",
      humanSeat: 1,
    });
    const spy = vi
      .spyOn(ApiClient, "sendInput")
      .mockResolvedValue({ run_id: "r1", accepted: true, message: null });

    await useGameStore
      .getState()
      .submitHumanInput({ kind: "witch", action: "poison", seat: 3 });

    expect(spy).toHaveBeenCalledWith("r1", {
      token: "seat1-r1",
      request_id: "r1-1-1",
      kind: "witch",
      payload: "毒 [[3]]",
    });
    expect(useGameStore.getState().pendingInput).toBeNull();
  });

  it("is a no-op without a pending request", async () => {
    const spy = vi
      .spyOn(ApiClient, "sendInput")
      .mockResolvedValue({ run_id: "r1", accepted: true, message: null });
    await useGameStore.getState().submitHumanInput({ kind: "seat", seat: 2 });
    expect(spy).not.toHaveBeenCalled();
  });
});

describe("store: cast + selection", () => {
  it("triggerCast sets activeCast and clearCast clears it", () => {
    useGameStore.getState().triggerCast({
      casterId: "USER", casterName: "Player1", role: "Witch",
      skillName: "女巫施药", skillSub: "解药 / 毒药",
      targetId: 3, targetName: "Player3", effectType: "heal",
    });
    expect(useGameStore.getState().activeCast?.effectType).toBe("heal");
    useGameStore.getState().clearCast();
    expect(useGameStore.getState().activeCast).toBeNull();
  });

  it("setSelectedTargetSeat updates selection", () => {
    useGameStore.getState().setSelectedTargetSeat(4);
    expect(useGameStore.getState().selectedTargetSeat).toBe(4);
    useGameStore.getState().setSelectedTargetSeat(null);
    expect(useGameStore.getState().selectedTargetSeat).toBeNull();
  });
});
