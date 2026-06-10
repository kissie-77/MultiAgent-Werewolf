import React, { useEffect, useState } from "react";
import { Sun, Moon, Hourglass, LogOut, Home, BrainCircuit, MessageCircle, Swords } from "lucide-react";
import { useGameStore } from "../store";
import { stageBadge } from "../lib/phaseStage";
import { NIGHT_SUB_PHASE_LABEL } from "../lib/liveCue";
import { isRoleRevealed } from "../lib/humanPrompt";
import { soundManager } from "../audio/soundManager";
import AudioControls from "./AudioControls";

// ─────────────────────────────────────────────────────────
// Per-role flavor descriptions (never expose role name directly)
// key = Chinese role name, values = context-sensitive descriptions
// ─────────────────────────────────────────────────────────
const ROLE_ACTION_DESC: Record<
  string,
  {
    /** Shown while this player is thinking (e.g. planning speech, night decision) */
    thinking: string;
    /** Shown while this player is actively speaking */
    speaking: string;
    /** Shown while this player is performing a night skill (no thinking cue) */
    nightActing: string;
  }
> = {
  // ─── 狼人阵营 ───
  default: {
    thinking: "正在推演策略",
    speaking: "正在慷慨陈词",
    nightActing: "正在暗中行动",
  },
  Werewolf: {
    thinking: "正在谋划猎杀路线",
    speaking: "正在狡辩脱身",
    nightActing: "正在锁定猎杀目标",
  },
  AlphaWolf: {
    thinking: "正在运筹帷幄",
    speaking: "正在发号施令",
    nightActing: "正在部署突袭计划",
  },
  WhiteWolf: {
    thinking: "正在收敛锋芒",
    speaking: "正在与狼共舞",
    nightActing: "正在搜寻猎物气味",
  },
  WolfBeauty: {
    thinking: "正在编织魅惑之网",
    speaking: "正在施展妖媚之术",
    nightActing: "正在勾魂摄魄",
  },
  GuardianWolf: {
    thinking: "正在暗中戒备",
    speaking: "正在假意投诚",
    nightActing: "正在布置陷阱防线",
  },
  HiddenWolf: {
    thinking: "正在完美伪装",
    speaking: "正在混淆视听",
    nightActing: "正在阴影中潜行",
  },
  BloodMoonApostle: {
    thinking: "正在吟诵献祭咒文",
    speaking: "正在传播末日预言",
    nightActing: "正在准备血月仪式",
  },
  NightmareWolf: {
    thinking: "正在散播梦魇种子",
    speaking: "正在蛊惑人心",
    nightActing: "正在潜入他人梦境",
  },
  // ─── 好人阵营 ───
  Villager: {
    thinking: "正在凝神倾听",
    speaking: "正在表达朴素正义",
    nightActing: "正在安心休憩",
  },
  Seer: {
    thinking: "正在解读命运之线",
    speaking: "正在揭示真相",
    nightActing: "正在凝望命运之轮",
  },
  Witch: {
    thinking: "正在观察草药反应",
    speaking: "正在讲述草药古卷",
    nightActing: "正在调配神秘药剂",
  },
  Hunter: {
    thinking: "正在擦拭猎枪",
    speaking: "正在宣扬赏金正义",
    nightActing: "正在警戒四周动静",
  },
  Guard: {
    thinking: "正在规划夜间防线",
    speaking: "正在呼吁团结御敌",
    nightActing: "正在加固城池壁垒",
  },
  Idiot: {
    thinking: "正在装疯卖傻",
    speaking: "正在胡言乱语藏锋",
    nightActing: "正在痴笑望月",
  },
  Elder: {
    thinking: "正在翻阅古老卷轴",
    speaking: "正在讲述先祖智慧",
    nightActing: "正在闭目沉思",
  },
  Knight: {
    thinking: "正在磨砺剑刃",
    speaking: "正在宣誓光明正义",
    nightActing: "正在守护心中信念",
  },
  Magician: {
    thinking: "正在编织幻术迷雾",
    speaking: "正在真假难辨地发言",
    nightActing: "正在施展障眼秘法",
  },
  Raven: {
    thinking: "正在搜集可疑情报",
    speaking: "正在散布流言蜚语",
    nightActing: "正在标记猎物",
  },
  GraveyardKeeper: {
    thinking: "正在倾听亡者低语",
    speaking: "正在传达墓穴信息",
    nightActing: "正在守护安息之地",
  },
  // ─── 第三方 ───
  Cupid: {
    thinking: "正在拨弄命运之弦",
    speaking: "正在歌颂爱情力量",
    nightActing: "正在寻找心动之人",
  },
  Thief: {
    thinking: "正在物色下手目标",
    speaking: "正在鬼鬼祟祟试探",
    nightActing: "正在暗中窥视宝库",
  },
  Lover: {
    thinking: "正在心灵共鸣",
    speaking: "正在为爱辩护",
    nightActing: "正在与羁绊者共感",
  },
};

// Build a map: Chinese name -> descriptions
const DISPLAY_NAME_TO_ACTION: Record<string, { thinking: string; speaking: string; nightActing: string }> = {
  "平民":     ROLE_ACTION_DESC["Villager"],
  "预言家":   ROLE_ACTION_DESC["Seer"],
  "女巫":     ROLE_ACTION_DESC["Witch"],
  "猎人":     ROLE_ACTION_DESC["Hunter"],
  "守卫":     ROLE_ACTION_DESC["Guard"],
  "白痴":     ROLE_ACTION_DESC["Idiot"],
  "长老":     ROLE_ACTION_DESC["Elder"],
  "骑士":     ROLE_ACTION_DESC["Knight"],
  "魔术师":   ROLE_ACTION_DESC["Magician"],
  "乌鸦":     ROLE_ACTION_DESC["Raven"],
  "守墓人":   ROLE_ACTION_DESC["GraveyardKeeper"],
  "丘比特":   ROLE_ACTION_DESC["Cupid"],
  "盗贼":     ROLE_ACTION_DESC["Thief"],
  "恋人":     ROLE_ACTION_DESC["Lover"],
  "狼人":     ROLE_ACTION_DESC["Werewolf"],
  "狼王":     ROLE_ACTION_DESC["AlphaWolf"],
  "白狼":     ROLE_ACTION_DESC["WhiteWolf"],
  "狼美人":   ROLE_ACTION_DESC["WolfBeauty"],
  "守卫狼":   ROLE_ACTION_DESC["GuardianWolf"],
  "隐狼":     ROLE_ACTION_DESC["HiddenWolf"],
  "血月使徒": ROLE_ACTION_DESC["BloodMoonApostle"],
  "梦魇狼":   ROLE_ACTION_DESC["NightmareWolf"],
};

function getRoleActionDesc(role: string): { thinking: string; speaking: string; nightActing: string } {
  const r = (role ?? "").trim();
  if (!r) return ROLE_ACTION_DESC["default"];
  // Try direct key match
  if (ROLE_ACTION_DESC[r]) return ROLE_ACTION_DESC[r];
  // Try Chinese display name match
  if (DISPLAY_NAME_TO_ACTION[r]) return DISPLAY_NAME_TO_ACTION[r];
  return ROLE_ACTION_DESC["default"];
}

// ─────────────────────────────────────────────────────────
// Daytime / waiting generic descriptions by phase
// ─────────────────────────────────────────────────────────
const DAY_PHASE_DESC: Record<string, string> = {
  DAY_SHERIFF_RUN: "警徽角逐·竞选演说中",
  DAY_SHERIFF_VOTE: "警长封印·公投进行中",
  DAY_ANNOUNCEMENT: "审判布告·死讯宣读中",
  DAY_DEBATE: "圆形议事·辩驳交锋中",
  DAY_VOTE: "封印放逐·公投裁决中",
  GAME_OVER: "终局·审判庭已做出最终裁决",
};

// ─────────────────────────────────────────────────────────
// 进行中状态的「...」呼吸灯：三点错调淡入淡出（鎏金色），
// 接在中央牌框演员标签末尾，暗示「正在进行」。
// ─────────────────────────────────────────────────────────
function BreathingDots() {
  return (
    <span className="breathing-dots text-[#d4af37]" aria-hidden="true">
      <span className="breathing-dot" />
      <span className="breathing-dot" />
      <span className="breathing-dot" />
    </span>
  );
}

// ─────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────
export default React.memo(function UnifiedGameHeader({
  onExit,
  isLiveRun = false,
}: {
  onExit?: () => void | Promise<void>;
  isLiveRun?: boolean;
}) {
  const gameState = useGameStore((state) => state.state);
  const humanSeat = useGameStore((state) => state.humanSeat);
  const pendingInput = useGameStore((state) => state.pendingInput);
  const exitGame = useGameStore((state) => state.exitGame);

  const phase = gameState?.phase;
  const dayNumber = gameState?.dayNumber || 1;
  const liveCue = gameState?.liveCue;
  const thinkingCue = liveCue?.thinking ?? null;
  const currentSpeakerId = gameState?.currentSpeakerId;

  const [confirmExit, setConfirmExit] = useState(false);

  useEffect(() => {
    if (confirmExit) {
      const timer = setTimeout(() => setConfirmExit(false), 4000);
      return () => clearTimeout(timer);
    }
  }, [confirmExit]);

  if (!gameState) return null;

  const isSeatView = humanSeat != null;
  const isNight = phase?.startsWith("NIGHT") ?? false;
  const badge = phase ? stageBadge(phase, dayNumber) : null;

  // ─── Resolve phase sub-text (more granular than static label) ───
  const phaseSubText = (() => {
    if (!badge) return "";
    if (isNight && liveCue?.nightSubPhase) {
      const label = NIGHT_SUB_PHASE_LABEL[liveCue.nightSubPhase];
      return isSeatView ? "" : (label ?? liveCue.nightSubPhase);
    }
    if (liveCue?.sheriffStage && phase === "DAY_SHERIFF_RUN") return "警徽竞选·演说中";
    if (liveCue?.sheriffStage && phase === "DAY_SHERIFF_VOTE") return "警长封印·公投中";
    return badge.phaseText;
  })();

  // ─── Resolve center actor info ───
  type ActorInfo = {
    icon: typeof BrainCircuit;
    label: string;
    color: string;
    /** data attribute for animators */
    cueType: string;
  };

  const actorInfo: ActorInfo | null = (() => {
    // 1. Thinking (LLM is planning)
    if (thinkingCue) {
      const isNightThink =
        thinkingCue.context === "werewolf_chat" || thinkingCue.context === "night_skill";
      const isSheriffThink =
        thinkingCue.context === "sheriff_speech" || thinkingCue.context === "sheriff_vote";

      // Seat view human waits for own input: suppress indicator
      if (isSeatView && pendingInput && thinkingCue.seat === humanSeat) {
        return null;
      }

      // Seat view: hide night thinker identity entirely. `seat == null` is the
      // reducer's "identity withheld" marker — always treat it as anonymous night.
      if (isSeatView && (isNightThink || thinkingCue.seat == null)) {
        return {
          icon: BrainCircuit,
          label: "夜间推演中……",
          color: "text-violet-300",
          cueType: "thinking",
        };
      }

      // Build per-role / per-context description
      const roleAction = getRoleActionDesc(thinkingCue.role);
      let specific: string;
      if (isNightThink) {
        specific = roleAction.thinking;
      } else if (isSheriffThink) {
        specific =
          thinkingCue.context === "sheriff_speech" ? "正在准备竞选演说" : "正在斟酌投票人选";
      } else {
        specific = roleAction.thinking;
      }

      // Use "玩家N号" format — never expose the raw role name
      const label = `玩家${thinkingCue.seat}号 ${specific}`;
      return {
        icon: BrainCircuit,
        label,
        color: "text-yellow-300",
        cueType: "thinking",
      };
    }

    // 2. Currently speaking (player has the floor)
    if (currentSpeakerId != null) {
      const speaker = gameState.players.find((p) => p.id === currentSpeakerId);
      if (speaker) {
        const roleAction = getRoleActionDesc(speaker.role);
        const label = `玩家${currentSpeakerId}号 ${roleAction.speaking}`;
        return {
          icon: MessageCircle,
          label,
          color: "text-emerald-300",
          cueType: "speaking",
        };
      }
    }

    // 3. Night skill acting (frame active, no thinking cue)
    if (liveCue?.nightSkill) {
      const ns = liveCue.nightSkill;
      if (isSeatView) {
        return {
          icon: Swords,
          label: "夜间行动进行中……",
          color: "text-violet-300",
          cueType: "acting",
        };
      }
      const roleAction = getRoleActionDesc(ns.role);
      const label = `玩家${ns.seat}号 ${roleAction.nightActing}`;
      return {
        icon: Swords,
        label,
        color: "text-fuchsia-300",
        cueType: "acting",
      };
    }

    // 4. No actor — phase-level generic description
    return null;
  })();

  // ─── Cue fallback (only when no active actor) ───
  const cueFallback = (() => {
    if (!liveCue) return null;
    const { nightSubPhase, sheriffStage } = liveCue;
    if (sheriffStage) {
      return `警长阶段 · ${sheriffStage === "campaign" ? "竞选发言" : "投票"}`;
    }
    if (nightSubPhase && !isSeatView) {
      // Left section already shows the sub-phase name, center just says "行动中"
      return "夜间行动进行时…";
    }
    if (phase && DAY_PHASE_DESC[phase]) {
      return DAY_PHASE_DESC[phase];
    }
    return null;
  })();

  // ─── Theme tokens ───
  const isMoon = badge?.icon === "moon";
  const isWait = badge?.icon === "wait";

  // Phase dayText override for night with sub-phase
  const dayLabel = (() => {
    if (!badge) return "";
    if (isMoon) return `第 ${dayNumber} 夜`;
    if (isWait) return "候场集结";
    return `第 ${dayNumber} 日`;
  })();

  return (
    <div
      className="w-full h-12 bg-black/45 backdrop-blur-md border-b border-zinc-900/60 px-6 py-1.5 shrink-0 flex items-center justify-between relative z-10 shadow-md gap-4"
      data-unified-header
    >
      {/* ═══════════════ LEFT: logo + 标题 ═══════════════ */}
      <div className="flex items-center gap-1 shrink-0">
        <div className="w-1.5 h-5 bg-red-600" />
        <div className="w-0.5 h-5 bg-red-800" />
        <div className="hidden sm:flex flex-col ml-2 font-sans text-[9px] text-zinc-100 uppercase tracking-widest font-black leading-tight">
          <span>狼人杀神圣审判厅</span>
          <span className="text-[8px] text-zinc-500">{gameState.winner ? "已结案" : "对决轮转中"}</span>
        </div>
      </div>

      {/* ═══════════════ CENTER: 石碑法阵框(阶段 + 实况) ═══════════════ */}
      <div className="flex items-center min-w-0 flex-1 justify-center overflow-hidden">
        {badge ? (
          <div
            className="flex items-center gap-4 bg-black/55 border border-zinc-800/50 px-6 py-1 rounded relative shadow-[0_2px_4px_rgba(0,0,0,0.4)] max-w-full"
            style={{ clipPath: "polygon(0 0, 100% 0, 97% 100%, 3% 100%)" }}
            data-live-cue={actorInfo?.cueType ?? undefined}
          >
            {/* 阶段图标 */}
            {isMoon ? (
              <div className="w-7 h-7 rounded-full bg-black border-2 border-[#ef4444] flex items-center justify-center text-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)] shrink-0">
                <Moon className="w-4 h-4 fill-red-500 animate-pulse" />
              </div>
            ) : isWait ? (
              <div className="w-7 h-7 rounded-full bg-black border-2 border-zinc-600 flex items-center justify-center text-zinc-300 shrink-0">
                <Hourglass className="w-4 h-4 animate-spin" style={{ animationDuration: "3s" }} />
              </div>
            ) : (
              <div className="w-7 h-7 rounded-full bg-black border-2 border-yellow-500 flex items-center justify-center text-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.5)] shrink-0">
                <Sun className="w-4 h-4 animate-spin-slow" />
              </div>
            )}

            {/* 日期 + 阶段副标 */}
            <div className="flex flex-col shrink-0">
              <span className="font-serif font-black text-xs text-zinc-100 tracking-wider whitespace-nowrap">
                {dayLabel}
              </span>
              {phaseSubText && (
                <span className="font-mono text-[9px] text-[#eab308]/90 tracking-widest font-black uppercase whitespace-nowrap">
                  {phaseSubText}
                </span>
              )}
            </div>

            {/* 分隔 + 实况台词(现有 actorInfo / cueFallback 文案原样) */}
            {(actorInfo || cueFallback) && (
              <>
                <div className="w-px h-6 bg-zinc-700 shrink-0" />
                <div className="flex flex-col min-w-0 text-left">
                  <span
                    className={`font-mono text-[8px] text-red-500 font-black tracking-widest uppercase ${
                      actorInfo?.cueType === "thinking" ? "animate-pulse" : ""
                    }`}
                  >
                    — {actorInfo
                      ? actorInfo.cueType === "thinking"
                        ? "心证推演"
                        : actorInfo.cueType === "acting"
                        ? "神职行动"
                        : "法庭陈词"
                      : "法庭实况"} —
                  </span>
                  <p className="font-sans text-xs text-[#e0e0e0] font-black tracking-[0.14em] whitespace-nowrap leading-tight">
                    {actorInfo ? actorInfo.label : cueFallback}
                    {(actorInfo || phase !== "GAME_OVER") && <BreathingDots />}
                  </p>
                </div>
              </>
            )}
          </div>
        ) : (
          <span className="font-mono text-xs text-zinc-500 italic tracking-wider">
            {phaseSubText || (phase === "ROLE_CHOICE" && "宿命契约抉择") || "等待入场"}
          </span>
        )}
      </div>

      {/* ═══════════════ RIGHT: 文字按钮 + 存活统计 + 音量 ═══════════════ */}
      <div className="flex items-center gap-3 shrink-0">
        {/* 返回上一级 */}
        <button
          type="button"
          onClick={() => {
            soundManager.playUi("ui_click");
            window.history.back();
          }}
          className="h-7 px-2.5 rounded border border-zinc-800 transition-all duration-200 bg-zinc-950/30 hover:bg-zinc-900/50 text-zinc-400 text-[10px] font-mono hover:text-zinc-200 uppercase tracking-widest cursor-pointer whitespace-nowrap flex items-center gap-1.5"
        >
          返回上一级
        </button>

        {/* 回到主界面 */}
        <button
          type="button"
          onClick={() => {
            soundManager.playUi("ui_click");
            window.location.href = "/home";
          }}
          className="h-7 px-2.5 rounded border border-indigo-900/60 transition-all duration-200 bg-indigo-950/30 hover:bg-indigo-900/40 text-blue-200 text-[10px] font-mono hover:text-white uppercase tracking-widest cursor-pointer whitespace-nowrap flex items-center gap-1.5"
        >
          <Home className="w-3.5 h-3.5" />
          回到主界面
        </button>

        {/* 存活 / 死亡统计(参考版两行小字) */}
        <div className="text-right font-mono text-[9.5px] leading-tight hidden md:block">
          <div className="text-yellow-500 font-extrabold uppercase tracking-wider">
            存活已降临: {gameState.players.filter((p) => p.isAlive).length}名
          </div>
          <div className="text-red-600 font-black uppercase tracking-wider mt-0.5">
            已被撕咬放逐: {gameState.players.filter((p) => !p.isAlive).length}名
          </div>
        </div>

        {/* 退出游戏(二次确认状态机原样保留) */}
        <button
          type="button"
          onClick={() => {
            if (confirmExit) {
              soundManager.playUi("ui_submit");
              if (onExit) void onExit();
              else exitGame();
              setConfirmExit(false);
            } else {
              soundManager.playUi("ui_error");
              setConfirmExit(true);
            }
          }}
          title={confirmExit ? "再次点击确认退出" : "退出游戏"}
          className={`h-7 px-2.5 rounded border text-[10px] font-sans font-bold tracking-wider cursor-pointer flex items-center gap-1 transition-all duration-200 whitespace-nowrap ${
            confirmExit
              ? "border-red-500 bg-red-600 text-white shadow-[0_0_12px_rgba(239,68,68,0.4)] animate-pulse"
              : "border-red-900/60 bg-red-950/30 hover:bg-red-900/40 text-red-100 hover:text-white"
          }`}
        >
          <LogOut className="w-3 h-3" />
          <span>{confirmExit ? "二次点击确认退出" : "退出游戏"}</span>
        </button>

        {/* 音量控件(紧凑形态) */}
        <AudioControls compact />
      </div>
    </div>
  );
});
