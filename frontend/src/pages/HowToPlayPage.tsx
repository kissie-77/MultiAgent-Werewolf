import React, { useState, useEffect } from "react";
import { ApiClient } from "../api/client";
import { HowToPlayPageData } from "../api/types";
import { motion } from "motion/react";
import {
  BookOpen,
  Compass,
  ShieldCheck,
  ShieldAlert,
  Loader2,
  Sparkles,
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
          setError("规则内容加载失败，请稍后重试。");
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
        <span className="font-mono text-xs tracking-widest uppercase">加载游戏规则...</span>
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
    <div className="max-w-4xl mx-auto px-4 py-12 md:py-16">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center space-y-3 mb-10"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-zinc-950 border border-zinc-900 rounded-full text-[9px] font-mono text-yellow-500 uppercase tracking-widest">
          <Sparkles className="w-3 h-3" />
          GAME RULES
        </div>
        <h1 className="text-3xl md:text-4xl font-extrabold uppercase tracking-widest font-sans bg-clip-text bg-gradient-to-r from-zinc-100 to-yellow-600 text-transparent">
          {data.title}
        </h1>
        <p className="text-xs text-zinc-400 max-w-2xl mx-auto leading-relaxed">{data.subtitle}</p>
        <div className="w-16 h-px bg-zinc-800 mx-auto" />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-8"
      >
        {data.sections.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 border-b border-zinc-900 pb-2">
              <BookOpen className="w-4 h-4 text-yellow-500" />
              <h2 className="text-xs font-mono font-bold uppercase tracking-widest text-zinc-300">
                基本说明
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.sections.map((section, index) => (
                <div
                  key={index}
                  className="bg-zinc-950/80 border border-zinc-900 rounded-lg p-5 hover:border-zinc-800 transition-colors"
                >
                  <h3 className="text-sm font-bold text-zinc-200 mb-2">{section.title}</h3>
                  <p className="text-xs text-zinc-400 leading-relaxed whitespace-pre-line">
                    {section.value}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-4">
          <div className="flex items-center gap-2 border-b border-zinc-900 pb-2">
            <Compass className="w-4 h-4 text-yellow-500" />
            <h2 className="text-xs font-mono font-bold uppercase tracking-widest text-zinc-300">
              游戏流程
            </h2>
          </div>
          <div className="relative pl-6 border-l border-zinc-900 space-y-5">
            {data.phase_flow.map((flowItem, index) => (
              <div key={index} className="relative">
                <div className="absolute -left-[30px] top-1 w-4 h-4 rounded-full border border-yellow-600 bg-zinc-950 text-yellow-500 flex items-center justify-center text-[9px] font-mono font-bold">
                  {index + 1}
                </div>
                <div className="bg-zinc-950/60 border border-zinc-900 rounded-lg p-4">
                  <h4 className="text-sm font-bold text-zinc-200 mb-1">{flowItem.phase}</h4>
                  <p className="text-xs text-zinc-400 leading-relaxed">{flowItem.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-2 border-b border-zinc-900 pb-2">
            <ShieldCheck className="w-4 h-4 text-yellow-500" />
            <h2 className="text-xs font-mono font-bold uppercase tracking-widest text-zinc-300">
              胜利条件
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.victory_conditions.map((vc, index) => {
              const isEvil = vc.camp.includes("狼");
              return (
                <div
                  key={index}
                  className={`border rounded-lg p-5 bg-zinc-950/40 ${
                    isEvil ? "border-red-950/80" : "border-yellow-950/60"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-3">
                    {isEvil ? (
                      <ShieldAlert className="w-4 h-4 text-red-500" />
                    ) : (
                      <ShieldCheck className="w-4 h-4 text-yellow-500" />
                    )}
                    <div>
                      <span className="text-[9px] font-mono text-zinc-500 uppercase block">
                        {vc.camp}
                      </span>
                      <h4 className="text-sm font-bold text-zinc-200">{vc.title}</h4>
                    </div>
                  </div>
                  <ul className="space-y-2">
                    {vc.conditions.map((cond, cIdx) => (
                      <li key={cIdx} className="flex gap-2 text-xs text-zinc-400 leading-relaxed">
                        <span className={isEvil ? "text-red-500" : "text-yellow-600"}>•</span>
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
    </div>
  );
}
