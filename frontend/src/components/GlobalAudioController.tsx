import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { useGameStore } from "../store";
import { soundManager } from "../audio/soundManager";
import { bgmIdForPhase } from "../audio/soundMap";

/** 对局路由：此时背景音乐跟随真实游戏阶段；其余页面统一放大厅曲。 */
const GAME_ROUTES = new Set(["/", "/game"]);

/**
 * 不渲染任何 DOM。全站背景音乐驱动 + 首次手势解锁。
 * 挂在 BrowserRouter 内、Routes 外，故所有路由（含信息页）都受其控制。
 */
export default function GlobalAudioController() {
  const pathname = useLocation().pathname;
  const phase = useGameStore((s) => s.state?.phase);

  // 首次指针手势解锁 AudioContext（满足浏览器自动播放策略），随后 BGM 才能发声。
  useEffect(() => {
    const unlock = () => soundManager.unlock();
    window.addEventListener("pointerdown", unlock, { once: true });
    return () => window.removeEventListener("pointerdown", unlock);
  }, []);

  // 路由 + 对局阶段 → 目标背景音乐（交叉淡变；同曲重复调用是空操作）。
  useEffect(() => {
    const inGame = GAME_ROUTES.has(pathname);
    const target = bgmIdForPhase(inGame ? phase : null);
    void soundManager.playBgm(target);
  }, [pathname, phase]);

  return null;
}
