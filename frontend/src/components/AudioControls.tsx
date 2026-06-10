import { useEffect, useRef, useState } from "react";
import { Volume2, VolumeX, Music2, Bell } from "lucide-react";
import { useGameStore } from "../store";
import { soundManager } from "../audio/soundManager";
import { playToggle } from "../lib/uiSound";

/**
 * 复用型音量控件（折叠式）。
 * 折叠态：一个喇叭图标（静音时显示 VolumeX）。点击 → 在其下方右对齐弹出浮层，
 * 浮层含「静音键 + 背景音乐滑块 + 音效滑块」。点外部 / Esc / 再点图标收起。
 * 出现在每个界面（首页浮层 / 内容页顶栏 / 对局顶栏 / 配置屏齿轮旁 / 结算面板 / 过场态）。
 *
 * @param className 施加在根容器上的定位类。缺省 "relative"（顶栏内联用）；
 *                  浮层场景传如 "fixed top-4 right-4 z-50"。
 */
export default function AudioControls({
  className,
  compact = false,
}: {
  className?: string;
  compact?: boolean;
}) {
  const audioMuted = useGameStore((s) => s.audioMuted);
  const sfxVolume = useGameStore((s) => s.sfxVolume);
  const bgmVolume = useGameStore((s) => s.bgmVolume);
  const setAudioMuted = useGameStore((s) => s.setAudioMuted);
  const setSfxVolume = useGameStore((s) => s.setSfxVolume);
  const setBgmVolume = useGameStore((s) => s.setBgmVolume);

  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  // 统一开合：带开/合提示音。
  const setOpenWithSound = (next: boolean) => {
    if (next === open) return;
    playToggle(next);
    setOpen(next);
  };

  // 展开时：点外部 / Esc 收起。
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpenWithSound(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpenWithSound(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  return (
    <div ref={rootRef} data-sfx="off" className={`inline-flex ${className ?? "relative"}`}>
      {/* 折叠态触发图标 —— 反映静音状态 */}
      <button
        type="button"
        onClick={() => setOpenWithSound(!open)}
        aria-label="音量设置"
        aria-expanded={open}
        title="音量设置"
        className={`flex items-center justify-center rounded-full border bg-zinc-900/60 backdrop-blur-md shadow-xl cursor-pointer transition-all active:scale-95 ${
          compact ? "p-1.5" : "p-2 md:p-2.5"
        } ${
          audioMuted
            ? "border-red-500/50 text-red-300/90 hover:text-red-200 hover:bg-zinc-800"
            : "border-amber-500/50 text-amber-200/90 hover:text-amber-100 hover:bg-zinc-800"
        }`}
      >
        {audioMuted ? (
          <VolumeX className={compact ? "w-4 h-4" : "w-5 h-5 md:w-6 md:h-6"} />
        ) : (
          <Volume2 className={compact ? "w-4 h-4" : "w-5 h-5 md:w-6 md:h-6"} />
        )}
      </button>

      {/* 展开态浮层 —— 右对齐于图标下方 */}
      {open && (
        <div className="absolute right-0 top-full mt-2 z-[60] flex w-56 flex-col gap-2.5 rounded-md border border-amber-500/30 bg-zinc-950/95 p-3 shadow-[0_8px_24px_rgba(0,0,0,0.6)] backdrop-blur-md">
          <button
            type="button"
            onClick={() => {
              const next = !audioMuted;
              setAudioMuted(next);
              // 解除静音时给一声确认音（此时增益已恢复，故可闻）。
              if (!next) soundManager.playUi("ui_click");
            }}
            className={`flex items-center gap-1.5 self-start rounded px-2 py-1 text-[11px] font-sans tracking-wide cursor-pointer transition-colors ${
              audioMuted
                ? "text-red-300 hover:bg-red-500/10"
                : "text-amber-200 hover:bg-amber-500/10"
            }`}
          >
            {audioMuted ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
            {audioMuted ? "取消静音" : "静音"}
          </button>

          <label className="flex items-center gap-2 text-[11px] text-zinc-300" title="背景音乐音量">
            <Music2 className={`h-3.5 w-3.5 shrink-0 ${audioMuted ? "text-zinc-600" : "text-amber-300/80"}`} />
            <span className="w-10 shrink-0 tracking-widest">背景</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={bgmVolume}
              onChange={(e) => setBgmVolume(Number(e.target.value))}
              disabled={audioMuted}
              aria-label="背景音乐音量"
              className="flex-1 accent-amber-500 cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
            />
          </label>

          <label className="flex items-center gap-2 text-[11px] text-zinc-300" title="音效音量">
            <Bell className={`h-3.5 w-3.5 shrink-0 ${audioMuted ? "text-zinc-600" : "text-amber-300/80"}`} />
            <span className="w-10 shrink-0 tracking-widest">音效</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={sfxVolume}
              onChange={(e) => setSfxVolume(Number(e.target.value))}
              disabled={audioMuted}
              aria-label="音效音量"
              className="flex-1 accent-amber-500 cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
            />
          </label>
        </div>
      )}
    </div>
  );
}
