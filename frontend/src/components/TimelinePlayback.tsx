import React, { useState, useEffect, useRef } from "react";
import { TimelineEvent } from "../api/types";
import { motion, AnimatePresence } from "motion/react";
import { Play, Pause, SkipBack, SkipForward, FastForward, User as UserIcon, Shield, Moon, Sun, Sword, ScanEye, Skull, HeartPulse, MessageSquare, Handshake } from "lucide-react";

interface PlayerData {
  id: string;
  role: string;
  camp: "GOOD" | "WEREWOLF" | "NEUTRAL";
  index: number;
}

const mockPlayers: PlayerData[] = [
  { id: "P1", role: "女巫", camp: "GOOD", index: 0 },
  { id: "P2", role: "预言家", camp: "GOOD", index: 1 },
  { id: "P3", role: "狼人", camp: "WEREWOLF", index: 2 },
  { id: "P4", role: "村民", camp: "GOOD", index: 3 },
  { id: "P5", role: "村民", camp: "GOOD", index: 4 },
  { id: "P6", role: "狼人", camp: "WEREWOLF", index: 5 }
];

export default function TimelinePlayback({ timeline, viewScope = "ALL" }: { timeline: TimelineEvent[], viewScope?: string }) {
  // 从第一个事件开始，让回放打开在编年史顶部并
  // 向前播放 — 初始化在最后一个事件会让视图卡在底部。
  const [cursor, setCursor] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const scrollRef = useRef<HTMLDivElement>(null);

  // 播放效果
  useEffect(() => {
    let timer: any;
    if (isPlaying) {
      timer = setInterval(() => {
        setCursor(c => {
          if (c < timeline.length - 1) return c + 1;
          setIsPlaying(false);
          return c;
        });
      }, 1500 / speed);
    }
    return () => clearInterval(timer);
  }, [isPlaying, speed, timeline.length]);

  // 自动滚动
  useEffect(() => {
    if (scrollRef.current) {
      const activeEl = scrollRef.current.querySelector('[data-active="true"]');
      if (activeEl) {
        activeEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [cursor]);

  // 计算光标位置之前的实时状态
  const currentEvent = timeline[cursor];
  const pastEvents = timeline.slice(0, cursor + 1);

  // 实时游戏状态
  const deadPlayers = new Set<string>();
  const voteCount: Record<string, number> = {};

  pastEvents.forEach(ev => {
    if (ev.result === "DEAD" && ev.targetId) {
      deadPlayers.add(ev.targetId);
    }
    if (ev.type === "vote" && ev.targetId && ev.phase !== "DAY_ANNOUNCE" /* Ensure we only count vote events */) {
      // 如果是投票事件，只显示当前票数
    }
  });

  // 计算玩家是否在发言
  const speakingPlayer = currentEvent?.type === "speech" ? currentEvent.playerId : null;

  const getCampColor = (camp: string, isDead: boolean) => {
    if (isDead) return "bg-zinc-800 text-zinc-500 border-zinc-700 opacity-60 grayscale";
    if (camp === "GOOD") return "bg-blue-500/20 text-blue-400 border-blue-500/50";
    if (camp === "WEREWOLF") return "bg-red-500/20 text-red-500 border-red-500/50";
    return "bg-amber-500/20 text-amber-500 border-amber-500/50";
  };

  const getEventIcon = (type: string | undefined) => {
    switch(type) {
      case "kill": return <Sword className="w-4 h-4 text-red-500" />;
      case "check": return <ScanEye className="w-4 h-4 text-indigo-400" />;
      case "save": return <HeartPulse className="w-4 h-4 text-emerald-500" />;
      case "vote": return <Handshake className="w-4 h-4 text-amber-500" />;
      case "speech": return <MessageSquare className="w-4 h-4 text-zinc-300" />;
      default: return <Moon className="w-4 h-4 text-zinc-500" />;
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 grid-rows-1 gap-4 h-[600px] border border-zinc-900 bg-zinc-950 rounded-lg overflow-hidden relative">
      
      {/* 1. Seat Ring (Left) */}
      <div className="col-span-1 border-r border-zinc-900 bg-[#0c0c0c] p-4 flex flex-col hidden lg:flex">
        <h3 className="font-sans text-xs text-zinc-500 tracking-widest text-center mb-12">上帝视角</h3>
        <div className="relative w-full aspect-square max-w-[200px] mx-auto mt-4">
          {mockPlayers.map((p, idx) => {
            const angle = (idx * 60) - 90; // 从顶部开始（-90度）
            const radius = 90;
            const x = Math.cos(angle * Math.PI / 180) * radius;
            const y = Math.sin(angle * Math.PI / 180) * radius;
            const isDead = deadPlayers.has(p.id);
            const isSpeaking = speakingPlayer === p.id;

            return (
              <div 
                key={p.id}
                className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 transition-all duration-300"
                style={{ transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))` }}
              >
                <div className={`
                  flex flex-col items-center justify-center w-12 h-12 rounded-full border-2 shadow-lg relative
                  ${viewScope === "ALL" || p.id === viewScope 
                    ? getCampColor(p.camp, isDead) 
                    : getCampColor("NEUTRAL", isDead) // 其他人隐藏阵营
                  }
                  ${isSpeaking ? "ring-4 ring-yellow-500/50 scale-110 z-10" : ""}
                `}>
                  <span className="font-bold text-sm tracking-tighter">{p.id}</span>
                  {!isDead && (viewScope === "ALL" || p.id === viewScope) && <span className="text-[8px] font-mono leading-none">{p.role}</span>}
                  {isDead && (
                    <div className="absolute inset-0 bg-black/60 rounded-full flex items-center justify-center">
                      <Skull className="w-5 h-5 text-zinc-400" />
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
        
        <div className="mt-auto pt-6 border-t border-zinc-900/50">
          <div className="flex justify-center gap-4 text-[10px] font-mono text-zinc-500">
            <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-blue-500/50 border border-blue-500"></div>好人</span>
            <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-red-500/50 border border-red-500"></div>狼人</span>
            <span className="flex items-center gap-1"><Skull className="w-3" />阵亡</span>
          </div>
        </div>
      </div>

      {/* 2. Event Feed (Center) */}
      <div className="col-span-1 lg:col-span-2 flex flex-col min-h-0 relative bg-zinc-950">
        <div className="h-10 border-b border-zinc-900 bg-zinc-900/20 flex items-center justify-between px-4">
          <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">
            {currentEvent?.day ? `DAY ${currentEvent.day}` : ''} {currentEvent?.isNight ? '🌙 黑夜' : '☀️ 白昼'}
          </span>
          <span className="text-[10px] font-mono text-zinc-600">
            {cursor + 1} / {timeline.length}
          </span>
        </div>
        
        <div
          ref={scrollRef}
          className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4 scroll-smooth scrollbar-thin scrollbar-thumb-zinc-800 scrollbar-track-transparent"
        >
          {timeline.map((ev, idx) => {
            const isActive = idx === cursor;
            const isPast = idx < cursor;

            // 可见性逻辑
            const isPrivateEvent = ev.phase === "NIGHT" && ev.type !== "system";
            let canView = true;
            if (viewScope === "PUBLIC" && isPrivateEvent) canView = false;
            if (viewScope.startsWith("P") && isPrivateEvent) {
              // 只有当事件参与者才能看到 
              // 有时玩家是目标，作为目标可能要到早上才知道
              // 这里只检查 playerId 是否匹配，或者如果是狼人且是击杀事件
              if (ev.playerId && !ev.playerId.includes(viewScope)) canView = false;
            }
            
            if (ev.type === "system") {
              return (
                <div key={ev.id} data-active={isActive} className={`text-center py-2 transition-opacity duration-300 ${isActive ? 'opacity-100' : isPast ? 'opacity-80' : 'opacity-20'}`}>
                  <span className="px-3 py-1 bg-zinc-900 rounded-full text-[10px] font-mono uppercase tracking-widest text-zinc-400 border border-zinc-800">
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
                  className={`flex gap-3 transition-all duration-300 ${isActive ? 'opacity-100 scale-100 ml-2' : isPast ? 'opacity-40 scale-95' : 'opacity-10 scale-95 blur-[1px]'}`}
                >
                  <div className={`mt-1 w-8 h-8 rounded-full border border-zinc-900 flex items-center justify-center shrink-0 bg-zinc-950 text-zinc-700`}>
                    <Moon className="w-4 h-4" />
                  </div>
                  <div className={`flex-1 rounded p-3 border border-zinc-900 border-dashed bg-[#0c0c0c]`}>
                    <p className={`text-xs ${isActive ? 'text-zinc-400' : 'text-zinc-600'} italic`}>[被迷雾掩盖的深夜秘密...]</p>
                  </div>
                </div>
              );
            }

            return (
              <div 
                key={ev.id} 
                data-active={isActive}
                className={`flex gap-3 transition-all duration-300 ${isActive ? 'opacity-100 scale-100 ml-2 shadow-lg shadow-black/50' : isPast ? 'opacity-80 scale-100' : 'opacity-20 scale-95 blur-[1px]'}`}
              >
                <div className={`mt-1 w-8 h-8 rounded-full border border-zinc-800 flex items-center justify-center shrink-0 ${isActive ? 'bg-zinc-800 text-zinc-200 border-yellow-500/50 shadow-[0_0_10px_rgba(234,179,8,0.2)]' : 'bg-zinc-900 text-zinc-400'}`}>
                  {getEventIcon(ev.type)}
                </div>
                
                <div className={`flex-1 rounded p-3 border ${isActive ? 'bg-zinc-900 border-zinc-700' : 'bg-zinc-950 border-zinc-900'}`}>
                  {ev.type === "speech" && (
                    <>
                      <div className="text-[10px] font-sans text-zinc-500 mb-1 font-bold">{ev.playerId} 发言</div>
                      <p className={`text-sm ${isActive ? 'text-zinc-200' : 'text-zinc-400'}`}>"{ev.message}"</p>
                    </>
                  )}
                  {ev.type !== "speech" && (
                    <>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-widest font-bold">{ev.title}</span>
                      </div>
                      <p className={`text-sm ${isActive ? 'text-red-400 font-bold' : 'text-zinc-500'}`}>{ev.description}</p>
                      
                      {ev.actions && ev.actions.length > 0 && (
                        <div className="mt-2 text-xs font-mono text-zinc-500 space-y-1">
                          {ev.actions.map(act => <div key={act} className="px-2 py-0.5 bg-zinc-950 rounded border border-zinc-900 truncate">{act}</div>)}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Playback Controls Footer */}
        <div className="h-14 bg-zinc-950 border-t border-zinc-900 flex items-center justify-between px-4 relative z-10">
          <div className="flex items-center gap-2">
            <button onClick={() => setCursor(0)} className="w-8 h-8 flex items-center justify-center text-zinc-500 hover:text-zinc-300 disabled:opacity-50" disabled={cursor === 0}>
              <SkipBack className="w-4 h-4" />
            </button>
            <button 
              onClick={() => setIsPlaying(!isPlaying)} 
              className="w-10 h-10 flex items-center justify-center bg-yellow-500 text-zinc-950 rounded-full hover:scale-105 transition-transform"
            >
              {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current ml-1" />}
            </button>
            <button onClick={() => setCursor(c => Math.min(timeline.length - 1, c + 1))} className="w-8 h-8 flex items-center justify-center text-zinc-500 hover:text-zinc-300 disabled:opacity-50" disabled={cursor === timeline.length - 1}>
              <SkipForward className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 px-4">
            <div className="w-full h-1 bg-zinc-900 rounded-full relative cursor-pointer" onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const percent = (e.clientX - rect.left) / rect.width;
              setCursor(Math.floor(percent * timeline.length));
            }}>
              <div className="absolute top-0 left-0 h-full bg-yellow-500 rounded-full pointer-events-none transition-all duration-300" style={{ width: `${(cursor / (timeline.length - 1)) * 100}%` }} />
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono">
            <button onClick={() => setSpeed(s => s === 1 ? 2 : s === 2 ? 4 : 1)} className="px-2 py-1 bg-zinc-900 rounded text-zinc-400 hover:text-zinc-200 border border-zinc-800">
              {speed}x
            </button>
          </div>
        </div>
      </div>

      {/* 3. Live State Menu (Right) */}
      <div className="col-span-1 border-l border-zinc-900 bg-[#0a0a0a] p-4 flex flex-col hidden lg:flex">
        <h3 className="font-sans text-[10px] text-zinc-600 tracking-widest mb-4">实时态视界</h3>
        
        <div className="bg-zinc-950 border border-zinc-900 rounded p-3 mb-4">
          <div className="text-[10px] font-sans text-zinc-500 mb-1">存活状况</div>
          <div className="text-xl font-serif font-bold text-yellow-500">
            {mockPlayers.length - deadPlayers.size} <span className="text-sm text-zinc-600 font-sans font-normal">/ {mockPlayers.length}</span>
          </div>
        </div>

        {currentEvent?.type === "vote" && currentEvent.actions && (
          <div className="bg-zinc-950 border border-zinc-900 rounded p-3 mb-4">
            <div className="text-[10px] font-sans text-zinc-500 mb-2">当前放逐票型</div>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-zinc-300">{currentEvent.targetId} 号出局</span>
              </div>
              <div className="flex flex-wrap gap-1 mt-1">
                 {currentEvent.actions.map(act => (
                   <span key={act} className="text-[9px] bg-zinc-900 px-1.5 py-0.5 rounded text-zinc-400 border border-zinc-800">{act.split(" ")[0]}</span>
                 ))}
              </div>
            </div>
          </div>
        )}

        <div className="bg-zinc-950 border border-zinc-900 rounded p-3 mb-4 mt-auto">
          <div className="text-[10px] font-sans text-zinc-500 mb-2">上帝视角全知</div>
          <p className="text-xs text-zinc-400 leading-tight">
            2026-06-04 15:16 录像 <br/>
            6人局，好人阵营最终获胜。
          </p>
        </div>
        
      </div>
    </div>
  );
}
