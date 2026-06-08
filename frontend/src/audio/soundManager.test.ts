import { describe, it, expect, vi, beforeEach } from "vitest";

class FakeGain { gain = { value: 1 }; connect() {} }
class FakeCtx {
  state = "running";
  currentTime = 0;
  destination = {};
  createGain() { return new FakeGain(); }
  createBufferSource() { return { buffer: null, connect() {}, start() {} }; }
  resume() { return Promise.resolve(); }
  decodeAudioData() { return Promise.resolve({} as AudioBuffer); }
}

beforeEach(() => {
  (globalThis as unknown as { AudioContext: unknown }).AudioContext = FakeCtx;
  (globalThis as unknown as { fetch: unknown }).fetch = vi.fn().mockResolvedValue({ ok: false });
});

describe("soundManager", () => {
  it("plays without throwing when files are missing (fallback/silent)", async () => {
    const { soundManager } = await import("./soundManager");
    expect(() => soundManager.playUi("ui_click")).not.toThrow();
    expect(() => soundManager.playGameplay("skill_bite", 1)).not.toThrow();
    expect(() => soundManager.playGameplay("skill_bite", 1)).not.toThrow();
  });
  it("mute / volume setters are safe", async () => {
    const { soundManager } = await import("./soundManager");
    expect(() => { soundManager.setMuted(true); soundManager.setSfxVolume(0.5); soundManager.unlock(); }).not.toThrow();
  });
});
