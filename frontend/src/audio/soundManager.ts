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
  private gate = createBurstGate();
  private dedup = createEventDedup();

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
      this.bgmBus.gain.value = 0; // BGM 休眠占位
      this.applyGain();
    } catch {
      this.ctx = null;
    }
    return this.ctx;
  }

  private applyGain(): void {
    if (this.sfxBus) this.sfxBus.gain.value = this.muted ? 0 : this.sfxVolume;
  }

  unlock(): void {
    const ctx = this.ensureCtx();
    if (ctx && ctx.state === "suspended") ctx.resume().catch(() => {});
    this.preloadAll();
  }

  setMuted(m: boolean): void { this.muted = m; this.applyGain(); }
  setSfxVolume(v: number): void { this.sfxVolume = Math.max(0, Math.min(1, v)); this.applyGain(); }

  /** UI 音：即时、不去重、不过 burst 门。 */
  playUi(id: SfxId): void { this.emit(id); }

  /** 对局音：event_id 去重 + burst 门。 */
  playGameplay(id: SfxId, eventId?: number): void {
    if (this.dedup.seen(eventId)) return;
    if (!this.gate.allow(Date.now())) return;
    this.emit(id);
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
