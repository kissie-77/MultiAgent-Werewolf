import React, { useState } from "react";
import { useGameStore } from "../store";
import { useGameInsight } from "../hooks/useGameInsight";
import NightActionLog from "./NightActionLog";
import BeliefMatrixPanel from "./BeliefMatrixPanel";
import ExposureRadarStrip from "./ExposureRadarStrip";
import WolfExposurePanel from "./WolfExposurePanel";
import GodRoleIntelPanel from "./GodRoleIntelPanel";
import { soundManager } from "../audio/soundManager";
import { playToggle } from "../lib/uiSound";
import {
  ChevronDown,
  Loader2,
  Eye,
  EyeOff,
  Users,
  Crosshair,
  Footprints,
  Sparkles,
} from "lucide-react";

/* ─────────────────────────────────────────────────────────────
   Right-column modules wear the same restrained amber-on-obsidian
   panel chrome as the 信念矩阵 / 投票意向 insight panels:
     border-amber-900/30 · bg-[#0a0808]/90 · zinc-950 header bar ·
     gilt #d4af37 serif title · subtle stardust overlay.
   No heavy gold frames / corners — clean, scannable, cohesive.
   ───────────────────────────────────────────────────────────── */

const STARDUST =
  "bg-[url('https://www.transparenttextures.com/patterns/stardust.png')]";

/* ─── Collapsible amber panel wrapper for each module ─── */
function CollapsibleCard({
  title,
  icon,
  subtitle,
  defaultOpen = true,
  children,
  extraHeader,
}: {
  title: string;
  icon: React.ReactNode;
  subtitle?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  extraHeader?: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="flex flex-col border border-amber-900/30 bg-[#0a0808]/90 rounded-md overflow-hidden text-amber-100 font-sans shadow-[0_4px_20px_rgba(0,0,0,0.6)] text-[10px] relative pointer-events-auto">
      <div className={`absolute inset-0 pointer-events-none opacity-20 ${STARDUST} mix-blend-overlay`} />
      {/* header — div+role so the optional inner toggle button is valid HTML */}
      <div
        role="button"
        tabIndex={0}
        onClick={() => { playToggle(!open); setOpen((v) => !v); }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            playToggle(!open);
            setOpen((v) => !v);
          }
        }}
        className="flex justify-between items-center px-3 py-2 border-b border-amber-900/40 bg-zinc-950/80 relative z-10 cursor-pointer select-none hover:bg-zinc-900/70 transition-colors"
      >
        <div className="flex items-center gap-2 text-amber-500 min-w-0">
          <span className="shrink-0 flex items-center text-amber-500">{icon}</span>
          <span className="font-display-cn tracking-widest text-[#d4af37] whitespace-nowrap">
            {title}
          </span>
          {subtitle && (
            <span className="text-amber-500/80 text-[10px] font-sans border-l border-amber-900/50 pl-2 whitespace-nowrap">
              {subtitle}
            </span>
          )}
          {extraHeader}
        </div>
        <ChevronDown
          className={`w-3.5 h-3.5 shrink-0 text-amber-500/70 transition-transform duration-300 ${open ? "rotate-180" : ""}`}
        />
      </div>
      <div
        className={`relative z-10 overflow-hidden transition-[max-height,opacity] duration-300 ease-in-out ${
          open ? "max-h-[620px] opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        <div className="px-3 py-2.5 max-h-[400px] overflow-y-auto scrollbar-none">
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
    <div className="flex flex-col gap-1.5">
      <span className="font-mono text-[9px] tracking-[0.25em] uppercase text-amber-500/80">
        存活 {alive.length} / {players.length}
      </span>
      <div className="flex flex-wrap gap-1.5">
        {alive.map((p) => (
          <span
            key={p.id}
            className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded border border-amber-900/40 bg-amber-950/20 font-serif font-bold text-[11px] tracking-wide text-amber-200/90"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_#34d399] animate-pulse" />
            {p.name}
          </span>
        ))}
        {players
          .filter((p) => !p.isAlive)
          .map((p) => (
            <span
              key={p.id}
              className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded border border-zinc-800/70 bg-black/30 font-serif text-[11px] text-zinc-600 line-through decoration-rose-900/70"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-zinc-700" />
              {p.name}
            </span>
          ))}
      </div>
    </div>
  );
}

/* ─── Root ─── */
export default React.memo(function RightPanelColumn({
  runId,
}: {
  runId: string | null;
}) {
  const { beliefs, voteSnapshot, players, speakerSeat, wolfCampMinds } = useGameInsight(runId);
  const gameState = useGameStore((s) => s.state);
  const isLLMOnly = gameState?.gameMode === "llmOnly";
  const [showIdentities, setShowIdentities] = useState(true);
  const canShowIdentities = isLLMOnly && showIdentities;

  const roundLabel =
    beliefs && beliefs.length > 0 ? `R${beliefs[0].round}·昼` : "-";

  const dataReady = beliefs && voteSnapshot;

  return (
    <div className="flex flex-col gap-3 w-full" data-roster-font>
      {/* ── 1. 存亡名录 ── */}
      <CollapsibleCard title="存亡名录" icon={<Users className="w-3.5 h-3.5" />} defaultOpen={true}>
        <AlivePlayerList />
      </CollapsibleCard>

      {/* ── 2. 暗夜行迹 ── */}
      <NightActionLog defaultOpen={true} />

      {/* ── 3. 疑心矩阵 ── */}
      <CollapsibleCard
        title="疑心矩阵"
        icon={<Eye className="w-3.5 h-3.5" />}
        defaultOpen={false}
        extraHeader={
          isLLMOnly ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                soundManager.playUi("ui_click");
                setShowIdentities((v) => !v);
              }}
              className="flex items-center ml-1.5 px-1.5 py-0.5 rounded border border-amber-900/50 hover:bg-amber-900/30 text-amber-500/80 hover:text-amber-400 focus:outline-none transition-colors"
              title={showIdentities ? "隐藏身份" : "显示身份"}
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
      <CollapsibleCard title="众矢之的" icon={<Crosshair className="w-3.5 h-3.5" />} defaultOpen={false}>
        {dataReady ? (
          <ExposureRadarStrip beliefs={beliefs} speakerSeat={speakerSeat} />
        ) : (
          <LoadingPlaceholder />
        )}
      </CollapsibleCard>

      {/* ── 5. 狼踪浮影 ── */}
      <CollapsibleCard title="狼踪浮影" icon={<Footprints className="w-3.5 h-3.5" />} defaultOpen={false}>
        {dataReady && canShowIdentities ? (
          <WolfExposurePanel beliefs={beliefs} players={players} />
        ) : (
          <GatedPlaceholder text={!isLLMOnly ? "仅观战模式可用" : "等待狼人身份数据……"} />
        )}
      </CollapsibleCard>

      {/* ── 6. 神机待测（狼队上帝视角推理矩阵） ── */}
      <CollapsibleCard title="神机待测" icon={<Sparkles className="w-3.5 h-3.5" />} defaultOpen={false}>
        {wolfCampMinds && Object.keys(wolfCampMinds).length > 0 ? (
          <div className="flex flex-col gap-2">
            {Object.values(wolfCampMinds).map((m) => (
              <GodRoleIntelPanel key={m.owner_seat} record={m} players={players} />
            ))}
          </div>
        ) : (
          <GatedPlaceholder text="等待狼队推理数据……" />
        )}
      </CollapsibleCard>
    </div>
  );
});

function LoadingPlaceholder() {
  return (
    <div className="flex items-center justify-center py-5 gap-2.5">
      <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-500/60" />
      <span className="text-[10px] font-serif tracking-[0.2em] uppercase text-amber-500/70">
        洞察推演中……
      </span>
    </div>
  );
}

function GatedPlaceholder({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-5 gap-2">
      <Loader2 className="w-4 h-4 animate-spin text-amber-500/40" />
      <span className="text-[10px] font-serif tracking-[0.18em] text-amber-500/70">
        {text}
      </span>
    </div>
  );
}
