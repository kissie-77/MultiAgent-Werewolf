import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Shield, ChevronDown, Play, Share, Trophy, Users, AlertCircle } from "lucide-react";
import { motion } from "motion/react";
import { ApiClient } from "../api/client";
import { mapRunRow, type RunRow } from "../utils/runRows";

export default function RunsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [campFilter, setCampFilter] = useState("ALL");
  const [countFilter, setCountFilter] = useState("ALL");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    ApiClient.getRunsPageData(1, 50)
      .then((data) => {
        if (cancelled) return;
        setRuns(data.runs.items.map(mapRunRow));
        setError(null);
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const filteredRuns = runs.filter((run) => {
    if (campFilter !== "ALL" && run.winnerCamp !== campFilter) return false;
    if (countFilter !== "ALL" && run.playerCount.toString() !== countFilter) return false;
    return true;
  });

  const winnerBadge = (camp: RunRow["winnerCamp"]) => {
    if (camp === "GOOD")
      return <span className="text-blue-400 flex items-center gap-1.5 font-bold tracking-widest text-sm"><Trophy className="w-4 h-4" /> 好人胜</span>;
    if (camp === "WEREWOLF")
      return <span className="text-red-500 flex items-center gap-1.5 font-bold tracking-widest text-sm"><Trophy className="w-4 h-4" /> 狼人胜</span>;
    if (camp === "DRAW")
      return <span className="text-zinc-400 flex items-center gap-1.5 font-bold tracking-widest text-sm">平局 / 弃局</span>;
    return <span className="text-zinc-500 flex items-center gap-1.5 font-bold tracking-widest text-sm">未结算</span>;
  };

  return (
    <div className="min-h-screen bg-[#07050d] text-zinc-100 font-sans relative overflow-x-hidden p-6 md:p-12">
      <div className="absolute inset-4 pointer-events-none border border-zinc-900/50 rounded z-0" />
      <div className="absolute inset-5 pointer-events-none border-2 border-zinc-950/80 rounded z-0" />

      <div className="max-w-6xl mx-auto relative z-10">
        <div className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-zinc-900/80 pb-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Shield className="w-6 h-6 text-yellow-500" />
              <h1 className="text-3xl font-black tracking-widest uppercase font-serif text-transparent bg-clip-text bg-gradient-to-r from-zinc-100 to-zinc-400">
                战绩中心
              </h1>
            </div>
            <p className="text-xs font-mono text-zinc-500 tracking-[0.2em]">
              RECORD OF JUDGMENTS &bull;{" "}
              {loading ? "载入中…" : `${runs.length} 局记载`}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="relative group">
              <select
                value={campFilter}
                onChange={(e) => setCampFilter(e.target.value)}
                className="appearance-none bg-zinc-950 border border-zinc-800 text-xs font-mono text-zinc-400 px-4 py-2 pr-8 rounded hover:border-zinc-700 outline-none cursor-pointer focus:border-yellow-500/50"
              >
                <option value="ALL">阵营 [全部]</option>
                <option value="GOOD">好人获胜</option>
                <option value="WEREWOLF">狼人获胜</option>
                <option value="DRAW">平局弃局</option>
              </select>
              <ChevronDown className="w-3 h-3 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-600 group-hover:text-zinc-400" />
            </div>
            <div className="relative group">
              <select
                value={countFilter}
                onChange={(e) => setCountFilter(e.target.value)}
                className="appearance-none bg-zinc-950 border border-zinc-800 text-xs font-mono text-zinc-400 px-4 py-2 pr-8 rounded hover:border-zinc-700 outline-none cursor-pointer focus:border-yellow-500/50"
              >
                <option value="ALL">人数 [全部]</option>
                <option value="4">4 人局</option>
                <option value="6">6 人局</option>
                <option value="8">8 人局</option>
                <option value="12">12 人局</option>
                <option value="16">16 人局</option>
              </select>
              <ChevronDown className="w-3 h-3 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-600 group-hover:text-zinc-400" />
            </div>
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-40 bg-zinc-900/40 rounded-lg border border-zinc-800/50 animate-pulse" />
            ))}
          </div>
        ) : error ? (
          <div className="py-20 flex flex-col items-center justify-center text-red-400/80 gap-4 text-center">
            <AlertCircle className="w-12 h-12 text-red-700" />
            <p className="font-mono text-xs">加载对局卷宗失败：{error}</p>
          </div>
        ) : filteredRuns.length === 0 ? (
          <div className="py-20 flex flex-col items-center justify-center text-zinc-500 gap-4 text-center">
            <AlertCircle className="w-12 h-12 text-zinc-700" />
            <div className="space-y-1">
              <p className="font-sans text-sm">虚境内尚未窥见相应的对局卷宗</p>
              <p className="font-mono text-xs opacity-60">尝试其他筛选条件，或去推案大厅新开一局。</p>
            </div>
            <Link to="/" className="mt-4 px-6 py-2 bg-yellow-600/20 text-yellow-500 hover:bg-yellow-600/30 border border-yellow-600/50 rounded text-xs font-mono tracking-widest uppercase transition-colors">
              新开对局
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {filteredRuns.map((run, idx) => (
              <motion.div
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                key={run.runId}
                className="bg-zinc-950/80 border border-zinc-900 hover:border-zinc-700/80 rounded-lg p-5 flex flex-col justify-between group transition-all"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      {winnerBadge(run.winnerCamp)}
                      <span className="text-zinc-600 text-[10px] font-mono border-l border-zinc-800 pl-2 ml-1">
                        {run.playerCount}人 &middot; {run.createdAt}
                      </span>
                    </div>
                    <div className="text-[10px] font-mono text-zinc-500 tracking-wider">#{run.runId}</div>
                  </div>
                </div>

                <div className="flex items-end justify-between mt-auto">
                  <div className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest flex items-center gap-1">
                    <Users className="w-3 h-3" />
                    {run.playerCount} 座
                  </div>
                  <div className="flex items-center gap-2">
                    {run.hasReplay ? (
                      <Link
                        to={`/replay/${run.runId}`}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30 hover:text-indigo-300 border border-indigo-500/30 rounded font-mono text-[10px] uppercase tracking-widest transition-colors"
                      >
                        <Play className="w-3 h-3" /> 复盘
                      </Link>
                    ) : (
                      <span className="text-[10px] text-zinc-600 font-mono">无回放</span>
                    )}
                    <Link
                      to={`/share/${run.runId}`}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-300 border border-zinc-700 rounded font-mono text-[10px] uppercase tracking-widest transition-colors"
                    >
                      <Share className="w-3 h-3" /> 分享
                    </Link>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
