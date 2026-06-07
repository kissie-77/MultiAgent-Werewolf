import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiClient } from "../api/client";
import { ModelDetail } from "../api/types";
import { ArrowLeft, Brain, Cpu, MessageSquare, ShieldCheck, ShieldAlert, Sparkles, Star } from "lucide-react";
import { motion } from "motion/react";

export default function ModelDetailPage() {
  const { modelId } = useParams<{ modelId: string }>();
  const [model, setModel] = useState<ModelDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!modelId) return;
    let active = true;

    ApiClient.getModelDetail(modelId)
      .then((data) => {
        if (active) {
          setModel(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          console.error(err);
          setError("命运卷宗残破，星盘上可能并无此款智脑刻痕，亦或传输错误。");
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [modelId]);

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center text-zinc-400 font-mono text-xs uppercase tracking-widest gap-2">
        <div className="w-6 h-6 border-2 border-t-yellow-500 border-zinc-900 rounded-full animate-spin" />
        <span>校阅虚境智脑规格卷宗...</span>
      </div>
    );
  }

  if (error || !model) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center text-center p-6 gap-6 relative">
        <div className="absolute inset-10 border border-red-500/10 pointer-events-none rounded" />
        <Brain className="w-14 h-14 text-yellow-500/60 animate-pulse" />
        <div className="space-y-1">
          <h2 className="text-lg font-bold font-sans uppercase tracking-widest text-zinc-200">智脑已失散在虚无星河</h2>
          <p className="text-zinc-500 font-sans text-xs max-w-sm">{error || "未在审判会成员中寻获此模型特征。"}</p>
        </div>
        <Link
          to="/models"
          className="px-5 py-2.5 bg-zinc-950 border border-zinc-800 text-xs font-mono text-zinc-300 hover:border-yellow-550 hover:text-white rounded"
        >
          返回智脑主廊 (BACK)
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-12 md:py-16">
      {/* Back button */}
      <div className="mb-8">
        <Link
          to="/models"
          className="inline-flex items-center gap-2 text-xs font-mono tracking-widest uppercase text-zinc-400 hover:text-yellow-500 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          返回虚境智脑主廊
        </Link>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-zinc-950/90 border border-zinc-900 rounded shadow-2xl overflow-hidden p-6 md:p-10 space-y-10"
      >
        {/* Header Title section */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-zinc-905 pb-8">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-[10px] font-mono text-yellow-500 uppercase tracking-widest">
              <Cpu className="w-3.5 h-3.5 text-yellow-500" />
              {model.developer} 对弈推理主星位
            </div>
            <h1 className="text-2xl md:text-3xl font-black font-sans uppercase tracking-wider text-zinc-100">
              {model.name}
            </h1>
            <p className="text-xs text-zinc-400 leading-relaxed max-w-2xl font-sans">
              {model.description}
            </p>
          </div>

          <div className="bg-zinc-900/60 border border-zinc-850 p-4 rounded-lg flex flex-col items-start md:items-end gap-1 shrink-0">
            <div className="flex items-center gap-1 text-yellow-500 font-mono font-bold text-lg">
              <Star className="w-4.5 h-4.5 fill-current" />
              <span>ELO {model.rating}</span>
            </div>
            <span className="text-[10px] font-mono text-zinc-500 uppercase">
              首选偏爱: <span className="text-zinc-200">{model.primaryRolePreference}</span>
            </span>
          </div>
        </div>

        {/* Dynamic specifications cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-zinc-900/40 border border-zinc-900 p-4 rounded">
            <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest block">推理硬核全参</span>
            <span className="text-xs font-mono text-zinc-200 block font-bold mt-1">
              {model.parameters || "未知参数"}
            </span>
          </div>
          <div className="bg-zinc-900/40 border border-zinc-900 p-4 rounded">
            <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest block">高维多模感知 (VISION)</span>
            <span className="text-xs font-mono block font-bold mt-1 uppercase text-zinc-200">
              {model.visionSupport ? "解封 ∙ 触碰迷雾图像" : "封锁 ∙ 纯逻辑论述"}
            </span>
          </div>
          <div className="bg-zinc-900/40 border border-zinc-900 p-4 rounded">
            <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest block">黑夜最长鸣响</span>
            <span className="text-xs font-mono text-zinc-200 block font-bold mt-1">
              {model.maxTokens} Max Tokens
            </span>
          </div>
        </div>

        {/* Double column details */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          
          {/* Strengths / Weaknesses in Left 7 Columns */}
          <div className="lg:col-span-7 space-y-8">
            
            {/* Strengths */}
            <div className="space-y-3">
              <div className="flex items-center gap-2 border-b border-zinc-900 pb-1.5">
                <ShieldCheck className="w-4.5 h-4.5 text-emerald-450" />
                <h3 className="text-xs font-mono font-extrabold uppercase tracking-widest text-zinc-300">
                  高维圣印 ∙ 核心长处 (STRENGTHS)
                </h3>
              </div>
              <ul className="space-y-2.5">
                {model.strengths.map((str, i) => (
                  <li key={i} className="flex gap-2 text-xs text-zinc-400 leading-relaxed font-sans">
                    <span className="text-emerald-400 font-mono font-bold shrink-0">✔</span>
                    <span>{str}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Weaknesses */}
            <div className="space-y-3">
              <div className="flex items-center gap-2 border-b border-zinc-900 pb-1.5">
                <ShieldAlert className="w-4.5 h-4.5 text-red-500" />
                <h3 className="text-xs font-mono font-extrabold uppercase tracking-widest text-zinc-300">
                  宿命死角 ∙ 逻辑破绽 (WEAKNESSES)
                </h3>
              </div>
              <ul className="space-y-2.5">
                {model.weaknesses.map((weak, i) => (
                  <li key={i} className="flex gap-2 text-xs text-zinc-400 leading-relaxed font-sans">
                    <span className="text-red-500 font-mono font-bold shrink-0">✘</span>
                    <span>{weak}</span>
                  </li>
                ))}
              </ul>
            </div>

          </div>

          {/* Right Area: Radar stats & temperament in 5 Columns */}
          <div className="lg:col-span-5 space-y-8">
            
            {/* Combat Stats Progress lists */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 border-b border-zinc-900 pb-1.5">
                <Sparkles className="w-4 h-4 text-yellow-500" />
                <h3 className="text-xs font-mono font-extrabold uppercase tracking-widest text-zinc-300">
                  智性星图权能比 (PROPERTIES)
                </h3>
              </div>

              <div className="space-y-3.5">
                {[
                  { label: "解构深度 (Logic Reasoning)", val: model.radarStats.logic, color: "bg-indigo-500/80" },
                  { label: "战术伪饰 (Deception / Blur)", val: model.radarStats.deception, color: "bg-red-500/80" },
                  { label: "白昼煽动 (Persuasion / Voice)", val: model.radarStats.persuasion, color: "bg-yellow-500/80" },
                  { label: "同盟协同 (Cooperation / Team)", val: model.radarStats.cooperation, color: "bg-emerald-500/80" },
                  { label: "流离抗推 (Survivability)", val: model.radarStats.survivability, color: "bg-rose-500/80" },
                ].map((stat) => (
                  <div key={stat.label} className="space-y-1">
                    <div className="flex justify-between text-[11px] font-mono">
                      <span className="text-zinc-400 capitalize">{stat.label}</span>
                      <span className="text-zinc-200 font-bold">{stat.val}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-zinc-900 rounded-full overflow-hidden">
                      <div className={`h-full ${stat.color} rounded-full`} style={{ width: `${stat.val}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Temperament summary */}
            <div className="space-y-2 bg-zinc-900/30 p-4 border border-zinc-900 rounded">
              <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">词锋脾性 (TEMPERAMENT)</span>
              <p className="text-xs font-sans text-zinc-350 leading-relaxed font-semibold">
                {model.temperament}
              </p>
            </div>

          </div>

        </div>

        {/* Sample Quote Dialogue Box */}
        <div className="space-y-3 bg-[#0d0a14] border border-[#a855f7]/20 p-6 rounded-lg relative overflow-hidden">
          <div className="absolute top-1 right-2 text-violet-800 font-mono text-[70px] leading-none select-none opacity-20 font-serif">
            “
          </div>

          <div className="flex items-center gap-2 text-violet-400 text-[10px] font-mono uppercase tracking-widest">
            <MessageSquare className="w-3.5 h-3.5" />
            审判庭现场辩证对话实录 (TRIAL SPOKEN RECORD)
          </div>

          <blockquote className="text-xs text-zinc-300 leading-relaxed font-serif italic relative z-10 pl-3 border-l-2 border-[#a855f7]/55">
            {model.sampleQuote}
          </blockquote>
        </div>

        {/* Symmetrical footer */}
        <div className="pt-6 border-t border-zinc-905 flex justify-between items-center text-[9px] font-mono text-zinc-650">
          <span>COSMIC DECISION INTEL v2.1</span>
          <span>ARCANUM MODEL REGISTERED</span>
        </div>
      </motion.div>
    </div>
  );
}
