import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { GameState } from "../types";
import { Trophy, Star, Skull, Heart, Shield, RefreshCw, Eye, Flame, ShieldAlert, Award, LogOut, Users, BrainCircuit, Loader2 } from "lucide-react";
import { motion } from "motion/react";
import { ApiClient } from "../api/client";
import { isPostGameReady, replayPathFor } from "../lib/settlement";
import type { ReplayPageData } from "../api/types";
import { resolveMvpView, resolveBoard, resolveWinnerIsGood, isWolfRole } from "../lib/gameOver";
import { soundManager } from "../audio/soundManager";
import AudioControls from "./AudioControls";

const POST_GAME_POLL_INTERVAL_MS = 2500;

interface GameOverPanelProps {
  gameState: GameState;
  onRestart: (role: "预言家" | "女巫" | "猎人" | "狼人" | "村民") => void;
  onExit: () => void;
  /** Backend run id for spectated/web games; enables real post-game polling + replay link. */
  runId?: string | null;
  /** The human's seat (seat view) so the MVP/board can mark the "本人" badge. */
  userSeat?: number | null;
}

// 根据 MVP 角色生成史诗级标题（覆盖中文显示名；未知则用通用标题）
function getMVPTitle(role: string) {
  switch (role) {
    case "预言家":
    case "Seer":
      return { title: "星宿指路人", description: "洞察宿命幽邃，真视天眼常开；凭借绝对推理彻底驱逐暗夜孤狼！" };
    case "女巫":
    case "Witch":
      return { title: "生死掌命者", description: "极光圣水起死回生，见血封喉荡平黑暗；妙手挽星盘于将倾！" };
    case "猎人":
    case "Hunter":
      return { title: "末日执行官", description: "铁血银弹武装威慑，钢枪最后一子弹不屈出击，陪葬仇敌黄昏！" };
    default:
      if (isWolfRole(role)) {
        return { title: "暗夜狂噬领主", description: "獠牙无情撕咬光明，以极致诡辩愚弄整座圆桌议会，篡夺至高王权！" };
      }
      return { title: "至臻明镜神探", description: "以凡人之躯并无畏之光，在迷雾中抽丝剥茧，斩断阴影迷瘴！" };
  }
}

export default function GameOverPanel({ gameState, onRestart, onExit, runId, userSeat }: GameOverPanelProps) {
  const [postGameReady, setPostGameReady] = useState(false);
  const [backendReplay, setBackendReplay] = useState<ReplayPageData | null>(null);

  // 对于后端支持的对局，轮询游戏状态直到对局产物就位
  // 然后启用真正的深度复盘链接并拉取权威的 MVP/排行榜
  //（座位 SSE 路径没有客户端阵容，且客户端 MVP 重新计算是
  // 错误的 — 见 lib/gameOver。本地对局（无 runId）跳过此步骤）
  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const poll = async () => {
      try {
        const status = await ApiClient.getGameStatus(runId);
        if (cancelled) return;
        if (isPostGameReady(status)) {
          setPostGameReady(true);
          try {
            const replay = await ApiClient.getReplayData(runId);
            if (!cancelled) setBackendReplay(replay);
          } catch {
            // replay fetch failed; the panel still renders (client/placeholder)
          }
          return; // ready — stop polling
        }
      } catch {
        // transient error (run still settling) — keep polling
      }
      if (!cancelled) {
        timer = setTimeout(poll, POST_GAME_POLL_INTERVAL_MS);
      }
    };
    poll();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [runId]);

  if (!gameState || !gameState.winner) return null;

  const seat = userSeat ?? null;
  const mvp = resolveMvpView(backendReplay, gameState, seat);
  const board = resolveBoard(backendReplay, gameState.players, seat);
  const isGoodWin = resolveWinnerIsGood(backendReplay, gameState);
  const mvpDetails = mvp ? getMVPTitle(mvp.role) : null;
  // backend runs whose post-game hasn't landed yet have no roster to reveal.
  const settlementPending = !mvp && board.length === 0;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="absolute inset-0 z-50 overflow-y-auto bg-black/90 backdrop-blur-md flex flex-col justify-between p-6 md:p-8 text-zinc-100 font-sans pointer-events-auto"
    >
      {/* 音量键 —— 结算遮罩盖住了顶栏，这里补一个 */}
      <AudioControls className="absolute top-4 right-4 z-[60]" />

      {/* Decorative Woodcut borders */}
      <div className="absolute inset-4 pointer-events-none border border-yellow-600/35 rounded z-0" />
      <div className="absolute inset-5 pointer-events-none border border-zinc-800/80 rounded z-0" />

      {/* Top Banner Area */}
      <div className="text-center mt-4 mb-4 relative z-10 shrink-0">
        <motion.div
          initial={{ y: -20 }}
          animate={{ y: 0 }}
          transition={{ type: "spring", stiffness: 200, damping: 15 }}
          className="inline-block"
        >
          {isGoodWin ? (
            <div className="flex flex-col items-center gap-1.5">
              <div className="w-16 h-16 rounded-full bg-yellow-500/10 border-2 border-yellow-500 flex items-center justify-center text-yellow-500 animate-pulse shadow-[0_0_20px_rgba(234,179,8,0.3)]">
                <Shield className="w-10 h-10" />
              </div>
              <h1 className="text-3xl font-black tracking-[0.2em] font-sans text-yellow-500 mt-2 uppercase text-shadow-glow">
                朝 晖 复 苏 ∙ 好 人 捷 报
              </h1>
              <p className="font-mono text-[10px] text-zinc-400 uppercase tracking-widest mt-0.5">
                Dawn Awakens: The Sacred Alliance of Light Prevails
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-1.5">
              <div className="w-16 h-16 rounded-full bg-red-650/15 border-2 border-red-500 flex items-center justify-center text-red-500 animate-pulse shadow-[0_0_20px_rgba(239,68,68,0.3)]">
                <Skull className="w-10 h-10" />
              </div>
              <h1 className="text-3xl font-black tracking-[0.2em] font-sans text-red-500 mt-2 uppercase text-shadow-glow-red">
                暗 夜 魔 啸 ∙ 狼 人 暴 虐
              </h1>
              <p className="font-mono text-[10px] text-zinc-400 uppercase tracking-widest mt-0.5">
                Moonless Eclipse: The Lycan Bloodline Conquers All
              </p>
            </div>
          )}
        </motion.div>
      </div>

      {/* Main Content Dashboard Area */}
      <div className="flex-grow flex flex-col lg:flex-row items-stretch justify-center gap-6 max-w-7xl mx-auto w-full relative z-10 shrink-0 select-none pb-4">

        {/* LEFT COLUMN: MVP Feature Card */}
        <motion.div
          initial={{ x: -30, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ delay: 0.15 }}
          className="w-full lg:w-[420px] shrink-0 bg-zinc-950/90 border-2 border-yellow-500/80 rounded-lg p-6 flex flex-col justify-between shadow-2xl relative"
        >
          {/* Subtle star elements or crown icon */}
          <div className="absolute top-3 left-4 flex gap-1 text-yellow-500 text-[10px] font-mono tracking-widest">
            <Star className="w-3.5 h-3.5 fill-current" />
            <span>CRITICAL_DECISION_UNIT</span>
          </div>
          <div className="absolute top-2 right-4 text-xs font-serif text-yellow-500/40">★ ★ ★</div>

          {mvp && mvpDetails ? (
            <>
              <div className="flex-grow flex flex-col items-center justify-center text-center py-6">
                <div className="relative mb-4">
                  <div className="w-24 h-24 rounded-full border-4 border-yellow-500/90 overflow-hidden bg-[#1a1205] shadow-[0_0_25px_rgba(234,179,8,0.25)] flex items-center justify-center">
                    <span className="text-5xl font-mono text-yellow-500 font-extrabold">{mvp.id}</span>
                  </div>
                  <div className="absolute -bottom-2 -right-1 bg-yellow-500 text-black font-sans font-black text-[9px] px-2 py-0.5 rounded shadow-lg uppercase tracking-wider flex items-center gap-0.5">
                    <Award className="w-3 h-3 text-black fill-current" />
                    MVP
                  </div>
                </div>

                <span className="text-[10px] font-mono tracking-widest uppercase text-yellow-500/80 bg-yellow-500/10 border border-yellow-600/35 px-2.5 py-0.5 rounded-full mb-2">
                  —— {mvpDetails.title} ——
                </span>

                <h2 className="text-xl font-black tracking-wide text-zinc-100 font-sans">
                  {mvp.name} ({mvp.id}号席位)
                </h2>
                <p className="text-[10px] text-zinc-400 font-mono mt-1.5">
                  宿命身份: <span className="text-yellow-500 font-bold">{mvp.role}</span> {mvp.isUser ? " | ( 体验决策者 )" : " | ( 虚境智能 AI )"}
                </p>

                <div className="w-12 h-0.5 bg-yellow-600/35 my-4" />

                <blockquote className="text-xs text-zinc-200/95 font-serif italic max-w-sm leading-relaxed px-4 bg-zinc-900/50 p-4 rounded border border-zinc-800/50">
                  “ {mvpDetails.description} ”
                </blockquote>
              </div>

              <div className="border-t border-zinc-900/80 pt-4 flex flex-col gap-2">
                <div className="flex justify-between items-center text-[10px] font-mono text-zinc-400">
                  <span>本局执念誓约:</span>
                  <span className="text-zinc-200">{mvp.role}</span>
                </div>
                <div className="flex justify-between items-center text-[10px] font-mono text-zinc-400">
                  <span>生命留存形态:</span>
                  <span className={mvp.isAlive ? "text-emerald-400 font-bold" : "text-red-500 font-bold"}>
                    {mvp.isAlive ? "🟢 驻留人间 (ALIVE)" : "💀 寂灭魂归 (DECIMATED)"}
                  </span>
                </div>
                <div className="flex justify-between items-center text-[10px] font-mono text-zinc-400">
                  <span>议案主导演讲:</span>
                  <span className="text-zinc-200">发表 {mvp.speechCount} 轮发言</span>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-grow flex flex-col items-center justify-center text-center py-10 gap-3">
              <Loader2 className="w-8 h-8 text-yellow-500 animate-spin" />
              <span className="text-[11px] font-mono tracking-widest uppercase text-zinc-400">
                {settlementPending ? "结算评选生成中…" : "MVP 评选生成中…"}
              </span>
              <span className="text-[10px] font-sans text-zinc-600">深度复盘就绪后自动填充本局 MVP 与底牌</span>
            </div>
          )}
        </motion.div>

        {/* RIGHT COLUMN: Full Board Identities揭幕 */}
        <motion.div
          initial={{ x: 30, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="flex-grow bg-zinc-950/80 border border-zinc-900/70 p-6 rounded-lg flex flex-col justify-between"
        >
          <div>
            <h3 className="text-sm font-black font-sans text-zinc-300 uppercase tracking-widest border-b border-zinc-900 pb-3 mb-4 flex items-center gap-2">
              <Star className="w-4 h-4 text-yellow-500" />
              圆形议政厅 ∙ 宿命之镜底牌曝白
            </h3>

            {/* Players Grid */}
            {board.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {board.map((player) => {
                  const isMVP = mvp != null && player.id === mvp.id;
                  const isWolf = isWolfRole(player.role);

                  return (
                    <motion.div
                      key={player.id}
                      className={`p-3.5 rounded border flex flex-col justify-between gap-1.5 transition-all bg-zinc-950/95 shadow-md relative overflow-hidden ${
                        isMVP
                          ? "border-yellow-500/80 ring-1 ring-yellow-500/30"
                          : "border-zinc-900"
                      }`}
                    >
                      {/* Role badge */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded-full bg-zinc-900 border border-zinc-800 text-[10px] text-zinc-300 flex items-center justify-center font-black font-mono">
                            {player.id}
                          </span>
                          <span className="font-sans font-bold text-xs text-zinc-200">
                            {player.name}
                          </span>
                        </div>
                        <span className={`text-[9px] font-serif font-black px-1.5 py-0.5 rounded border uppercase ${
                          isWolf
                            ? "bg-red-950/60 text-red-400 border-red-900/40"
                            : (player.role === "村民" || player.role === "平民" || player.role === "Villager")
                              ? "bg-zinc-900 text-zinc-400 border-zinc-800"
                              : "bg-indigo-950/60 text-indigo-300 border-indigo-900/40"
                        }`}>
                          {player.role}
                        </span>
                      </div>

                      <div className="text-[10px] text-zinc-500 font-mono leading-relaxed mt-1 line-clamp-2">
                        “ {player.statusNotes || "在法阵中沉稳论证，审视迷云。"} ”
                      </div>

                      <div className="border-t border-zinc-950 pt-2 mt-1 flex justify-between items-center text-[9px] font-mono">
                        <span className={player.isAlive ? "text-emerald-500" : "text-zinc-600"}>
                          {player.isAlive ? "🟢 常驻阳世" : "💀 宿命陨落"}
                        </span>
                        {player.isUser && (
                          <span className="text-[8.5px] text-yellow-500/90 font-sans tracking-wide uppercase px-1 border border-yellow-500/30 rounded bg-yellow-500/5">
                            体验者 (You)
                          </span>
                        )}
                      </div>

                      {isMVP && (
                        <div className="absolute top-0 right-0 w-8 h-8 pointer-events-none overflow-hidden">
                          <div className="absolute top-0 right-0 transform translate-x-4 -rotate-45 block bg-yellow-500 w-12 text-center text-[7px] text-black font-black uppercase tracking-tighter">
                            MVP
                          </div>
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 gap-2 text-zinc-500">
                <Loader2 className="w-6 h-6 animate-spin text-zinc-600" />
                <span className="text-[10px] font-sans tracking-widest">底牌曝白生成中…</span>
              </div>
            )}
          </div>

          {/* Interactive Logs timeline drawer summary for context */}
          <div className="border-t border-zinc-900/80 pt-4 mt-6">
            <h4 className="text-[10px] font-sans text-zinc-500 tracking-widest mb-2">本局法阵辩论要项摘要</h4>
            <div className="max-h-24 overflow-y-auto border border-zinc-900 rounded p-2.5 bg-zinc-950/60 flex flex-col gap-1.5 relative scroll-thin">
              {gameState.speechLogs.map((log, index) => (
                <div key={index} className="text-[9.5px] font-mono text-zinc-400 leading-normal border-b border-zinc-900/40 pb-1 flex gap-2">
                  <span className="text-yellow-500/85 shrink-0">[{log.isNight ? "夜间" : `第${log.day}日`} - {log.playerName.replace(/\(.*?\)/g, "").trim()}]:</span>
                  <span className="italic">“ {log.content.length > 55 ? `${log.content.slice(0, 55)}...` : log.content} ”</span>
                </div>
              ))}
              {gameState.speechLogs.length === 0 && (
                <span className="text-zinc-600 text-[10px] font-sans italic">未留下显著星盘神言。</span>
              )}
            </div>
          </div>
        </motion.div>
      </div>

      {/* Restart/Replay Buttons Deck */}
      <div className="text-center relative z-10 py-4 shrink-0 flex flex-col items-center gap-3">
        <h4 className="text-[9.5px] text-zinc-500 font-mono tracking-widest uppercase">
          — 宿命交织的下一场轮回 已经在大门外敲响 —
        </h4>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <button
            onClick={() => { soundManager.playUi("ui_click"); onRestart("预言家"); }}
            className="group relative px-6 py-2.5 font-sans font-black text-[10px] uppercase tracking-wider text-black bg-yellow-500 hover:bg-yellow-400 border border-yellow-700/60 rounded shadow-lg transition-transform transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5 group-hover:rotate-180 transition-transform duration-500" />
            重铸星盘 ∙ 预言家开局
          </button>

          <button
            onClick={() => { soundManager.playUi("ui_click"); onRestart("女巫"); }}
            className="group relative px-6 py-2.5 font-sans font-black text-[10px] uppercase tracking-wider text-white bg-fuchsia-850 hover:bg-fuchsia-750 border border-fuchsia-800/40 rounded shadow-lg transition-transform transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer flex items-center gap-1.5 bg-fuchsia-900"
          >
            <Heart className="w-3.5 h-3.5" />
            重铸星盘 ∙ 女巫开局
          </button>

          <button
            onClick={() => { soundManager.playUi("ui_click"); onRestart("猎人"); }}
            className="group relative px-6 py-2.5 font-sans font-black text-[10px] uppercase tracking-wider text-white bg-teal-850 hover:bg-teal-750 border border-teal-800/40 rounded shadow-lg transition-transform transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer flex items-center gap-1.5 bg-emerald-800"
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            重铸星盘 ∙ 猎人开局
          </button>

          <button
            onClick={() => { soundManager.playUi("ui_click"); onRestart("村民"); }}
            className="group relative px-6 py-2.5 font-sans font-black text-[10px] uppercase tracking-wider text-white bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded shadow-lg transition-transform transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer flex items-center gap-1.5"
          >
            <Users className="w-3.5 h-3.5" />
            重铸星盘 ∙ 村民开局
          </button>

          <button
            onClick={() => { soundManager.playUi("ui_click"); onRestart("狼人"); }}
            className="group relative px-6 py-2.5 font-sans font-black text-[10px] uppercase tracking-wider text-white bg-red-850 hover:bg-red-750 border border-red-800/40 rounded shadow-lg transition-transform transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer flex items-center gap-1.5 bg-red-950"
          >
            <Flame className="w-3.5 h-3.5" />
            重铸星盘 ∙ 狼人开局
          </button>

          {runId ? (
            postGameReady ? (
              <Link
                to={replayPathFor(runId)}
                onClick={() => soundManager.playUi("ui_click")}
                className="group relative px-6 py-2.5 font-sans font-black text-[10px] uppercase tracking-wider text-zinc-950 bg-yellow-500 hover:bg-yellow-400 border border-yellow-600 rounded shadow-lg transition-transform transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer flex items-center gap-1.5 text-center font-bold"
              >
                <BrainCircuit className="w-3.5 h-3.5 animate-pulse" />
                查看本局高维深度复盘
              </Link>
            ) : (
              <span
                aria-disabled="true"
                title="复盘数据生成中，请稍候…"
                className="group relative px-6 py-2.5 font-sans font-black text-[10px] uppercase tracking-wider text-zinc-400 bg-zinc-900 border border-zinc-700 rounded shadow-lg cursor-wait opacity-70 flex items-center gap-1.5 text-center font-bold"
              >
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                深度复盘生成中…
              </span>
            )
          ) : (
            <Link
              to={`/replay/run-gameover-${gameState.winner?.toLowerCase()}`}
              onClick={() => soundManager.playUi("ui_click")}
              className="group relative px-6 py-2.5 font-sans font-black text-[10px] uppercase tracking-wider text-zinc-950 bg-yellow-500 hover:bg-yellow-400 border border-yellow-600 rounded shadow-lg transition-transform transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer flex items-center gap-1.5 text-center font-bold"
            >
              <BrainCircuit className="w-3.5 h-3.5 animate-pulse" />
              查看本局高维深度复盘
            </Link>
          )}

          <button
            onClick={() => { soundManager.playUi("ui_click"); onExit(); }}
            className="group relative px-6 py-2.5 font-sans font-black text-[10px] uppercase tracking-wider text-zinc-300 bg-zinc-950 border border-zinc-800 hover:bg-zinc-900 hover:text-white hover:border-zinc-500 rounded shadow-lg transition-transform transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer flex items-center gap-1.5"
          >
            <LogOut className="w-3.5 h-3.5" />
            退出游戏
          </button>
        </div>
      </div>
    </motion.div>
  );
}
