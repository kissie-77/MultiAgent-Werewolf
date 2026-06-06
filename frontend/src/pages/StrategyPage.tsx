import React, { useState, useEffect } from "react";
import { ApiClient } from "../api/client";
import { StrategyPageData } from "../api/types";
import ContentPageLayout from "../components/ContentPageLayout";
import { motion } from "motion/react";
import { 
  Flame, 
  Compass, 
  ShieldCheck, 
  ShieldAlert, 
  BookOpen, 
  Fingerprint,
  Calendar,
  Loader2 
} from "lucide-react";

export default function StrategyPage() {
  const [data, setData] = useState<StrategyPageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    ApiClient.getStrategyPageData()
      .then((res) => {
        if (active) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          console.error(err);
          setError("虚空网络被封阻，无法索取全智能圆桌战术册。");
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center text-zinc-400">
        <Loader2 className="w-8 h-8 animate-spin text-yellow-500 mb-2" />
        <span className="font-mono text-xs tracking-widest uppercase">召来智武巅峰战策卷...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center text-center p-4">
        <p className="text-sm font-mono text-stone-500 tracking-wider mb-2">{error || "数据载入失败"}</p>
      </div>
    );
  }

  return (
    <ContentPageLayout
      title={data.title}
      subtitle={data.subtitle}
      description={data.description}
      sections={data.sections}
    >
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-10 font-sans"
      >
        {/* 1. General Tips */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-900 pb-2">
            <span className="font-serif text-xs font-black tracking-widest text-[#eae5db] uppercase flex items-center gap-2">
              <Flame className="w-4 h-4 text-orange-500 animate-pulse" />
              圆桌通识秘守 (GENERAL ADVICE)
            </span>
          </div>

          <div className="space-y-3">
            {data.general_tips.map((tip, idx) => {
              const parts = tip.split("】");
              const title = parts[0]?.replace("【", "") || "";
              const body = parts[1] || "";
              return (
                <div key={idx} className="bg-zinc-950/60 border border-zinc-900 rounded p-4 text-xs relative flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-yellow-500/5 text-yellow-500 flex items-center justify-center font-mono font-bold border border-yellow-500/10 mt-0.5">
                    {idx + 1}
                  </div>
                  <div className="flex-grow space-y-1">
                    <span className="font-serif font-bold text-[#eae5db] block text-[13px]">
                      {title}
                    </span>
                    <p className="text-zinc-400 font-sans leading-relaxed">
                      {body}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 2. Chronological Phase tips */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-900 pb-2">
            <span className="font-serif text-xs font-black tracking-widest text-[#eae5db] uppercase flex items-center gap-2">
              <Calendar className="w-4 h-4 text-zinc-500" />
              对局阶程战术 (PHASE STRATEGY)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.phase_tips.map((pt, idx) => (
              <div key={idx} className="bg-zinc-950/60 border border-zinc-900 rounded p-5 space-y-3 hover:border-zinc-800 transition-all">
                <span className="text-[10px] font-mono text-zinc-500 block uppercase tracking-widest border-b border-zinc-900 pb-1.5 flex items-center gap-1.5">
                  <span className="text-yellow-600 font-bold">★</span>
                  {pt.phase}
                </span>
                <ul className="space-y-2 text-xs">
                  {pt.tips.map((tip, tIdx) => (
                    <li key={tIdx} className="text-zinc-400 font-sans leading-relaxed flex gap-2">
                      <span className="text-yellow-700 font-mono">•</span>
                      <span>{tip}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* 3. Micro Roles Tips */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-900 pb-2">
            <span className="font-serif text-xs font-black tracking-widest text-[#eae5db] uppercase flex items-center gap-2">
              <Fingerprint className="w-4 h-4 text-zinc-500" />
              神圣权能微操建议 (ROLE SPECIALIZATION)
            </span>
          </div>

          <div className="space-y-4">
            {data.role_tips.map((rt, idx) => (
              <div key={idx} className="bg-zinc-950/70 border border-zinc-900/60 rounded p-5 relative overflow-hidden transition-colors hover:border-zinc-800">
                <div className="flex items-center gap-2 mb-3">
                  <span className="px-2.5 py-0.5 text-[9px] font-mono tracking-widest bg-yellow-500/5 text-yellow-500 border border-yellow-500/10 rounded uppercase">
                    {rt.role}
                  </span>
                </div>
                <ul className="space-y-2">
                  {rt.tips.map((tip, tIdx) => (
                    <li key={tIdx} className="text-xs text-zinc-400 font-sans leading-relaxed flex gap-2">
                      <span className="text-yellow-600 font-mono">▸</span>
                      <span>{tip}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* 4. Camps tips */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-900 pb-2">
            <span className="font-serif text-xs font-black tracking-widest text-[#eae5db] uppercase flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-zinc-500 animate-spin-slow" />
              阵营宏观对抗术 (CAMP-LEVEL STRATEGEMS)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.role_tips_by_camp.map((campTip, idx) => {
              const isEvil = campTip.camp.includes("WOLVES") || campTip.camp.includes("狼");
              return (
                <div 
                  key={idx}
                  className={`border rounded p-5 bg-zinc-950/40 relative overflow-hidden hover:border-zinc-800 transition-all ${
                    isEvil ? "border-red-950" : "border-yellow-950/80"
                  }`}
                >
                  <div className="flex items-center gap-2 border-b border-zinc-900 pb-2.5 mb-3.5">
                    <div className={`p-1.5 rounded ${isEvil ? "bg-red-500/5 text-red-500" : "bg-yellow-500/5 text-yellow-500"}`}>
                      {isEvil ? <ShieldAlert className="w-4 h-4" /> : <ShieldCheck className="w-4 h-4" />}
                    </div>
                    <span className="font-serif text-xs font-black text-zinc-200 tracking-wider">
                      {campTip.camp}
                    </span>
                  </div>

                  <ul className="space-y-2.5">
                    {campTip.tips.map((tip, tIdx) => (
                      <li key={tIdx} className="text-xs text-zinc-400 leading-relaxed font-sans flex gap-2">
                        <span className={`font-mono text-xs ${isEvil ? "text-red-500" : "text-yellow-600"}`}>★</span>
                        <span>{tip}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        </div>
      </motion.div>
    </ContentPageLayout>
  );
}
