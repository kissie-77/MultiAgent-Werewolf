import React, { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import ThreeCanvas from "../components/ThreeCanvas";
import SpeechConsole from "../components/SpeechConsole";
import UnifiedGameHeader from "../components/UnifiedGameHeader";
import GameSetup from "../components/GameSetup";
import GameOverPanel from "../components/GameOverPanel";

import { useGameStore } from "../store";
import { Skull, Moon, MessageSquare } from "lucide-react";
import AlertOverlays from "../components/AlertOverlays";
import SeatCommandDock from "../components/SeatCommandDock";
import IdentityHud from "../components/IdentityHud";
import CardDeck from "../components/CardDeck";
import CastSkillOverlay from "../components/CastSkillOverlay";
import LiveCueAnchors from "../components/LiveCueAnchors";
import ErrorBoundary from "../components/ErrorBoundary";
import PhaseTransitionCard from "../components/PhaseTransitionCard";
import GameAudioBridge from "../components/GameAudioBridge";
import RightPanelColumn from "../components/RightPanelColumn";

export default function GameApp() {
  const navigate = useNavigate();
  const gameState = useGameStore((state) => state.state);
  const exitGame = useGameStore((state) => state.exitGame);

  const [searchParams] = useSearchParams();
  const runId = searchParams.get("run_id");
  const view = searchParams.get("view");
  const seatParam = searchParams.get("seat");
  const token = searchParams.get("token");
  const connectSpectate = useGameStore((s) => s.connectSpectate);
  const connectSeat = useGameStore((s) => s.connectSeat);
  const disconnectSpectate = useGameStore((s) => s.disconnectSpectate);
  const spectateError = useGameStore((s) => s.spectateError);
  const insightEnabled = useGameStore((s) => s.insightEnabled);

  const isLiveRun = Boolean(runId);
  const isSeatView =
    isLiveRun &&
    view === "seat" &&
    Boolean(token) &&
    Number.isFinite(Number(seatParam));

  useEffect(() => {
    if (!runId) return;
    const seat = seatParam ? Number(seatParam) : NaN;
    if (view === "seat" && token && Number.isFinite(seat)) {
      connectSeat(runId, { seat, token });
    } else {
      connectSpectate(runId);
    }
    return () => disconnectSpectate();
  }, [runId, view, seatParam, token, connectSpectate, connectSeat, disconnectSpectate]);

  const handleExitGame = async () => {
    await exitGame();
    navigate("/");
  };

  if (!isLiveRun) {
    return (
      <div className="relative w-screen h-screen flex flex-col items-center justify-center bg-gradient-to-br from-indigo-950 via-slate-900 to-blue-950 text-slate-100 overflow-hidden font-sans select-none antialiased">
        <div className="absolute inset-0 bg-woodcut-dark opacity-30 mix-blend-multiply pointer-events-none z-0" />
        <ThreeCanvas />
        <GameSetup />
        <div className="absolute inset-0 pointer-events-none border-4 border-indigo-900/40 shadow-[inset_0_0_100px_rgba(30,58,138,0.5)] z-50 rounded-xl" />
      </div>
    );
  }

  if (!gameState) {
    return (
      <div className="min-h-screen bg-[#0d0907] flex flex-col items-center justify-center text-zinc-400 font-mono text-xs uppercase tracking-widest gap-2">
        <div className="w-6 h-6 border-2 border-t-yellow-500 border-zinc-800 rounded-full animate-spin" />
        <span>召唤宿命之光...</span>
      </div>
    );
  }

  const spectateBooting =
    gameState.phase === "START_SCREEN" &&
    (gameState.players?.length ?? 0) === 0;

  if (spectateError) {
    return (
      <div className="min-h-screen bg-[#0d0907] flex flex-col items-center justify-center text-zinc-300 font-sans gap-4 px-6 text-center">
        <p className="text-amber-500/90 font-sans text-xs">观战不可用</p>
        <p className="text-sm text-zinc-400 max-w-md">{spectateError}</p>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => navigate("/runs")}
            className="px-4 py-2 bg-zinc-900 border border-zinc-700 rounded text-xs font-mono hover:border-zinc-500"
          >
            战绩中心
          </button>
          {runId && (
            <button
              type="button"
              onClick={() => navigate(`/replay/${runId}`)}
              className="px-4 py-2 bg-indigo-900/60 border border-indigo-700 rounded text-xs font-mono hover:border-indigo-500"
            >
              打开复盘
            </button>
          )}
          <button
            type="button"
            onClick={handleExitGame}
            className="px-4 py-2 bg-zinc-900 border border-zinc-700 rounded text-xs font-mono hover:border-zinc-500"
          >
            返回首页
          </button>
        </div>
      </div>
    );
  }

  if (spectateBooting) {
    return (
      <div className="min-h-screen bg-[#0d0907] flex flex-col items-center justify-center gap-5 text-zinc-400">
        <div className="relative w-20 h-20 flex items-center justify-center">
          <div className="absolute inset-0 rounded-full border border-violet-700/40 animate-ping" />
          <div className="absolute inset-2 rounded-full border border-amber-700/30 animate-ping [animation-delay:400ms]" />
          <Moon className="w-9 h-9 text-violet-300/90 animate-pulse" />
        </div>
        <div className="flex flex-col items-center gap-1">
          <span className="font-serif font-black text-sm tracking-[0.4em] text-zinc-200 uppercase">
            候场集结
          </span>
          <span className="font-mono text-[11px] tracking-widest text-zinc-500 uppercase">
            等待 LLM 入场…
          </span>
        </div>
        <span className="text-[10px] text-zinc-600 font-sans">{runId}</span>
      </div>
    );
  }

  const isNight = gameState?.phase?.startsWith("NIGHT") || false;

  return (
    <div className={`relative w-screen h-screen flex flex-col transition-colors duration-[2000ms] ease-in-out ${isNight ? "bg-gradient-to-br from-[#0d0415] via-slate-900 to-[#1a0b2e] shadow-[inset_0_0_120px_rgba(76,29,149,0.4)]" : "bg-gradient-to-br from-amber-950 via-[#27150a] to-[#3f1905] shadow-[inset_0_0_120px_rgba(217,119,6,0.2)]"} text-slate-100 overflow-hidden font-sans select-none antialiased`}>
      <div className="absolute inset-0 bg-woodcut-dark opacity-30 mix-blend-multiply pointer-events-none z-0" />
      <ThreeCanvas />

      {gameState?.phase === "GAME_OVER" && (
        <ErrorBoundary
          label="GameOverPanel"
          fallback={
            <div className="absolute inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-black/90 text-zinc-200 pointer-events-auto">
              <span className="text-2xl font-black tracking-widest">
                {gameState.winner === "WOLVES" ? "狼人阵营获胜" : "好人阵营获胜"}
              </span>
              <span className="font-sans text-xs text-zinc-500">结算面板渲染异常，已安全兜底。</span>
              <button onClick={handleExitGame} className="px-5 py-2 bg-zinc-800 border border-zinc-700 rounded text-xs hover:border-zinc-500">
                退出游戏
              </button>
            </div>
          }
        >
          <GameOverPanel
            gameState={gameState}
            onRestart={handleExitGame}
            onExit={handleExitGame}
            runId={runId}
            userSeat={isSeatView && seatParam ? Number(seatParam) : null}
          />
        </ErrorBoundary>
      )}

      <div className="absolute inset-0 flex flex-col pointer-events-none z-10 w-full h-full">
        <div className="pointer-events-auto">
          <UnifiedGameHeader onExit={handleExitGame} isLiveRun={isLiveRun} />
        </div>

        <div className="flex-grow flex flex-row w-full min-h-0 relative">
          {isSeatView && (
            <div className="w-[300px] shrink-0 h-full overflow-y-auto pointer-events-auto hidden md:block">
              <CardDeck />
            </div>
          )}
          <div className="flex-grow flex flex-col min-w-0 h-full relative pointer-events-auto bg-transparent">
            <div className="flex-grow flex flex-col min-h-0 overflow-hidden relative">
              {gameState?.winner && (
                <div className="absolute top-4 right-4 z-30 bg-rose-950/90 border-2 border-rose-500/80 px-4 py-2.5 rounded shadow-2xl animate-bounce flex items-center gap-3">
                  <Skull className="w-6 h-6 text-rose-500 shrink-0" />
                  <div className="flex flex-col">
                    <span className="font-sans font-black text-xs uppercase tracking-widest text-rose-100">
                      审判庭决议：终盘
                    </span>
                    <span className="font-mono text-[9px] text-slate-300 mt-0.5">
                      {gameState.winner === "WOLVES" ? "狼人肆虐 篡夺王庭" : "好人抱团 朝晖复苏"}
                    </span>
                  </div>
                </div>
              )}

              <SpeechConsole highlightSelfSeat={isSeatView} />
            </div>
          </div>

          {/* Right-side multi-module panel column */}
          {insightEnabled && !isSeatView && (
            <div className="w-[300px] shrink-0 pointer-events-auto overflow-y-auto py-3 pr-3 scrollbar-none">
              <RightPanelColumn runId={runId} />
            </div>
          )}
        </div>

        {/* ═══ Bottom: Narration bar + 纯文本记录 ═══ */}
        <div className="pointer-events-auto shrink-0">
          <div className="w-full bg-gradient-to-t from-black/70 via-black/50 to-transparent px-5 py-2.5 flex items-center gap-3 border-t border-white/5">
            <div className="w-7 h-7 rounded shrink-0 bg-red-950/40 border border-red-800/60 flex items-center justify-center text-red-500 font-serif font-black text-sm shadow-[0_0_10px_rgba(239,68,68,0.4)] animate-pulse">
              ☠
            </div>
            <div className="flex flex-col truncate min-w-0 flex-1">
              <span className="font-mono text-[10px] uppercase text-red-500 tracking-widest font-black leading-none mb-0.5 animate-pulse">
                [ 审判官裁决引导布告 ]
              </span>
              <p className="font-sans text-sm text-zinc-200 leading-tight font-bold truncate">
                {gameState?.narration || "幽暗城堡的丧钟敲响，所有人各就各位..."}
              </p>
            </div>
            <button
              onClick={() => {
                // trigger the pure text history overlay in SpeechConsole via a custom event
                window.dispatchEvent(new CustomEvent("toggle-pure-text-history"));
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700/50 rounded-lg font-mono text-xs text-zinc-300 uppercase tracking-widest transition-colors cursor-pointer shrink-0"
            >
              <MessageSquare className="w-4 h-4 text-yellow-500" />
              <span>纯文本记录 / {gameState?.speechLogs?.length ?? 0} 条</span>
            </button>
          </div>
        </div>
      </div>
      <div className={`absolute inset-x-0 top-0 h-2 bg-gradient-to-b pointer-events-none z-50 transition-colors duration-[2000ms] ${isNight ? "from-[#3b82f6]/40" : "from-[#f59e0b]/40"} to-transparent`} />
      <div className={`absolute inset-y-0 left-0 w-2 bg-gradient-to-r pointer-events-none z-50 transition-colors duration-[2000ms] ${isNight ? "from-[#8b5cf6]/30" : "from-[#d97706]/30"} to-transparent`} />
      <div className={`absolute inset-y-0 right-0 w-2 bg-gradient-to-l pointer-events-none z-50 transition-colors duration-[2000ms] ${isNight ? "from-[#8b5cf6]/30" : "from-[#d97706]/30"} to-transparent`} />
      <div className={`absolute inset-x-0 bottom-0 h-2 bg-gradient-to-t pointer-events-none z-50 transition-colors duration-[2000ms] ${isNight ? "from-[#3b82f6]/40" : "from-[#f59e0b]/40"} to-transparent`} />

      <PhaseTransitionCard />
      <GameAudioBridge />
      <AlertOverlays />
      <LiveCueAnchors />
      <CastSkillOverlay />
      {isSeatView && <IdentityHud />}
      {isSeatView && <SeatCommandDock />}
    </div>
  );
}
