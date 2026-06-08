import React, { useState } from "react";
import { useGameStore } from "../store";
import { useGameInsight } from "../hooks/useGameInsight";
import NightActionLog from "./NightActionLog";
import BeliefMatrixPanel from "./BeliefMatrixPanel";
import ExposureRadarStrip from "./ExposureRadarStrip";
import WolfExposurePanel from "./WolfExposurePanel";
import { ChevronDown, ChevronUp, Loader2, Eye, EyeOff } from "lucide-react";

/* ─── Color scheme definitions ─── */
export type ColorScheme = "emerald" | "violet" | "amber" | "rose";

const CARD_COLORS: Record<
  ColorScheme,
  { header: string; chevron: string; body: string }
> = {
  emerald: {
    header:
      "border-emerald-700/50 text-emerald-400 bg-black/70 hover:bg-black/80",
    chevron: "text-emerald-500/60",
    body: "border-emerald-900/30 bg-black/50",
  },
  violet: {
    header:
      "border-violet-700/50 text-violet-300 bg-black/70 hover:bg-black/80",
    chevron: "text-violet-500/60",
    body: "border-violet-900/30 bg-black/50",
  },
  amber: {
    header:
      "border-amber-700/50 text-amber-400 bg-black/70 hover:bg-black/80",
    chevron: "text-amber-500/60",
    body: "border-amber-900/30 bg-black/50",
  },
  rose: {
    header:
      "border-rose-800/50 text-rose-400 bg-black/70 hover:bg-black/80",
    chevron: "text-rose-500/60",
    body: "border-rose-900/30 bg-black/50",
  },
};

/* ─── Collapsible card wrapper for each module ─── */
function CollapsibleCard({
  title,
  icon,
  colorScheme = "amber",
  defaultOpen = true,
  children,
  extraHeader,
}: {
  title: string;
  icon: string;
  colorScheme?: ColorScheme;
  defaultOpen?: boolean;
  children: React.ReactNode;
  extraHeader?: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const cc = CARD_COLORS[colorScheme];
  return (
    <div className="pointer-events-auto w-full">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center justify-between w-full px-3 py-2 ${cc.header} transition-colors cursor-pointer shrink-0 ${
          open ? "rounded-t-lg" : "rounded-lg"
        }`}
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[13px] shrink-0">{icon}</span>
          <span className="font-serif text-[11px] font-black tracking-[0.15em] uppercase whitespace-nowrap">
            {title}
          </span>
          {extraHeader}
        </div>
        {open ? (
          <ChevronUp className={`w-3.5 h-3.5 shrink-0 ${cc.chevron}`} />
        ) : (
          <ChevronDown className={`w-3.5 h-3.5 shrink-0 ${cc.chevron}`} />
        )}
      </button>
      <div
        className={`overflow-hidden transition-[max-height,opacity] duration-300 ease-in-out ${
          open ? "max-h-[600px] opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        <div className={`border-x border-b ${cc.body} rounded-b-lg px-3 py-2 max-h-[400px] overflow-y-auto`}>
          {children}
        </div>
      </div>
    </div>
  );
}

/* ─── Module 1: 存亡名录 ─── */
function AlivePlayerList() {
  const players = useGameStore((s) => s.state?.players ?? []);
  const alive = players.filter((p) => p.isAlive);
  return (
    <div className="flex flex-col gap-1">
      <span className="font-mono text-[10px] text-zinc-500 tracking-wider">
        存活 {alive.length}/{players.length}
      </span>
      <div className="flex flex-wrap gap-1.5">
        {alive.map((p) => (
          <span
            key={p.id}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-emerald-700/40 bg-emerald-950/30 text-emerald-300 font-mono text-[11px] font-bold"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            {p.name}
          </span>
        ))}
        {players
          .filter((p) => !p.isAlive)
          .map((p) => (
            <span
              key={p.id}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-zinc-800 bg-zinc-900/60 text-zinc-600 font-mono text-[11px] line-through"
            >
              {p.name}
            </span>
          ))}
      </div>
    </div>
  );
}

/* ─── Module 6 placeholder: 神机待测 ─── */
function PlaceholderCard({ title, icon, colorScheme }: { title: string; icon: string; colorScheme: ColorScheme }) {
  return (
    <CollapsibleCard title={title} icon={icon} colorScheme={colorScheme} defaultOpen={false}>
      <div className="flex flex-col items-center justify-center py-6 gap-2 text-zinc-600">
        <Loader2 className="w-4 h-4 animate-spin text-amber-500/30" />
        <span className="font-mono text-[10px] tracking-wider">等待数据流接入...</span>
      </div>
    </CollapsibleCard>
  );
}

/* ─── Root ─── */
export default React.memo(function RightPanelColumn({
  runId,
}: {
  runId: string | null;
}) {
  const { beliefs, voteSnapshot, players, speakerSeat } = useGameInsight(runId);
  const gameState = useGameStore((s) => s.state);
  const isLLMOnly = gameState?.gameMode === "llmOnly";
  const [showIdentities, setShowIdentities] = useState(true);
  const canShowIdentities = isLLMOnly && showIdentities;

  const roundLabel =
    beliefs && beliefs.length > 0 ? `R${beliefs[0].round}·昼` : "-";

  const dataReady = beliefs && voteSnapshot;

  return (
    <div className="flex flex-col gap-2 w-full">
      {/* ── 1. 存亡名录 ── */}
      <CollapsibleCard title="存亡名录" icon="👥" colorScheme="emerald" defaultOpen={true}>
        <AlivePlayerList />
      </CollapsibleCard>

      {/* ── 2. 暗夜行迹 ── */}
      <NightActionLog colorScheme="violet" defaultOpen={true} />

      {/* ── 3. 疑心矩阵 ── */}
      <CollapsibleCard
        title="疑心矩阵"
        icon="🔍"
        colorScheme="amber"
        defaultOpen={false}
        extraHeader={
          isLLMOnly ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setShowIdentities((v) => !v);
              }}
              className="flex items-center ml-1.5 px-1 py-0.5 rounded border border-amber-900/50 hover:bg-amber-900/30 text-amber-500/70 hover:text-amber-400 transition-colors"
            >
              {showIdentities ? (
                <EyeOff className="w-3 h-3" />
              ) : (
                <Eye className="w-3 h-3" />
              )}
            </button>
          ) : null
        }
      >
        {dataReady ? (
          <BeliefMatrixPanel
            beliefs={beliefs}
            players={players}
            roundLabel={roundLabel}
            scope="god"
            showIdentities={canShowIdentities}
            currentSpeakerSeat={speakerSeat}
          />
        ) : (
          <LoadingPlaceholder />
        )}
      </CollapsibleCard>

      {/* ── 4. 众矢之的 ── */}
      <CollapsibleCard title="众矢之的" icon="🎯" colorScheme="amber" defaultOpen={false}>
        {dataReady ? (
          <ExposureRadarStrip beliefs={beliefs} speakerSeat={speakerSeat} />
        ) : (
          <LoadingPlaceholder />
        )}
      </CollapsibleCard>

      {/* ── 5. 狼踪浮影 ── */}
      <CollapsibleCard title="狼踪浮影" icon="🐺" colorScheme="rose" defaultOpen={false}>
        {dataReady && canShowIdentities ? (
          <WolfExposurePanel beliefs={beliefs} players={players} />
        ) : (
          <div className="flex flex-col items-center justify-center py-4 gap-2 text-zinc-600">
            <span className="text-[10px] font-mono tracking-wider">
              {!isLLMOnly ? "仅观战模式可用" : "等待狼人身份数据..."}
            </span>
          </div>
        )}
      </CollapsibleCard>

      {/* ── 6. 神机待测（预留） ── */}
      <PlaceholderCard title="神机待测" icon="🔮" colorScheme="rose" />
    </div>
  );
});

function LoadingPlaceholder() {
  return (
    <div className="flex items-center justify-center py-4 gap-2 text-zinc-500">
      <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-500/40" />
      <span className="text-[10px] font-mono tracking-wider">洞察加载中...</span>
    </div>
  );
}
