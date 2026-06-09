import { describe, it, expect, vi, afterEach } from "vitest";
import { soundManager } from "../audio/soundManager";
import { playToggle } from "./uiSound";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("playToggle", () => {
  it("plays ui_panel_open when opening", () => {
    const spy = vi.spyOn(soundManager, "playUi").mockImplementation(() => {});
    playToggle(true);
    expect(spy).toHaveBeenCalledWith("ui_panel_open");
  });

  it("plays ui_panel_close when collapsing", () => {
    const spy = vi.spyOn(soundManager, "playUi").mockImplementation(() => {});
    playToggle(false);
    expect(spy).toHaveBeenCalledWith("ui_panel_close");
  });

  it("fires exactly once per call", () => {
    const spy = vi.spyOn(soundManager, "playUi").mockImplementation(() => {});
    playToggle(true);
    playToggle(false);
    expect(spy).toHaveBeenCalledTimes(2);
  });
});
