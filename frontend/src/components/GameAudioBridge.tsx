import { useEffect, useRef } from "react";
import { useGameStore } from "../store";
import { soundManager } from "../audio/soundManager";
import { stageSfx } from "../audio/soundMap";

/** 不渲染任何 DOM；把 store 信号桥接到 SoundManager。 */
export default function GameAudioBridge() {
  const stageFx = useGameStore((s) => s.stageFx);
  const audioMuted = useGameStore((s) => s.audioMuted);
  const sfxVolume = useGameStore((s) => s.sfxVolume);
  const lastNonce = useRef<number>(-1);

  // 首次手势解锁 AudioContext（满足浏览器自动播放策略）
  useEffect(() => {
    const unlock = () => soundManager.unlock();
    window.addEventListener("pointerdown", unlock, { once: true });
    return () => window.removeEventListener("pointerdown", unlock);
  }, []);

  // 音量 / 静音同步
  useEffect(() => { soundManager.setMuted(audioMuted); }, [audioMuted]);
  useEffect(() => { soundManager.setSfxVolume(sfxVolume); }, [sfxVolume]);

  // 昼夜转场音（stageFx 已被 PhaseTransitionCard 做过突发抑制）
  useEffect(() => {
    if (!stageFx) return;
    if (stageFx.nonce === lastNonce.current) return;
    lastNonce.current = stageFx.nonce;
    const sid = stageSfx(stageFx.stage);
    if (sid) soundManager.playGameplay(sid);
  }, [stageFx]);

  return null;
}
