import React, { useEffect, useState } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { ApiClient } from "../api/client";
import { ModelDetail, ModelUsageStat, ModelComparisonData } from "../api/types";
import { ArrowLeft, Scale, Star, ShieldCheck, HeartPulse, Brain, Zap, HelpCircle, CheckCircle, Flame } from "lucide-react";
import { motion } from "motion/react";

export default function ModelComparePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // 从 URL 读取多个 "ids"
  const [ids, setIds] = useState<string[]>([]);
  const [compareData, setCompareData] = useState<ModelComparisonData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 用户需要选择引导时，获取完整模型列表
  const [allModels, setAllModels] = useState<ModelUsageStat[]>([]);
  const [loadingAll, setLoadingAll] = useState(false);

  useEffect(() => {
    const list = searchParams.getAll("ids");
    setIds(list);
  }, [searchParams]);

  useEffect(() => {
    let cancelled = false;
    setLoadingAll(true);
    ApiClient.getModelsPageData()
      .then((data) => {
        if (cancelled) return;
        setAllModels(data.models || []);
        setLoadingAll(false);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Failed loading all models for guide list:", err);
        setLoadingAll(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const currentIds = searchParams.getAll("ids");
    if (currentIds.length === 0) {
      setCompareData(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    ApiClient.compareModels(currentIds)
      .then((data) => {
        if (cancelled) return;
        setCompareData(data);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error(err);
        setError("无法接轨高维对比星符，虚无之流翻滚。");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [searchParams]);

  const updateIdsInUrl = (newIds: string[]) => {
    const params = new URLSearchParams();
    newIds.forEach((id) => params.append("ids", id));
    navigate(`/models/compare?${params.toString()}`);
  };

  const handleToggleId = (id: string) => {
    const isSelected = ids.includes(id);
    let nextIds: string[];
    if (isSelected) {
      nextIds = ids.filter((x) => x !== id);
    } else {
      nextIds = [...ids, id];
    }
    updateIdsInUrl(nextIds);
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center text-zinc-400 font-mono text-xs uppercase tracking-widest gap-2">
        <div className="w-6 h-6 border-2 border-t-yellow-500 border-zinc-900 rounded-full animate-spin" />
        <span>同步多维对弈沙盘属性...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center text-center p-4 gap-4">
        <Scale className="w-10 h-10 text-red-500 animate-pulse" />
        <p className="text-zinc-400 font-mono text-xs tracking-wider">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-zinc-950 border border-zinc-800 hover:border-yellow-500 text-xs font-mono text-zinc-300 hover:text-white"
        >
          重新校验 (RETRY)
        </button>
      </div>
    );
  }

  // 引导场景：URL 中少于 2 个 id 时显示选择引导
  const isFewerThanTwo = ids.length < 2;

  return (
    <div className="max-w-6xl mx-auto px-4 py-12 md:py-16 space-y-10">
      
      {/* Top Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-zinc-900 pb-6">
        <div className="space-y-1">
          <Link
            to="/models"
            className="inline-flex items-center gap-1 text-[11px] font-mono tracking-widest uppercase text-zinc-400 hover:text-yellow-500 transition-colors mb-2"
          >
            <ArrowLeft className="w-4 h-4" />
            返回智脑大殿 (BACK)
          </Link>
          <h1 className="text-2xl md:text-3xl font-black font-sans uppercase tracking-[0.1em] text-zinc-100 flex items-center gap-3">
            <Scale className="w-6 h-6 text-yellow-500 shrink-0" />
            虚境双天平 ∙ 智脑多维校对 (MODEL COMPARISON)
          </h1>
          <p className="text-xs text-zinc-400 max-w-3xl leading-relaxed">
            比照不同思维脾性之模型的推理硬深度、黑夜诡计伪装力以及白昼辩证热度，助你物色出圆桌上最无暇的同盟护卫。
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start relative">
        
        {/* Left Interactive Checklist Sidebar: Select Models (4 cols) */}
        <div className="lg:col-span-4 bg-zinc-950/90 border border-zinc-900 p-5 rounded-lg space-y-6">
          <div>
            <h3 className="text-xs font-mono font-extrabold uppercase tracking-widest text-[#f59e0b] border-b border-zinc-900 pb-2 flex items-center gap-2">
              <Brain className="w-4 h-4" />
              星符席位勾挑 (AGENTS POOL)
            </h3>
            <p className="text-[11px] text-zinc-500 mt-1 lines-clamp-2 leading-relaxed">
              勾选或卸除下方大模型的权能圣徽，右侧星盘对比矩阵将实时同步。
            </p>
          </div>

          <div className="space-y-3.5">
            {loadingAll ? (
              <div className="text-[10px] font-sans text-zinc-650 tracking-wider">正在载入神圣席位...</div>
            ) : (
              allModels.map((model) => {
                const checked = ids.includes(model.model_id);

                return (
                  <button
                    type="button"
                    key={model.model_id}
                    onClick={() => handleToggleId(model.model_id)}
                    className={`w-full group p-3.5 rounded text-left border flex items-center justify-between transition-all cursor-pointer ${
                      checked
                        ? "bg-[#110e08]/90 border-yellow-500/70"
                        : "bg-zinc-900/40 border-zinc-900 hover:border-zinc-800"
                    }`}
                  >
                    <div>
                      <h4 className={`text-xs font-bold transition-colors ${checked ? "text-yellow-500" : "text-zinc-200"}`}>
                        {model.display_name}
                      </h4>
                      <p className="text-[10px] text-zinc-500 mt-1 uppercase">
                        胜率 {model.win_rate}% ∙ MVP {model.avg_mvp}
                      </p>
                    </div>

                    <div className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 text-black uppercase text-[10px] font-bold ${
                      checked 
                        ? "bg-yellow-500 border-yellow-500" 
                        : "border-zinc-700 bg-transparent group-hover:border-zinc-550"
                    }`}>
                      {checked && "✓"}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right Area: Comparison Matrix or Selection Guide (8 cols) */}
        <div className="lg:col-span-8">
          {isFewerThanTwo ? (
            /* SELECTION GUIDE: Show gorgeous guiding state for lack of models */
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-zinc-950/80 border border-zinc-900 rounded p-8 text-center space-y-6 relative"
            >
              <div className="absolute inset-2 border border-zinc-900/40 rounded-sm pointer-events-none" />
              
              <div className="w-16 h-16 rounded-full bg-yellow-500/10 border-2 border-yellow-500 flex items-center justify-center text-yellow-500 mx-auto animate-pulse">
                <Scale className="w-8 h-8" />
              </div>

              <div className="space-y-2">
                <h2 className="text-base font-black font-sans uppercase tracking-widest text-zinc-100">
                  星盘感应不足 (SELECTION REQUIRED)
                </h2>
                <p className="text-xs text-zinc-400 max-w-sm mx-auto leading-relaxed">
                  大天平左侧盘空无，我们需要至少 <span className="text-yellow-500 font-bold font-sans">2 款对弈模型</span> 方可施加星符刻印，解包多维度逻辑胜负比对。
                </p>
              </div>

              <div className="w-10 h-px bg-zinc-850 mx-auto" />

              <div className="space-y-2 text-left max-w-md mx-auto bg-zinc-900/40 border border-zinc-900 p-4 rounded-lg">
                <span className="text-[10px] font-sans text-zinc-500 tracking-widest block font-bold mb-2">如何开启对决：</span>
                <ul className="space-y-1.5 text-xs text-zinc-400">
                  <li className="flex items-start gap-1">
                    <span className="text-yellow-500 font-bold font-mono">①</span>
                    <span>阅读左侧列表勾选任意两款智脑（如 Gemini 1.5 Pro & 2.5 Flash）。</span>
                  </li>
                  <li className="flex items-start gap-1">
                    <span className="text-yellow-500 font-bold font-mono">②</span>
                    <span>系统将检索其后台对弈胜率、逻辑深度并解构其欺饰长短处。</span>
                  </li>
                </ul>
              </div>
            </motion.div>
          ) : (
            /* COMPLETE MATRIX SECTION: Displays side-by-side matrices */
            compareData && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="space-y-8"
              >
                {/* 1. Basic Summary Cards row */}
                <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${compareData.models.length}, minmax(0, 1fr))` }}>
                  {compareData.models.map((model) => (
                    <div key={model.id} className="bg-zinc-950/95 border border-zinc-900 p-4 rounded text-left relative overflow-hidden flex flex-col justify-between min-h-[140px] shadow-lg">
                      <div className="space-y-2">
                        <div className="text-[9px] font-mono text-zinc-650 uppercase">
                          {model.developer}
                        </div>
                        <h4 className="text-sm font-black font-sans text-zinc-100 uppercase tracking-wide">
                          {model.name}
                        </h4>
                        <div className="flex items-center gap-1 text-[11px] font-mono text-yellow-500 font-extrabold mt-1">
                          <Star className="w-3.5 h-3.5 fill-current" />
                          <span>Rating {model.rating}</span>
                        </div>
                      </div>

                      <div className="pt-2 border-t border-zinc-900/50 mt-4 flex justify-between items-center text-[10px] font-mono">
                        <span className="text-zinc-500">
                          偏好: <span className="text-zinc-300 font-bold">{model.primaryRolePreference}</span>
                        </span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* 2. Detailed Dimension Grid Block */}
                <div className="bg-zinc-950/90 border border-zinc-900 rounded-lg overflow-hidden">
                  <div className="bg-zinc-900/50 border-b border-zinc-900 px-5 py-3 text-left">
                    <span className="text-[10px] font-mono text-yellow-500 uppercase tracking-[0.15em] font-extrabold">
                      圣会多维对撞 (CRITICAL BENCHMARKS)
                    </span>
                  </div>

                  <div className="divide-y divide-zinc-900/80">
                    {compareData.dimensionAnalysis.map((dim, idx) => (
                      <div key={idx} className="p-5 space-y-4 text-left">
                        {/* Dimension Header */}
                        <div>
                          <h4 className="text-xs font-mono font-extrabold text-zinc-100 uppercase tracking-wider flex items-center gap-1.5">
                            <span className="text-yellow-600 font-bold">●</span>
                            {dim.dimension}
                          </h4>
                          <p className="text-[11px] text-zinc-500 leading-relaxed font-sans mt-0.5 max-w-2xl">
                            {dim.description}
                          </p>
                        </div>

                        {/* Side By Side dynamic text cells */}
                        <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${compareData.models.length}, minmax(0, 1fr))` }}>
                          {compareData.models.map((model) => (
                            <div key={model.id} className="bg-zinc-900/20 border border-zinc-900/40 p-4 rounded text-xs space-y-2">
                              <span className="font-mono text-[9px] text-[#22c55e]/90 font-bold block uppercase border-b border-zinc-900 pb-1 flex items-center gap-1">
                                <CheckCircle className="w-3 h-3" />
                                {model.name} 判决
                              </span>
                              <p className="text-zinc-400 font-sans leading-relaxed text-[11px]">
                                {dim.details[model.id] || "无法感应决策记录。"}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 3. Overall Verdict Narrative Box */}
                <div className="bg-[#0b0914] border border-[#a855f7]/25 p-6 rounded-lg relative overflow-hidden text-left space-y-3 shadow-2xl">
                  <div className="absolute top-1 right-2 text-violet-850 font-mono text-[55px] select-none opacity-20 font-bold">
                    VERDICT
                  </div>

                  <div className="flex items-center gap-2 text-xs font-mono text-violet-400 uppercase tracking-widest font-extrabold">
                    <Flame className="w-4.5 h-4.5 text-violet-400 animate-pulse" />
                    圣会大祭司终审评述 (FINAL VERDICT)
                  </div>

                  <p className="text-xs text-zinc-200 leading-relaxed font-sans pr-12 relative z-10 font-medium">
                    {compareData.overallVerdict}
                  </p>
                </div>

              </motion.div>
            )
          )}
        </div>

      </div>

      {/* Symmetrical footer */}
      <div className="pt-8 border-t border-zinc-900/50 flex justify-between items-center text-[9px] font-mono text-zinc-700">
        <span>COSMIC SANDBOX COMPLIANT</span>
        <span>BENCHMARKS CALIBRATED ON REAL GAME RUNS</span>
      </div>
    </div>
  );
}
