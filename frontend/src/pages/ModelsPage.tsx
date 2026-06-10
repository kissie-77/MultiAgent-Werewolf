import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiClient } from "../api/client";
import { ModelUsageStat } from "../api/types";
import { Brain, Star, Tag, Landmark, Sparkles, Scale, ArrowRight, CornerDownRight, CheckSquare, Square } from "lucide-react";
import { motion } from "motion/react";
import RadarCompare from "../components/RadarCompare";
import PageLoadState from "../components/PageLoadState";

export default function ModelsPage() {
  const navigate = useNavigate();
  const [models, setModels] = useState<ModelUsageStat[]>([]);
  const [introTitle, setIntroTitle] = useState("");
  const [introText, setIntroText] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [sortOrder, setSortOrder] = useState<"win_rate" | "run_count" | "avg_mvp">("win_rate");

  useEffect(() => {
    let active = true;
    ApiClient.getModelsPageData()
      .then((data) => {
        if (active) {
          // 预期数据结构现在返回 ModelUsageStat[] 类型的模型
          setModels((data.models as unknown as ModelUsageStat[]) || []);
          setIntroTitle(data.introTitle || "模型排行榜");
          setIntroText(data.introText || "");
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError("命运迷雾阻扰，无法探寻大堂对弈天平智脑。");
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const toggleSelect = (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter((x) => x !== id));
    } else {
      if (selectedIds.length < 3) {
        setSelectedIds([...selectedIds, id]);
      }
    }
  };

  const sortedModels = [...models].sort((a, b) => b[sortOrder] - a[sortOrder]);
  // Extract raw model_id from composite key for RadarCompare
  const modelIdsForRadar = selectedIds.map((k) => k.split("|")[0]);

  if (loading) {
    return <PageLoadState variant="loading" loadingText="同步沙场战报与智脑阶级..." />;
  }

  if (error) {
    return (
      <PageLoadState
        variant="error"
        errorText={error}
        onRetry={() => window.location.reload()}
        retryText="重新感应"
      />
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-12 text-center"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-zinc-950 border border-zinc-900 rounded-full text-[9px] font-mono text-amber-500 uppercase tracking-widest mb-4">
          <Landmark className="w-3.5 h-3.5 text-amber-500" />
          DECISION ARCHONS & MODELS
        </div>
        <h1 className="text-2xl md:text-3xl font-extrabold uppercase tracking-widest font-sans text-zinc-100">
          模型排行榜
        </h1>
        <p className="text-xs text-zinc-500 mt-2">
          所有参与过对弈的大语言模型战绩横向评测
        </p>
      </motion.div>

      <div className="bg-zinc-950/60 border border-zinc-900 rounded-lg overflow-hidden mb-8">
        <div className="px-6 py-4 border-b border-zinc-900 flex justify-between items-center bg-zinc-950">
           <h3 className="text-sm font-sans tracking-widest text-[#eae5db] font-bold">全网出战模型总序</h3>
           <div className="flex items-center gap-4">
             <Link
               to="/models/overall"
               className="flex items-center gap-1 text-xs font-mono text-amber-500/80 hover:text-amber-400 transition-colors whitespace-nowrap"
             >
               总胜率对比
               <ArrowRight className="w-3.5 h-3.5" />
             </Link>
             <div className="flex items-center gap-2 text-xs font-mono text-zinc-500">
               排位依据:
               <select
                 value={sortOrder}
                 onChange={(e) => setSortOrder(e.target.value as any)}
                 className="bg-zinc-900 border border-zinc-800 rounded px-2 py-1 outline-none focus:border-amber-500 transition-colors text-zinc-300"
               >
                 <option value="win_rate">胜率 (Win Rate)</option>
                 <option value="run_count">对局数 (Run Count)</option>
                 <option value="avg_mvp">平均MVP分 (MVP Score)</option>
               </select>
             </div>
           </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[600px]">
             <thead>
               <tr className="border-b border-zinc-900/60 text-[10px] font-mono uppercase tracking-widest text-zinc-500 bg-zinc-900/10">
                 <th className="px-6 py-3 font-normal w-12 text-center">#</th>
                 <th className="px-6 py-3 font-normal">模型名称</th>
                 <th className="px-6 py-3 font-normal text-right">对局数</th>
                 <th className="px-6 py-3 font-normal text-right">胜率</th>
                 <th className="px-6 py-3 font-normal text-right">平均 MVP</th>
                 <th className="px-6 py-3 font-normal text-center">对比</th>
               </tr>
             </thead>
             <tbody className="text-sm font-sans divide-y divide-zinc-900/30">
                {sortedModels.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-16 text-center">
                      <div className="flex flex-col items-center gap-3">
                        <Landmark className="w-8 h-8 text-zinc-700" />
                        <p className="text-zinc-500 font-mono text-xs tracking-widest">暂无模型出战记录</p>
                        <p className="text-zinc-600 text-[10px] font-mono">请先通过「对局引擎」发起一场对弈</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                sortedModels.map((model, idx) => {
                  const compositeKey = model.model_id + "|" + (model.role_name ?? "");
                  const isSelected = selectedIds.includes(compositeKey);
                  return (
                    <tr key={compositeKey} className={`transition-colors hover:bg-zinc-900/20 ${isSelected ? 'bg-amber-500/5' : ''}`}>
                       <td className="px-6 py-4 text-center font-mono text-xs text-zinc-500">{idx + 1}</td>
                       <td className="px-6 py-4 font-bold text-zinc-200">{model.display_name}</td>
                       <td className="px-6 py-4 text-right font-mono text-zinc-400">{model.run_count}</td>
                       <td className="px-6 py-4 text-right font-mono font-bold text-amber-500">{model.win_rate}%</td>
                       <td className="px-6 py-4 text-right font-mono text-blue-400">{model.avg_mvp.toFixed(1)}</td>
                       <td className="px-6 py-4 text-center">
                          <button
                            onClick={() => toggleSelect(compositeKey)}
                            className="text-zinc-500 hover:text-amber-500 transition-colors"
                          >
                             {isSelected ? <CheckSquare className="w-5 h-5 text-amber-500 mx-auto" /> : <Square className="w-5 h-5 mx-auto" />}
                          </button>
                       </td>
                    </tr>
                  )
                })
                )}
             </tbody>
          </table>
        </div>
      </div>

      {selectedIds.length > 0 ? (
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="border border-zinc-900 bg-zinc-950/80 rounded-lg p-6 lg:p-10 text-center"
        >
           <h3 className="text-sm font-serif tracking-widest text-[#eae5db] uppercase font-bold mb-2 flex items-center justify-center gap-2">
             模型灵能雷达解析库
           </h3>
           <p className="text-[10px] font-mono text-zinc-500 mb-8 uppercase tracking-widest">
              Radar Analytical Superposition
           </p>

           <RadarCompare selectedIds={modelIdsForRadar} />
        </motion.div>
      ) : (
        <div className="border border-zinc-900 border-dashed rounded-lg p-10 text-center text-zinc-600 font-mono text-xs">
           从列表勾选模型以调取能力雷达重叠视图
        </div>
      )}
    </div>
  );
}
