import React, { useState, useEffect } from "react";
import { ApiClient } from "../api/client";
import { HowToPlayPageData } from "../api/types";
import ContentPageLayout from "../components/ContentPageLayout";
import { motion } from "motion/react";
import { 
  Compass, 
  ShieldCheck, 
  ShieldAlert, 
  Clock, 
  HelpCircle,
  Loader2 
} from "lucide-react";

export default function HowToPlayPage() {
  const [data, setData] = useState<HowToPlayPageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    ApiClient.getHowToPlayPageData()
      .then((res) => {
        if (active) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          console.error(err);
          setError("虚境网络受到封魔阻隔，未寻获对决规则古卷。");
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
        <span className="font-mono text-xs tracking-widest uppercase">解封法碑规程法卷...</span>
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
        className="space-y-10"
      >
        {/* 1. Game Flow Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-900 pb-2">
            <span className="font-serif text-xs font-black tracking-widest text-[#eae5db] uppercase flex items-center gap-2">
              <Compass className="w-4 h-4 text-yellow-500 animate-spin-slow" />
              游戏四大循环步迹 (PHASE FLOW)
            </span>
            <span className="text-[10px] text-zinc-500 font-mono tracking-wider">LOOP PATTERNS</span>
          </div>

          <div className="relative pl-6 border-l border-zinc-900 space-y-6">
            {data.phase_flow.map((flowItem, index) => {
              const num = index + 1;
              return (
                <div key={index} className="relative group">
                  {/* Styled Node Dot representing the sequence status */}
                  <div className="absolute -left-[30px] top-1.5 w-4 h-4 rounded-full border border-yellow-600 bg-[#07050d] text-yellow-500/80 group-hover:bg-yellow-950 flex items-center justify-center text-[9px] font-mono font-bold transition-all">
                    {num}
                  </div>

                  <div className="bg-zinc-950/60 border border-zinc-900 rounded p-4 group-hover:border-zinc-800 transition-all">
                    <div className="flex flex-wrap items-center justify-between gap-3 mb-1.5">
                      <h4 className="font-serif text-sm font-bold text-zinc-200 tracking-wide">
                        {flowItem.phase}
                      </h4>
                      {flowItem.duration_hint && (
                        <span className="inline-flex items-center gap-1.2 text-[9px] font-mono text-yellow-700 bg-yellow-500/5 px-2 py-0.5 rounded border border-yellow-500/10">
                          <Clock className="w-3 h-3" />
                          {flowItem.duration_hint}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-zinc-400 font-sans leading-relaxed">
                      {flowItem.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 2. Victory Conditions Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-900 pb-2">
            <span className="font-serif text-xs font-black tracking-widest text-[#eae5db] uppercase">
              胜出裁定神格条件 (VICTORY CONDITIONS)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.victory_conditions.map((vc, index) => {
              const isEvil = vc.camp.includes("WOLVES") || vc.camp.includes("狼");
              return (
                <div 
                  key={index}
                  className={`border rounded p-5 relative overflow-hidden bg-zinc-950/40 ${
                    isEvil 
                      ? "border-red-950 hover:border-red-900/60" 
                      : "border-yellow-950/80 hover:border-yellow-900/60"
                  }`}
                >
                  {/* Camp Victory Emblem */}
                  <div className="flex items-center gap-2.5 mb-4 border-b border-zinc-900 pb-2.5">
                    <div className={`p-2 rounded ${
                      isEvil ? "bg-red-500/5 text-red-500 border border-red-500/15" : "bg-yellow-500/5 text-yellow-500 border border-yellow-500/15"
                    }`}>
                      {isEvil ? <ShieldAlert className="w-4 h-4" /> : <ShieldCheck className="w-4 h-4" />}
                    </div>
                    <div>
                      <span className="text-[9px] font-mono tracking-widest text-zinc-500 block uppercase leading-none mb-1">
                        {vc.camp}
                      </span>
                      <h4 className="font-serif text-sm font-black text-zinc-200 tracking-wider">
                        {vc.title}
                      </h4>
                    </div>
                  </div>

                  <ul className="space-y-3">
                    {vc.conditions.map((cond, cIdx) => (
                      <li key={cIdx} className="flex gap-2 text-xs text-zinc-400 leading-normal font-sans">
                        <span className={`font-mono text-xs ${isEvil ? "text-red-500" : "text-yellow-600"}`}>★</span>
                        <span>{cond}</span>
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
