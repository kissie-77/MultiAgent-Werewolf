import React from "react";
import { Link } from "react-router-dom";
import { Hammer, ArrowLeft, ShieldAlert } from "lucide-react";
import { motion } from "motion/react";

interface NotImplementedPageProps {
  title: string;
}

export default function NotImplementedPage({ title }: NotImplementedPageProps) {
  return (
    <div className="min-h-screen bg-[#07050d] text-zinc-100 flex flex-col items-center justify-center p-6 font-sans relative select-none antialiased">
      {/* Heavy woodcut border frame overlay */}
      <div className="absolute inset-4 pointer-events-none border border-zinc-800/60 rounded" />
      <div className="absolute inset-5 pointer-events-none border-2 border-zinc-950/85 rounded" />

      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 180, damping: 20 }}
        className="max-w-md w-full bg-zinc-950/90 border border-zinc-800 p-8 rounded-lg shadow-2xl text-center flex flex-col items-center gap-6 relative"
      >
        <div className="w-16 h-16 rounded-full bg-yellow-500/10 border-2 border-yellow-500 flex items-center justify-center text-yellow-500 animate-pulse">
          <Hammer className="w-8 h-8" />
        </div>

        <div className="space-y-2">
          <h1 className="text-xl font-bold tracking-widest text-[#facc15] font-sans uppercase">
            {title} ∙ 虚境铸造中
          </h1>
          <p className="font-mono text-[10px] text-zinc-400 uppercase tracking-widest">
            Arcane Hall: Under Construction
          </p>
        </div>

        <p className="text-xs text-zinc-400 leading-relaxed max-w-sm font-sans">
          关于该殿堂的规则条例、卷宗记录或细节，正由圣誓大法官连夜整理、雕刻成书。请静待下一次星盘重铸开启！
        </p>

        <div className="w-20 h-px bg-zinc-800" />

        <Link
          to="/"
          className="group px-6 py-2.5 font-sans font-bold text-xs uppercase tracking-wider text-black bg-yellow-500 hover:bg-yellow-400 rounded-lg shadow-lg/40 transition-transform transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer flex items-center justify-center gap-2"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
          返回法阵主殿 (BACK)
        </Link>
      </motion.div>
    </div>
  );
}
