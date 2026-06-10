import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiClient } from "../api/client";
import { ModelUsageStat } from "../api/types";
import { ArrowLeft, Trophy } from "lucide-react";
import { motion } from "motion/react";
import PageLoadState from "../components/PageLoadState";
import {
  selectOverallStats,
  LOW_SAMPLE_THRESHOLD,
  OverallSortKey,
} from "../utils/modelOverall";

export default function ModelOverallPage() {
  const [models, setModels] = useState<ModelUsageStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<OverallSortKey>("win_rate");

  useEffect(() => {
    let active = true;
    ApiClient.getModelsPageData()
      .then((data) => {
        if (!active) return;
        setModels((data.models as unknown as ModelUsageStat[]) || []);
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setError("命运迷雾阻扰，无法探寻模型总战绩。");
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return <PageLoadState variant="loading" loadingText="聚合各模型总体战绩..." />;
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

  const rows = selectOverallStats(models, sortKey);

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-10 text-center"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-zinc-950 border border-zinc-900 rounded-full text-[9px] font-mono text-amber-500 uppercase tracking-widest mb-4">
          <Trophy className="w-3.5 h-3.5 text-amber-500" />
          OVERALL WIN RATE
        </div>
        <h1 className="text-2xl md:text-3xl font-extrabold uppercase tracking-widest font-sans text-zinc-100">
          模型总胜率对比
        </h1>
        <p className="text-xs text-zinc-500 mt-2">不区分角色，每个模型跨全部对局的总体胜率</p>
      </motion.div>

      <div className="bg-zinc-950/60 border border-zinc-900 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-zinc-900 flex justify-between items-center bg-zinc-950">
          <Link
            to="/models"
            className="flex items-center gap-1.5 text-xs font-mono text-zinc-500 hover:text-amber-500 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            返回模型排行榜
          </Link>
          <div className="flex items-center gap-2 text-xs font-mono text-zinc-500">
            排序:
            <select
              value={sortKey}
              onChange={(e) => setSortKey(e.target.value as OverallSortKey)}
              className="bg-zinc-900 border border-zinc-800 rounded px-2 py-1 outline-none focus:border-amber-500 transition-colors text-zinc-300"
            >
              <option value="win_rate">按胜率</option>
              <option value="run_count">按对局数</option>
            </select>
          </div>
        </div>

        {rows.length === 0 ? (
          <div className="px-6 py-16 text-center">
            <p className="text-zinc-500 font-mono text-xs tracking-widest">暂无模型出战记录</p>
            <p className="text-zinc-600 text-[10px] font-mono mt-2">请先通过「对局引擎」发起一场对弈</p>
          </div>
        ) : (
          <ul className="divide-y divide-zinc-900/30">
            {rows.map((m, idx) => (
              <li key={m.model_id} className="px-6 py-4 flex items-center gap-4">
                <span className="w-6 text-center font-mono text-xs text-zinc-500 shrink-0">{idx + 1}</span>
                <div className="w-52 shrink-0 min-w-0">
                  <p className="font-bold text-sm text-zinc-200 truncate" title={m.display_name}>
                    {m.display_name}
                  </p>
                  <p className="font-mono text-[10px] text-zinc-500 mt-0.5">
                    {m.run_count} 局 · 平均 MVP {m.avg_mvp.toFixed(1)}
                    {m.run_count < LOW_SAMPLE_THRESHOLD && (
                      <span className="ml-1.5 px-1 py-px rounded-sm bg-zinc-800 text-zinc-400">样本少</span>
                    )}
                  </p>
                </div>
                <div className="flex-1 h-3 bg-zinc-900/80 rounded-sm overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-amber-700 to-amber-400 rounded-sm"
                    style={{ width: `${Math.min(100, Math.max(0, m.win_rate))}%` }}
                  />
                </div>
                <span className="w-14 text-right font-mono font-bold text-amber-500 shrink-0">
                  {m.win_rate}%
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
