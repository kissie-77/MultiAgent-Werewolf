import { sfxPath, createBurstGate, createEventDedup, ALL_SFX_IDS, type SfxId } from "./soundMap";
import {
  playInspectSFX, playHealSFX, playPoisonSFX, playBiteSFX, playShootSFX, playVoteSFX,
} from "../utils/audio";

/** 仅这 6 个 id 有合成兜底（文件缺失/未加载时用）。 */
const SYNTH_FALLBACK: Record<string, () => void> = {
  skill_bite: playBiteSFX,
  skill_inspect: playInspectSFX,
  skill_heal: playHealSFX,
  skill_poison: playPoisonSFX,
  skill_shoot: playShootSFX,
  skill_vote: playVoteSFX,
};

class SoundManager {
  private ctx: AudioContext | null = null;
  private sfxBus: GainNode | null = null;
  private bgmBus: GainNode | null = null;
  private cache = new Map<SfxId, AudioBuffer | null>();
  private inflight = new Map<SfxId, Promise<void>>();
  private muted = false;
  private sfxVolume = 0.8;
  private bgmVolume = 0.5;
  private gate = createBurstGate();
  private dedup = createEventDedup();

  // BGM 当前曲目 + 交叉淡变所用的每轨增益（位于 source 与 bgmBus 之间）。
  private bgmId: SfxId | null = null;
  private bgmSource: AudioBufferSourceNode | null = null;
  private bgmGain: GainNode | null = null;

  private ensureCtx(): AudioContext | null {
    if (this.ctx) return this.ctx;
    try {
      const Ctor = (window.AudioContext
        || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext);
      if (!Ctor) return null;
      this.ctx = new Ctor();
      this.sfxBus = this.ctx.createGain();
      this.bgmBus = this.ctx.createGain();
      this.sfxBus.connect(this.ctx.destination);
      this.bgmBus.connect(this.ctx.destination);
      this.applyGain();
    } catch {
      this.ctx = null;
    }
    return this.ctx;
  }

  private applyGain(): void {
    if (this.sfxBus) this.sfxBus.gain.value = this.muted ? 0 : this.sfxVolume;
    if (this.bgmBus) this.bgmBus.gain.value = this.muted ? 0 : this.bgmVolume;
  }

  unlock(): void {
    const ctx = this.ensureCtx();
    if (ctx && ctx.state === "suspended") ctx.resume().catch(() => {});
    this.preloadAll();
  }

  setMuted(m: boolean): void { this.muted = m; this.applyGain(); }
  setSfxVolume(v: number): void { this.sfxVolume = Math.max(0, Math.min(1, v)); this.applyGain(); }
  setBgmVolume(v: number): void { this.bgmVolume = Math.max(0, Math.min(1, v)); this.applyGain(); }

  /** UI 音：即时、不去重、不过 burst 门。 */
  playUi(id: SfxId): void { this.emit(id); }

  /** 对局音：event_id 去重 + burst 门。 */
  playGameplay(id: SfxId, eventId?: number): void {
    if (this.dedup.seen(eventId)) return;
    if (!this.gate.allow(Date.now())) return;
    this.emit(id);
  }

  /** 切换背景音乐：循环 + 交叉淡变。同曲重复调用无副作用。 */
  async playBgm(id: SfxId, fadeMs = 1400): Promise<void> {
    if (id === this.bgmId) return;
    this.bgmId = id;
    const ctx = this.ensureCtx();
    if (!ctx || !this.bgmBus) return;
    if (ctx.state === "suspended") ctx.resume().catch(() => {});
    const buf = await this.loadBuffer(id);
    if (this.bgmId !== id) return;   // 加载期间又切了曲：放弃这次
    if (!buf) return;                // 文件缺失：保持当前

    const now = ctx.currentTime;
    const fade = Math.max(0.01, fadeMs / 1000);

    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.loop = true;
    const g = ctx.createGain();
    g.connect(this.bgmBus);
    src.connect(g);
    try { src.start(); } catch { /* edge: already started */ }
    g.gain.setValueAtTime(0, now);
    g.gain.linearRampToValueAtTime(1, now + fade);

    const oldSrc = this.bgmSource;
    const oldGain = this.bgmGain;
    if (oldGain && oldSrc) {
      oldGain.gain.cancelScheduledValues(now);
      oldGain.gain.setValueAtTime(oldGain.gain.value, now);
      oldGain.gain.linearRampToValueAtTime(0, now + fade);
      try { oldSrc.stop(now + fade + 0.05); } catch { /* noop */ }
    }
    this.bgmSource = src;
    this.bgmGain = g;
  }

  /** 停止背景音乐（淡出）。 */
  stopBgm(fadeMs = 800): void {
    const ctx = this.ctx;
    this.bgmId = null;
    if (!ctx || !this.bgmGain || !this.bgmSource) return;
    const now = ctx.currentTime;
    const fade = Math.max(0.01, fadeMs / 1000);
    const g = this.bgmGain;
    const s = this.bgmSource;
    g.gain.cancelScheduledValues(now);
    g.gain.setValueAtTime(g.gain.value, now);
    g.gain.linearRampToValueAtTime(0, now + fade);
    try { s.stop(now + fade + 0.05); } catch { /* noop */ }
    this.bgmSource = null;
    this.bgmGain = null;
  }

  private emit(id: SfxId): void {
    const ctx = this.ensureCtx();
    if (!ctx || !this.sfxBus) return;
    if (ctx.state === "suspended") ctx.resume().catch(() => {});
    const cached = this.cache.get(id);
    if (cached) { this.playBuffer(cached); return; }
    if (cached === null) { this.fallback(id); return; }   // 已知缺文件
    this.fallback(id);                                     // 首次：先合成兜底
    void this.load(id);                                    // 后台加载，下次放文件
  }

  private playBuffer(buf: AudioBuffer): void {
    if (!this.ctx || !this.sfxBus) return;
    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    src.connect(this.sfxBus);
    src.start();
  }

  private fallback(id: SfxId): void {
    const fb = SYNTH_FALLBACK[id];
    if (fb) { try { fb(); } catch { /* autoplay blocked */ } }
  }

  /** 取已解码 buffer（命中缓存即返回，否则按需加载）。BGM 等大文件走这里懒加载。 */
  private async loadBuffer(id: SfxId): Promise<AudioBuffer | null> {
    if (this.cache.has(id)) return this.cache.get(id) ?? null;
    await this.load(id);
    return this.cache.get(id) ?? null;
  }

  private load(id: SfxId): Promise<void> {
    const existing = this.inflight.get(id);
    if (existing) return existing;
    const p = (async () => {
      try {
        const res = await fetch(sfxPath(id));
        if (!res.ok) { this.cache.set(id, null); return; }
        const arr = await res.arrayBuffer();
        const buf = await this.ctx!.decodeAudioData(arr);
        this.cache.set(id, buf);
      } catch {
        this.cache.set(id, null);
      } finally {
        this.inflight.delete(id);
      }
    })();
    this.inflight.set(id, p);
    return p;
  }

  private preloadAll(): void {
    if (!this.ensureCtx()) return;
    for (const id of ALL_SFX_IDS) {
      if (!this.cache.has(id) && !this.inflight.has(id)) void this.load(id);
    }
  }
}

export const soundManager = new SoundManager();
