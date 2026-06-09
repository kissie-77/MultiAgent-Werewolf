import React, { useState, useEffect, useRef, useMemo } from "react";
import { TimelineEvent, ReplayRunInfo, PlayerScore } from "../api/types";
import { Play, Pause, SkipBack, SkipForward, Moon, Sword, ScanEye, Skull, HeartPulse, MessageSquare, Handshake, ChevronDown } from "lucide-react";

interface SeatPlayer {
  id: string;
  role: string;
  camp: "GOOD" | "WEREWOLF" | "NEUTRAL";
  index: number;
}

function normalizeSeatId(raw: string | number | null | undefined): string {
  const digits = String(raw ?? "").replace(/\D/g, "");
  const n = parseInt(digits, 10);
  return Number.isFinite(n) && n > 0 ? `P${n}` : String(raw ?? "");
}

function toCamp(camp: string | null | undefined): SeatPlayer["camp"] {
  const c = (camp ?? "").toLowerCase();
  if (c.includes("wolf") || c.includes("werewolf") || c.includes("狼")) return "WEREWOLF";
  if (c.includes("neutral") || c.includes("third")) return "NEUTRAL";
  return "GOOD";
}

function buildSeatPlayers(
  scores: PlayerScore[] | undefined,
  seatCount: number,
): SeatPlayer[] {
  if (scores && scores.length > 0) {
    return scores.map((p, idx) => ({
      id: `P${p.playerId}`,
      role: p.role || "未知",
      camp: toCamp(p.camp),
      index: idx,
    }));
  }
  return Array.from({ length: seatCount }, (_, i) => ({
    id: `P${i + 1}`,
    role: "未知",
    camp: "GOOD" as const,
    index: i,
  }));
}

export default function TimelinePlayback({
  timeline,
  viewScope = "ALL",
  setViewScope,
  seatNumbers = [],
  run,
  players = [],
}: {
  timeline: TimelineEvent[];
  viewScope?: string;
  setViewScope?: (v: string) => void;
  seatNumbers?: number[];
  run?: ReplayRunInfo;
  players?: PlayerScore[];
}) {
  const [cursor, setCursor] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [showScopePicker, setShowScopePicker] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const seatPlayers = useMemo(
    () => buildSeatPlayers(players, (run?.initial_players ?? players.length) || 6),
    [players, run?.initial_players],
  );

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | undefined;
    if (isPlaying) {
      timer = setInterval(() => {
        setCursor((c) => {
          if (c < timeline.length - 1) return c + 1;
          setIsPlaying(false);
          return c;
        });
      }, 1500 / speed);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isPlaying, speed, timeline.length]);

  useEffect(() => {
    if (scrollRef.current) {
      const activeEl = scrollRef.current.querySelector('[data-active="true"]');
      if (activeEl) {
        activeEl.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }, [cursor]);

  const currentEvent = timeline[cursor];
  const pastEvents = timeline.slice(0, cursor + 1);

  const deadPlayers = new Set<string>();
  pastEvents.forEach((ev) => {
    // Kill-type events: werewolf_killed / player_died / player_eliminated / witch_poison_used
    // Backend puts the victim in player_id OR target_id depending on the event_type.
    if (ev.type === "kill") {
      if (ev.targetId) deadPlayers.add(normalizeSeatId(ev.targetId));
      if (ev.playerId) deadPlayers.add(normalizeSeatId(ev.playerId));
    }
    // Fallback: any event with result === "DEAD" on playerId or targetId
    if (ev.result === "DEAD") {
      if (ev.playerId) deadPlayers.add(normalizeSeatId(ev.playerId));
      if (ev.targetId) deadPlayers.add(normalizeSeatId(ev.targetId));
    }
  });

  const speakingPlayer = currentEvent?.type === "speech"
    ? normalizeSeatId(currentEvent.playerId)
    : null;

  const getCampColor = (camp: string, isDead: boolean) => {
    if (isDead) return "bg-zinc-800 text-zinc-500 border-zinc-700 opacity-60 grayscale";
    if (camp === "GOOD") return "bg-blue-500/20 text-blue-400 border-blue-500/50";
    if (camp === "WEREWOLF") return "bg-red-500/20 text-red-500 border-red-500/50";
    return "bg-amber-500/20 text-amber-500 border-amber-500/50";
  };

  const getEventIcon = (type: string | undefined) => {
    switch (type) {
      case "kill": return <Sword className="w-5 h-5 text-red-500" />;
      case "check": return <ScanEye className="w-5 h-5 text-indigo-400" />;
      case "save": return <HeartPulse className="w-5 h-5 text-emerald-500" />;
      case "vote": return <Handshake className="w-5 h-5 text-amber-500" />;
      case "speech": return <MessageSquare className="w-5 h-5 text-zinc-300" />;
      default: return <Moon className="w-5 h-5 text-zinc-500" />;
    }
  };

  const angleStep = seatPlayers.length > 0 ? 360 / seatPlayers.length : 60;
  const winnerLabel = run?.winner_camp === "WOLVES" ? "狼人阵营获胜" : "好人阵营获胜";

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 grid-rows-1 gap-4 h-[650px] border border-zinc-900 bg-zinc-950 rounded-lg overflow-hidden relative">
      {/* ═══ Left panel: Seat wheel + View scope ═══ */}
      <div className="col-span-1 border-r border-zinc-900 bg-[#0c0c0c] p-5 flex flex-col hidden lg:flex">
        {/* View scope toggle — compact, with border/glow */}
        <div className="mb-6">
          <button
            onClick={() => setShowScopePicker(!showScopePicker)}
            className={`w-full flex items-center justify-between gap-2 px-4 py-2.5 rounded-lg border transition-all cursor-pointer ${
              viewScope === "ALL"
                ? "border-amber-500/50 bg-amber-500/10 text-amber-400 shadow-[0_0_12px_rgba(245,158,11,0.15)]"
                : viewScope === "PUBLIC"
                ? "border-blue-500/40 bg-blue-500/8 text-blue-400"
                : "border-violet-500/40 bg-violet-500/8 text-violet-400"
            }`}
          >
            <div className="flex items-center gap-2">
              <span className={`w-4 h-4 rounded border-2 flex items-center justify-center text-[10px] font-bold transition-colors ${
                viewScope === "ALL"
                  ? "bg-amber-500 border-amber-500 text-black"
                  : "bg-transparent border-current"
              }`}>
                {viewScope === "ALL" ? "✓" : ""}
              </span>
              <span className="text-sm font-mono font-bold tracking-wider">
                {viewScope === "ALL" ? "上帝视角" : viewScope === "PUBLIC" ? "公开视角" : `${viewScope} 视角`}
              </span>
            </div>
            <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${showScopePicker ? "rotate-180" : ""}`} />
          </button>

          {showScopePicker && (
            <div className="mt-2 space-y-0.5 bg-zinc-900/80 border border-zinc-800 rounded-lg p-1.5 shadow-xl shadow-black/50">
              <button
                onClick={() => { setViewScope?.("ALL"); setShowScopePicker(false); }}
                className={`w-full text-left px-3 py-2 text-xs font-mono rounded-md transition-all cursor-pointer ${
                  viewScope === "ALL"
                    ? "bg-amber-500/20 text-amber-400 border-l-2 border-amber-500 font-bold"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 border-l-2 border-transparent"
                }`}
              >
                ☉ 上帝视角 — 全知全能
              </button>
              <button
                onClick={() => { setViewScope?.("PUBLIC"); setShowScopePicker(false); }}
                className={`w-full text-left px-3 py-2 text-xs font-mono rounded-md transition-all cursor-pointer ${
                  viewScope === "PUBLIC"
                    ? "bg-blue-500/20 text-blue-400 border-l-2 border-blue-500 font-bold"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 border-l-2 border-transparent"
                }`}
              >
                ◎ 公开视角 — 日间公开信息
              </button>
              <div className="border-t border-zinc-800 my-1" />
              {seatNumbers.map((n) => (
                <button
                  key={n}
                  onClick={() => { setViewScope?.(`P${n}`); setShowScopePicker(false); }}
                  className={`w-full text-left px-3 py-2 text-xs font-mono rounded-md transition-all cursor-pointer ${
                    viewScope === `P${n}`
                      ? "bg-violet-500/20 text-violet-400 border-l-2 border-violet-500 font-bold"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 border-l-2 border-transparent"
                  }`}
                >
                  P{n} 视角 — 座位 {n} 所见
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Seat wheel — pushed down with more top margin to avoid folding */}
        <div className="relative w-full aspect-square max-w-[220px] mx-auto mt-6 flex-1 flex items-center justify-center">
          {seatPlayers.map((p, idx) => {
            const angle = idx * angleStep - 90;
            const radius = 90;
            const x = Math.cos((angle * Math.PI) / 180) * radius;
            const y = Math.sin((angle * Math.PI) / 180) * radius;
            const isDead = deadPlayers.has(p.id);
            const isSpeaking = speakingPlayer === p.id;

            return (
              <div
                key={p.id}
                className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 transition-all duration-300"
                style={{ transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))` }}
              >
                <div
                  className={`
                  flex flex-col items-center justify-center w-14 h-14 rounded-full border-2 shadow-lg relative
                  ${viewScope === "ALL" || p.id === viewScope
                      ? getCampColor(p.camp, isDead)
                      : getCampColor("NEUTRAL", isDead)
                    }
                  ${isSpeaking ? "ring-4 ring-yellow-500/60 scale-110 z-10 shadow-[0_0_16px_rgba(234,179,8,0.35)]" : ""}
                `}
                >
                  <span className="font-bold text-sm tracking-tighter">{p.id}</span>
                  {!isDead && (viewScope === "ALL" || p.id === viewScope) && (
                    <span className="text-[9px] font-mono leading-none mt-0.5">{p.role}</span>
                  )}
                  {isDead && (
                    <div className="absolute inset-0 bg-black/60 rounded-full flex items-center justify-center">
                      <Skull className="w-6 h-6 text-zinc-400" />
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Legend fixed at bottom */}
        <div className="mt-auto pt-5 border-t border-zinc-900/50">
          <div className="flex justify-center gap-5 text-xs font-mono text-zinc-500">
            <span className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-blue-500/50 border border-blue-500" />好人</span>
            <span className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-red-500/50 border border-red-500" />狼人</span>
            <span className="flex items-center gap-1.5"><Skull className="w-4" />阵亡</span>
          </div>
        </div>
      </div>

      {/* ═══ Center: Timeline events ═══ */}
      <div className="col-span-1 lg:col-span-2 flex flex-col min-h-0 relative bg-zinc-950">
        <div className="h-12 border-b border-zinc-900 bg-zinc-900/20 flex items-center justify-between px-5">
          <span className="text-xs font-mono text-zinc-500 uppercase tracking-widest font-bold">
            {currentEvent?.day ? `DAY ${currentEvent.day}` : ""} {currentEvent?.isNight ? "🌙 黑夜" : "☀️ 白昼"}
          </span>
          <span className="text-xs font-mono text-zinc-600">
            {timeline.length > 0 ? cursor + 1 : 0} / {timeline.length}
          </span>
        </div>

        <div
          ref={scrollRef}
          className="flex-1 min-h-0 overflow-y-auto p-5 space-y-4 scroll-smooth scrollbar-thin scrollbar-thumb-zinc-800 scrollbar-track-transparent"
        >
          {timeline.map((ev, idx) => {
            const isActive = idx === cursor;
            const isPast = idx < cursor;
            const isPrivateEvent = ev.phase === "NIGHT" && ev.type !== "system";
            let canView = true;
            if (viewScope === "PUBLIC" && isPrivateEvent) canView = false;
            if (viewScope.startsWith("P") && isPrivateEvent) {
              if (ev.playerId && !normalizeSeatId(ev.playerId).includes(viewScope)) canView = false;
            }

            if (ev.type === "system") {
              return (
                <div key={ev.id} data-active={isActive} className={`text-center py-2 transition-opacity duration-300 ${isActive ? "opacity-100" : isPast ? "opacity-80" : "opacity-20"}`}>
                  <span className="px-4 py-1.5 bg-zinc-900 rounded-full text-sm font-mono uppercase tracking-widest text-zinc-400 border border-zinc-800">
                    {ev.day}日 {ev.title} - {ev.description}
                  </span>
                </div>
              );
            }

            if (!canView) {
              return (
                <div
                  key={ev.id}
                  data-active={isActive}
                  className={`flex gap-3 transition-all duration-300 ${isActive ? "opacity-100 scale-100 ml-2" : isPast ? "opacity-40 scale-95" : "opacity-10 scale-95 blur-[1px]"}`}
                >
                  <div className="mt-1 w-10 h-10 rounded-full border border-zinc-900 flex items-center justify-center shrink-0 bg-zinc-950 text-zinc-700">
                    <Moon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 rounded p-3 border border-zinc-900 border-dashed bg-[#0c0c0c]">
                    <p className="text-sm text-zinc-500 italic">[被迷雾掩盖的深夜秘密...]</p>
                  </div>
                </div>
              );
            }

            return (
              <div
                key={ev.id}
                data-active={isActive}
                className={`flex gap-3 transition-all duration-300 ${isActive ? "opacity-100 scale-100 ml-2 shadow-lg shadow-black/50" : isPast ? "opacity-80 scale-100" : "opacity-20 scale-95 blur-[1px]"}`}
              >
                <div className={`mt-1 w-10 h-10 rounded-full border border-zinc-800 flex items-center justify-center shrink-0 ${isActive ? "bg-zinc-800 text-zinc-200 border-yellow-500/50 shadow-[0_0_10px_rgba(234,179,8,0.2)]" : "bg-zinc-900 text-zinc-400"}`}>
                  {getEventIcon(ev.type)}
                </div>

                <div className={`flex-1 rounded p-4 border ${isActive ? "bg-zinc-900 border-zinc-700" : "bg-zinc-950 border-zinc-900"}`}>
                  {ev.type === "speech" && (
                    <>
                      <div className="text-sm font-sans text-zinc-500 mb-1.5 font-bold">{normalizeSeatId(ev.playerId)} 发言</div>
                      <p className={`text-base ${isActive ? "text-zinc-200" : "text-zinc-400"}`}>&quot;{ev.message}&quot;</p>
                    </>
                  )}
                  {ev.type !== "speech" && (
                    <>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-sm font-mono text-zinc-400 uppercase tracking-widest font-bold">{ev.title}</span>
                      </div>
                      <p className={`text-sm ${isActive ? "text-red-400 font-bold" : "text-zinc-500"}`}>{ev.description}</p>
                      {ev.actions && ev.actions.length > 0 && (
                        <div className="mt-2 text-sm font-mono text-zinc-500 space-y-1">
                          {ev.actions.map((act) => (
                            <div key={act} className="px-2 py-0.5 bg-zinc-950 rounded border border-zinc-900 truncate">{act}</div>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Playback controls */}
        <div className="h-16 bg-zinc-950 border-t border-zinc-900 flex items-center justify-between px-5 relative z-10">
          <div className="flex items-center gap-3">
            <button type="button" aria-label="回到开头" onClick={() => setCursor(0)} className="w-9 h-9 flex items-center justify-center text-zinc-500 hover:text-zinc-300 disabled:opacity-50" disabled={cursor === 0}>
              <SkipBack className="w-5 h-5" />
            </button>
            <button
              type="button"
              aria-label={isPlaying ? "暂停回放" : "播放回放"}
              onClick={() => setIsPlaying(!isPlaying)}
              className="w-11 h-11 flex items-center justify-center bg-yellow-500 text-zinc-950 rounded-full hover:scale-105 transition-transform"
            >
              {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current ml-1" />}
            </button>
            <button type="button" aria-label="下一事件" onClick={() => setCursor((c) => Math.min(timeline.length - 1, c + 1))} className="w-9 h-9 flex items-center justify-center text-zinc-500 hover:text-zinc-300 disabled:opacity-50" disabled={cursor === timeline.length - 1}>
              <SkipForward className="w-5 h-5" />
            </button>
          </div>

          <div className="flex-1 px-5">
            <div
              className="w-full h-1.5 bg-zinc-900 rounded-full relative cursor-pointer"
              role="slider"
              aria-label="回放进度"
              aria-valuemin={0}
              aria-valuemax={Math.max(timeline.length - 1, 0)}
              aria-valuenow={cursor}
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const percent = (e.clientX - rect.left) / rect.width;
                setCursor(Math.floor(percent * timeline.length));
              }}
            >
              <div
                className="absolute top-0 left-0 h-full bg-yellow-500 rounded-full pointer-events-none transition-all duration-300"
                style={{ width: `${timeline.length > 1 ? (cursor / (timeline.length - 1)) * 100 : 0}%` }}
              />
            </div>
          </div>

          <div className="flex items-center gap-2 text-sm font-mono">
            <button type="button" aria-label="切换播放速度" onClick={() => setSpeed((s) => (s === 1 ? 2 : s === 2 ? 4 : 1))} className="px-3 py-1.5 bg-zinc-900 rounded text-zinc-400 hover:text-zinc-200 border border-zinc-800">
              {speed}x
            </button>
          </div>
        </div>
      </div>

      {/* ═══ Right panel: Live status ═══ */}
      <div className="col-span-1 border-l border-zinc-900 bg-[#0a0a0a] p-5 flex flex-col hidden lg:flex">
        <h3 className="font-sans text-xs text-zinc-600 tracking-widest mb-5 font-bold uppercase">实时态视界</h3>

        <div className="bg-zinc-950 border border-zinc-900 rounded-lg p-4 mb-4">
          <div className="text-xs font-sans text-zinc-500 mb-1.5">存活状况</div>
          <div className="text-2xl font-serif font-bold text-yellow-500">
            {seatPlayers.length - deadPlayers.size}{" "}
            <span className="text-base text-zinc-600 font-sans font-normal">/ {seatPlayers.length}</span>
          </div>
        </div>

        {currentEvent?.type === "vote" && currentEvent.actions && (
          <div className="bg-zinc-950 border border-zinc-900 rounded-lg p-4 mb-4">
            <div className="text-xs font-sans text-zinc-500 mb-2">当前放逐票型</div>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm font-mono">
                <span className="text-zinc-300">{normalizeSeatId(currentEvent.targetId)} 号出局</span>
              </div>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {currentEvent.actions.map((act) => (
                  <span key={act} className="text-xs bg-zinc-900 px-2 py-0.5 rounded text-zinc-400 border border-zinc-800">{act.split(" ")[0]}</span>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="bg-zinc-950 border border-zinc-900 rounded-lg p-4 mb-4 mt-auto">
          <div className="text-xs font-sans text-zinc-500 mb-2">对局概要</div>
          <p className="text-sm text-zinc-400 leading-relaxed">
            {run?.date ? `${run.date} 录像` : "复盘录像"}
            <br />
            {run?.initial_players ?? seatPlayers.length} 人局，{winnerLabel}。
          </p>
        </div>
      </div>
    </div>
  );
}
