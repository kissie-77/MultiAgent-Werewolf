import React from "react";
import { Sparkles, Wand2, LayoutGrid } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import type { BoardPresetOption, PlayableRoleOption } from "../api/types";
import {
  effectivePlayableRoles,
  lineupSummary,
  presetsByKind,
  roleDisplayName,
  roleOptionLabel,
  sortedRoleOptions,
  standardLineupForCount,
  validateCustomLineup,
} from "../lib/roleCatalog";

export type BoardSetupMode = "curated" | "standard" | "custom";

export default React.memo(function BoardSetupPanel({
  mode,
  onModeChange,
  presets,
  playableRoles,
  selectedPresetId,
  onSelectPreset,
  customLineup,
  onCustomLineupChange,
  playerCount,
  onPlayerCountChange,
}: {
  mode: BoardSetupMode;
  onModeChange: (m: BoardSetupMode) => void;
  presets: BoardPresetOption[];
  playableRoles: PlayableRoleOption[];
  selectedPresetId: string;
  onSelectPreset: (id: string) => void;
  customLineup: string[];
  onCustomLineupChange: (lineup: string[]) => void;
  playerCount: number;
  onPlayerCountChange: (n: number) => void;
}) {
  const rolePool = effectivePlayableRoles(playableRoles);
  const roleOptions = sortedRoleOptions(playableRoles);
  const { curated, standard } = presetsByKind(presets);
  const customError = mode === "custom" ? validateCustomLineup(customLineup, playableRoles) : null;

  const activeLineup =
    mode === "custom"
      ? customLineup
      : mode === "curated"
        ? presets.find((p) => p.preset_id === selectedPresetId)?.role_names ?? []
        : standard.find((p) => p.player_count === playerCount)?.role_names
          ?? standardLineupForCount(playerCount);

  return (
    <div className="flex flex-col gap-3">
      <span className="font-serif text-[11px] text-amber-500 font-bold tracking-[0.2em] flex items-center gap-2">
        <span className="font-gothic text-amber-700 text-sm">II.</span> 席位编排{" "}
        <span className="font-gothic text-xs uppercase opacity-70 ml-1">Player Seats</span>
        <span className="inline-block h-px flex-grow bg-gradient-to-r from-amber-900/50 to-transparent ml-2" />
      </span>

      <div className="grid grid-cols-3 gap-2">
        {(
          [
            { id: "standard" as const, label: "标准", icon: LayoutGrid },
            { id: "curated" as const, label: "主题", icon: Sparkles },
            { id: "custom" as const, label: "自选", icon: Wand2 },
          ] as const
        ).map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => onModeChange(id)}
            className={`flex items-center justify-center gap-1.5 py-2 rounded border text-[10px] font-bold tracking-widest transition-all duration-200 ${
              mode === id
                ? "bg-amber-500/15 border-amber-500/50 text-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.08)]"
                : "bg-black/40 border-slate-800 text-slate-500 hover:border-amber-900/40"
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      <div className="rounded border border-slate-800/80 bg-black/30 overflow-hidden">
        <AnimatePresence mode="wait" initial={false}>
          {mode === "standard" && (
            <motion.div
              key="standard"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              className="p-4 flex flex-col gap-3"
            >
              <p className="text-[9px] text-zinc-500 text-center font-sans shrink-0">
                按人数自动分配二十二种身份中的标准组合
              </p>
              <div className="w-full flex items-center justify-between shrink-0">
                <button
                  type="button"
                  onClick={() => onPlayerCountChange(playerCount - 1)}
                  className="w-10 h-10 rounded border border-slate-700 hover:border-amber-500/50 hover:bg-amber-500/10 flex items-center justify-center font-bold text-lg text-slate-400 hover:text-amber-400"
                >
                  -
                </button>
                <div className="flex flex-col items-center">
                  <span className="text-3xl font-serif font-black text-amber-500">{playerCount}</span>
                  <span className="text-[8px] text-slate-500 uppercase tracking-widest mt-1">入局人数</span>
                </div>
                <button
                  type="button"
                  onClick={() => onPlayerCountChange(playerCount + 1)}
                  className="w-10 h-10 rounded border border-slate-700 hover:border-amber-500/50 hover:bg-amber-500/10 flex items-center justify-center font-bold text-lg text-slate-400 hover:text-amber-400"
                >
                  +
                </button>
              </div>
              <div className="flex flex-wrap gap-2 justify-center shrink-0">
                {[6, 8, 9, 12, 16].map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => onPlayerCountChange(n)}
                    className={`px-3 py-1.5 rounded text-[10px] font-mono border transition-colors ${
                      playerCount === n
                        ? "bg-amber-500/20 text-amber-400 border-amber-500/50"
                        : "text-slate-500 border-slate-700 hover:border-amber-900/50"
                    }`}
                  >
                    {n} 人局
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {mode === "curated" && (
            <motion.div
              key="curated"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              className="p-2 flex flex-col gap-2 max-h-56 overflow-y-auto custom-scrollbar"
            >
              {curated.length === 0 ? (
                <span className="text-[10px] text-zinc-500 p-2 font-sans">暂无主题局，请使用标准或自选</span>
              ) : (
                curated.map((p) => (
                  <button
                    key={p.preset_id}
                    type="button"
                    onClick={() => onSelectPreset(p.preset_id)}
                    className={`text-left p-3 rounded border transition-all shrink-0 ${
                      selectedPresetId === p.preset_id
                        ? "border-amber-500/50 bg-amber-900/20"
                        : "border-slate-800 hover:border-amber-900/40 bg-black/30"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="text-[11px] font-bold text-amber-200">{p.title}</span>
                      <span className="text-[9px] text-zinc-500 font-mono">{p.player_count} 人</span>
                    </div>
                    <p className="text-[9px] text-zinc-500 leading-relaxed mb-1.5 font-sans">{p.description}</p>
                    <p className="text-[9px] text-amber-500/80 font-mono leading-relaxed">
                      {lineupSummary(p.role_names, rolePool)}
                    </p>
                  </button>
                ))
              )}
            </motion.div>
          )}

          {mode === "custom" && (
            <motion.div
              key="custom"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              className="p-3 flex flex-col gap-2 max-h-56 overflow-y-auto custom-scrollbar"
            >
              <div className="flex items-center justify-between mb-1 gap-2 shrink-0">
                <span className="text-[10px] text-zinc-500 font-sans">为每个席位指定身份</span>
                <select
                  value={customLineup.length}
                  onChange={(e) => {
                    const n = Number(e.target.value);
                    onCustomLineupChange(
                      Array.from({ length: n }, (_, i) => customLineup[i] ?? "Villager"),
                    );
                  }}
                  className="bg-black/60 border border-slate-700 text-amber-100 text-[10px] px-2 py-1 rounded shrink-0"
                >
                  {Array.from({ length: 15 }, (_, i) => i + 6).map((n) => (
                    <option key={n} value={n}>
                      {n} 人局
                    </option>
                  ))}
                </select>
              </div>
              {customLineup.map((roleKey, index) => (
                <div key={index} className="flex items-center gap-2 shrink-0">
                  <span className="text-[10px] text-zinc-600 w-8 shrink-0 font-mono">{index + 1} 号</span>
                  <select
                    value={roleKey}
                    onChange={(e) => {
                      const next = [...customLineup];
                      next[index] = e.target.value;
                      onCustomLineupChange(next);
                    }}
                    className="flex-1 min-w-0 bg-black/60 border border-slate-700 text-amber-100 text-[11px] px-2 py-2 rounded font-sans"
                  >
                    {roleOptions.map((r) => (
                      <option key={`${index}-${r.key}`} value={r.key}>
                        {roleOptionLabel(r)}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
              {customError && (
                <p className="text-[10px] text-red-400 font-sans shrink-0">{customError}</p>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="px-3 py-2 bg-slate-900/60 border border-slate-800 rounded text-[10px] text-slate-400 shrink-0">
        <span className="text-slate-500 mr-2 font-serif">本局身份:</span>
        <span className="text-amber-100/90 font-mono leading-relaxed">
          {activeLineup.length > 0 ? lineupSummary(activeLineup, rolePool) : "—"}
        </span>
      </div>
    </div>
  );
})

export { roleDisplayName };
