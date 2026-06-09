import React, { useEffect, useState } from "react";
import { Sun, Moon, Hourglass, LogOut, Home, BrainCircuit, MessageCircle, Swords } from "lucide-react";
import { useGameStore } from "../store";
import { stageBadge } from "../lib/phaseStage";
import { NIGHT_SUB_PHASE_LABEL } from "../lib/liveCue";
import { isRoleRevealed } from "../lib/humanPrompt";

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

      // Seat view: hide night thinker identity entirely
      if (isSeatView && isNightThink) {
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
      className="w-full bg-gradient-to-b from-black/75 via-black/50 to-black/30 backdrop-blur-md border-b border-white/5 px-5 py-3 shrink-0 flex items-center justify-between relative z-10 shadow-[0_4px_24px_rgba(0,0,0,0.6)] gap-4"
      data-unified-header
    >
      {/* ═══════════════ LEFT: Icon + Day/Phase ═══════════════ */}
      {badge && (
        <div className="flex items-center gap-4 shrink-0 min-w-0">
          {/* Glowing icon */}
          <div
            className={`relative w-12 h-12 rounded-full border-2 flex items-center justify-center shrink-0 ${
              isMoon
                ? "border-red-500/60 bg-gradient-to-br from-red-950/40 to-black shadow-[0_0_20px_rgba(239,68,68,0.3)]"
                : isWait
                ? "border-zinc-600/50 bg-zinc-900/50"
                : "border-amber-500/60 bg-gradient-to-br from-amber-950/40 to-black shadow-[0_0_20px_rgba(245,158,11,0.3)]"
            }`}
          >
            {isMoon ? (
              <Moon className="w-6 h-6 text-red-400 animate-pulse fill-current drop-shadow-[0_0_6px_rgba(239,68,68,0.6)]" />
            ) : isWait ? (
              <Hourglass className="w-5 h-5 text-zinc-300 animate-spin" style={{ animationDuration: "3s" }} />
            ) : (
              <Sun className="w-6 h-6 text-amber-400 animate-spin-slow drop-shadow-[0_0_6px_rgba(245,158,11,0.6)]" />
            )}
          </div>

          {/* Day/night + phase */}
          <div className="flex flex-col leading-tight min-w-0">
            <span
              className={`font-serif font-black text-xl tracking-wider whitespace-nowrap ${
                isMoon
                  ? "text-red-100 drop-shadow-[0_0_8px_rgba(239,68,68,0.4)]"
                  : isWait
                  ? "text-zinc-300"
                  : "text-amber-100 drop-shadow-[0_0_8px_rgba(245,158,11,0.4)]"
              }`}
            >
              {dayLabel}
            </span>
            {phaseSubText && (
              <span
                className={`font-mono text-xs uppercase tracking-widest font-bold whitespace-nowrap mt-0.5 ${
                  isMoon
                    ? "text-violet-300/80"
                    : isWait
                    ? "text-zinc-500"
                    : "text-amber-300/80"
                }`}
              >
                {phaseSubText}
              </span>
            )}
          </div>
        </div>
      )}

      {/* separator */}
      <div className="w-px h-11 bg-white/8 shrink-0" />

      {/* ═══════════════ CENTER: Actor info / phase status ═══════════════ */}
      <div className="flex items-center gap-3 min-w-0 flex-1 justify-center overflow-hidden">
        {actorInfo && (
          <div
            className="bg-black border-2 border-[#eab308] px-5 py-1 rounded shadow-[3px_3px_0_#000] text-center max-w-full"
            data-live-cue={actorInfo.cueType}
          >
            <span
              className={`block font-mono text-[8px] text-red-500 font-black tracking-widest uppercase mb-0.5 ${
                actorInfo.cueType === "thinking" ? "animate-pulse" : ""
              }`}
            >
              — {actorInfo.cueType === "thinking"
                ? "心证推演"
                : actorInfo.cueType === "acting"
                ? "神职行动"
                : "法庭陈词"} —
            </span>
            <p className="font-serif text-sm text-[#e0e0e0] font-black tracking-[0.14em] whitespace-nowrap leading-tight">
              {actorInfo.label}
            </p>
          </div>
        )}

        {/* Fallback: generic cue when nobody is acting/speaking/thinking */}
        {!actorInfo && cueFallback && (
          <div className="bg-black border-2 border-[#eab308] px-5 py-1 rounded shadow-[3px_3px_0_#000] text-center max-w-full">
            <span className="block font-mono text-[8px] text-red-500 font-black tracking-widest uppercase mb-0.5">
              — 法庭实况 —
            </span>
            <p className="font-serif text-sm text-[#e0e0e0] font-black tracking-[0.14em] whitespace-nowrap leading-tight">
              {cueFallback}
            </p>
          </div>
        )}

        {!actorInfo && !cueFallback && (
          <span className="font-mono text-sm text-zinc-500 italic tracking-wider">
            {phaseSubText || (phase === "ROLE_CHOICE" && "宿命契约抉择") || (phase === "START_SCREEN" && "等待入场")}
          </span>
        )}
      </div>

      {/* separator */}
      <div className="w-px h-11 bg-white/8 shrink-0" />

      {/* ═══════════════ RIGHT: Stats + Buttons ═══════════════ */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Alive / Dead counts */}
        <div className="text-right font-mono text-xs leading-tight hidden md:block">
          <div className="text-emerald-400 font-extrabold uppercase tracking-wider">
            存活&nbsp;{gameState.players.filter((p) => p.isAlive).length}
          </div>
          <div className="text-red-400 font-black uppercase tracking-wider mt-0.5">
            死亡&nbsp;{gameState.players.filter((p) => !p.isAlive).length}
          </div>
        </div>

        {/* Navigation buttons */}
        <button
          type="button"
          onClick={() => window.history.back()}
          className="h-8 px-3 rounded-lg border border-white/10 bg-white/5 text-zinc-400 text-[11px] font-mono hover:text-white hover:bg-white/10 hover:border-white/20 cursor-pointer whitespace-nowrap flex items-center gap-1.5 transition-all duration-200"
        >
          返回
        </button>

        <button
          type="button"
          onClick={() => {
            window.location.href = "/home";
          }}
          className="h-8 px-3 rounded-lg border border-indigo-700/40 bg-indigo-950/30 text-indigo-300 text-[11px] font-mono hover:text-white hover:bg-indigo-900/40 hover:border-indigo-500/60 cursor-pointer whitespace-nowrap flex items-center gap-1.5 transition-all duration-200"
        >
          <Home className="w-3.5 h-3.5" />
          主页
        </button>

        <button
          type="button"
          onClick={() => {
            if (confirmExit) {
              onExit ? void onExit() : exitGame();
              setConfirmExit(false);
            } else {
              setConfirmExit(true);
            }
          }}
          className={`h-8 px-3 rounded-lg border text-[11px] font-sans font-bold tracking-wider cursor-pointer flex items-center gap-1.5 transition-all duration-200 ${
            confirmExit
              ? "border-red-500 bg-red-600 text-white shadow-[0_0_16px_rgba(239,68,68,0.4)] animate-pulse"
              : "border-red-800/40 bg-red-950/20 text-red-300 hover:text-white hover:bg-red-900/40 hover:border-red-600/60"
          }`}
        >
          <LogOut className="w-3.5 h-3.5" />
          {confirmExit ? "确认退出?" : "退出"}
        </button>
      </div>
    </div>
  );
});
