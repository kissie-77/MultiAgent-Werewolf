import { AnimatePresence, motion } from "motion/react";
import type { InsightPlayer } from "../lib/insightMap";
import type { WolfCampMindV2 } from "../lib/godRoleIntel";
import GodRoleIntelPanel from "./GodRoleIntelPanel";

interface Props {
  matrices: WolfCampMindV2[];
  players: InsightPlayer[];
  round: number;
  isOpen: boolean;
  onToggle: () => void;
}

/**
 * god 视角第二栏：主面板左侧滑出，纵向堆叠每只狼的神职猜测矩阵。
 * 渲染在主面板 motion.div 内部（绝对定位 right-full），随主面板拖动作为整体单元移动。
 * 无存活狼（matrices 为空）→ 整体不渲染（连拉手都不出现）。
 */
export default function WolfGodRoleColumn({ matrices, players, round, isOpen, onToggle }: Props) {
  if (matrices.length === 0) return null;

  return (
    <div className="absolute right-full top-0 h-full flex items-stretch pointer-events-none">
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 360, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="pointer-events-auto overflow-hidden mr-1 rounded-l-xl border border-r-0 border-rose-900/40 bg-[#0c0a09]/95 shadow-[0_4px_24px_rgba(0,0,0,0.8)]"
            style={{ maxHeight: "calc(100vh - 4rem)" }}
          >
            <div
              className="overflow-y-auto overflow-x-hidden p-3 custom-scrollbar flex flex-col gap-3"
              style={{ width: 360, maxHeight: "calc(100vh - 4rem)" }}
            >
              <div className="text-rose-400 font-serif font-black text-xs uppercase tracking-widest flex items-center gap-2">
                🔪 狼·神职预测 <span className="text-rose-500/60 text-[10px] font-sans">R{round}</span>
              </div>
              {matrices.map((m) => (
                <GodRoleIntelPanel key={m.owner_seat} record={m} players={players} />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <button
        onClick={onToggle}
        title={isOpen ? "收起神职预测" : "展开神职预测"}
        className="pointer-events-auto self-center -ml-px w-5 py-3 rounded-l-md border border-r-0 border-rose-900/50 bg-[#0c0a09]/95 text-rose-400 hover:text-rose-300 hover:bg-rose-950/40 transition-colors flex items-center justify-center cursor-pointer"
      >
        <span className="text-[10px] leading-none" style={{ writingMode: "vertical-rl" }}>
          🔪{isOpen ? "▶" : "◀"}
        </span>
      </button>
    </div>
  );
}
