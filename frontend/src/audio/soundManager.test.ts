import { describe, it, expect, vi, beforeEach } from "vitest";

class FakeParam {
  value = 1;
  setValueAtTime() { return this; }
  linearRampToValueAtTime() { return this; }
  cancelScheduledValues() { return this; }
}
class FakeGain { gain = new FakeParam(); connect() {} }
class FakeCtx {
  state = "running";
  currentTime = 0;
  destination = {};
  createGain() { return new FakeGain(); }
  createBufferSource() { return { buffer: null, loop: false, connect() {}, start() {}, stop() {} }; }
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
    expect(() => {
      soundManager.setMuted(true);
      soundManager.setSfxVolume(0.5);
      soundManager.setBgmVolume(0.3);
      soundManager.unlock();
    }).not.toThrow();
  });
  it("bgm playback + crossfade + stop are safe", async () => {
    (globalThis as unknown as { fetch: unknown }).fetch = vi
      .fn()
      .mockResolvedValue({ ok: true, arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)) });
    const { soundManager } = await import("./soundManager");
    await expect(soundManager.playBgm("bgm_lobby", 10)).resolves.toBeUndefined();
    await expect(soundManager.playBgm("bgm_night", 10)).resolves.toBeUndefined(); // crossfade
    await expect(soundManager.playBgm("bgm_night", 10)).resolves.toBeUndefined(); // same id = no-op
    expect(() => soundManager.stopBgm(10)).not.toThrow();
  });
});
