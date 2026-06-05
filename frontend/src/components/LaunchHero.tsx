import { Link } from "react-router-dom";
import { motion } from "motion/react";
import { Flame, ScrollText, Swords, ChevronRight } from "lucide-react";

export default function LaunchHero() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 15 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="relative z-10 w-full max-w-lg px-4 text-center select-none"
    >
      <div className="absolute top-2 left-2 font-mono text-[10px] text-zinc-600">🕀</div>
      <div className="absolute top-2 right-2 font-mono text-[10px] text-zinc-600">🕀</div>
      <div className="absolute bottom-2 left-2 font-mono text-[10px] text-zinc-600">✝</div>
      <div className="absolute bottom-2 right-2 font-mono text-[10px] text-zinc-600">✝</div>

      <div className="mb-4 inline-block border border-zinc-800 bg-zinc-900/80 px-3 py-1 font-mono text-[9px] uppercase tracking-[0.25em] text-yellow-500">
        🔮 诸神交错 · 狼月落尘 🔮
      </div>

      <h1 className="font-serif text-4xl font-black uppercase tracking-[0.2em] text-[#e5e5e0] ink-shadow md:text-5xl">
        宿命审判
      </h1>

      <p className="mx-auto mt-4 max-w-md font-mono text-[11px] leading-relaxed tracking-wide text-zinc-400">
        在大理石圆盘刻纹与微温烛台前，多 Agent 狼人杀对局于此上演。
        观战、复盘、评测——一切从这张圆桌开始。
      </p>

      <div className="mt-8 flex flex-col items-stretch gap-3 sm:flex-row sm:justify-center">
        <Link
          to="/game"
          className="stone-btn group relative flex items-center justify-center gap-3 rounded px-8 py-4 font-serif text-base font-black uppercase tracking-[0.2em] text-[#f5f5f5] shadow-2xl transition-all active:translate-y-1"
          style={{ clipPath: "polygon(4% 0%, 96% 0%, 100% 18%, 100% 100%, 0% 100%, 0% 18%)" }}
        >
          <Flame className="h-5 w-5 text-red-500 group-hover:animate-bounce" />
          <span>进入对局</span>
          <ChevronRight className="h-4 w-4 text-yellow-500" />
        </Link>

        <Link
          to="/features"
          className="flex items-center justify-center gap-2 rounded border border-zinc-800 bg-black/50 px-6 py-4 font-mono text-[10px] font-bold uppercase tracking-widest text-zinc-300 transition-colors hover:border-purple-500/50 hover:text-purple-200"
        >
          <ScrollText className="h-4 w-4" />
          了解能力
        </Link>
      </div>

      <div className="mt-10 grid grid-cols-3 gap-3 border-t border-zinc-900/80 pt-6">
        {[
          { icon: Swords, label: "12 人标准局", sub: "多 Agent 协作" },
          { icon: Flame, label: "赛后复盘", sub: "PostGame 14 步" },
          { icon: ScrollText, label: "Skill 进化", sub: "跨局策略沉淀" },
        ].map(({ icon: Icon, label, sub }) => (
          <div key={label} className="rounded border border-zinc-900/60 bg-black/30 px-2 py-3">
            <Icon className="mx-auto mb-1.5 h-4 w-4 text-purple-400" />
            <div className="font-mono text-[9px] font-bold uppercase tracking-wider text-zinc-200">{label}</div>
            <div className="mt-0.5 font-mono text-[8px] text-zinc-600">{sub}</div>
          </div>
        ))}
      </div>

      <p className="mt-6 font-mono text-[8px] uppercase tracking-widest text-zinc-600">
        — 浮雕圆盘静静旋转，等待入局 —
      </p>
    </motion.div>
  );
}
