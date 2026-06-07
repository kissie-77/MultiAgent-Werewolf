import React, { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { ApiClient } from "../api/client";
import { ReplayPageData } from "../api/types";
import { motion } from "motion/react";
import TimelinePlayback from "../components/TimelinePlayback";
import BeliefHeatmap from "../components/BeliefHeatmap";
import VoteSwing from "../components/VoteSwing";
import MvpTab from "../components/MvpTab";
import {  
  Calendar, 
  Clock, 
  Tv, 
  Gauge, 
  Compass, 
  Users, 
  ShieldCheck, 
  ShieldAlert, 
  ChevronRight, 
  Map, 
  Crown, 
  Award, 
  Heart, 
  Zap, 
  BrainCircuit, 
  Eye, 
  MessageSquare, 
  User, 
  TrendingUp, 
  Flame,
  Grid
} from "lucide-react";
import PageLoadState from "../components/PageLoadState";

export default function ReplayPage() {
  const { runId } = useParams<{ runId: string }>();
  const [data, setData] = useState<ReplayPageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"timeline" | "mvp_report" | "report" | "belief" | "vote_swing">("timeline");
  const [viewScope, setViewScope] = useState<string>("ALL");

  const fetchData = useCallback(() => {
    if (!runId) return;
    setLoading(true);
    setErr(null);
    ApiClient.getReplayData(runId)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((e) => {
        console.error(e);
        setErr("真意星流无法检索此局复盘，或虚境网络波动，请稍后再试。");
        setLoading(false);
      });
  }, [runId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 信念/狼人快照的日期选择器 — 从真实时间线（和信念快照日期）推导，
  // 而非硬编码的 [1, 2]。
  const [selectedSnapshotDay, setSelectedSnapshotDay] = useState<number>(1);

  if (loading) {
    return <PageLoadState variant="loading" loadingText="正在点燃烛火，召回审判镜像..." />;
  }

  if (err || !data) {
    return (
      <PageLoadState
        variant="error"
        errorText={err || "无法检索指定的复盘档案"}
        onRetry={fetchData}
        action={
          <Link
            to="/"
            className="px-5 py-2.5 bg-zinc-900 border border-zinc-800 hover:border-yellow-500 hover:text-yellow-500 text-xs font-mono tracking-widest text-zinc-300 rounded transition-colors"
          >
            返回首页
          </Link>
        }
      />
    );
  }

  const { run, timeline, phase_summary, turning_points, mvp_ranking, scores, report_markdown, coach_excerpt, belief_snapshots, wolf_camp_snapshots, belief_heatmap, belief_matrix_anchors, vote_swing_summary } = data;

  // 日期选项 — 从真实时间线（和信念快照日期）推导，而非硬编码的 [1, 2]。
  const snapshotDays: number[] = (() => {
    const days = new Set<number>();
    timeline.forEach((e) => { if (e.day > 0) days.add(e.day); });
    belief_snapshots.forEach((s) => { if (s.day > 0) days.add(s.day); });
    const sorted = Array.from(days).sort((a, b) => a - b);
    return sorted.length > 0 ? sorted : [1];
  })();

  // 每个座位的视角选项必须匹配真实玩家数量，而非硬编码 P1–P6
  //（这会让 9/12 人复盘看起来像 6 人游戏）。优先使用对局的玩家数；
  // 回退到时间线中出现的最高座位号。
  const seatCount: number = (() => {
    if (run.initial_players && run.initial_players > 0) return run.initial_players;
    let max = 0;
    timeline.forEach((e) => {
      const n = e.playerId ? parseInt(String(e.playerId).replace(/\D/g, ""), 10) : NaN;
      if (Number.isFinite(n) && n > max) max = n;
    });
    return max;
  })();
  const seatNumbers: number[] = Array.from({ length: seatCount }, (_, i) => i + 1);

  // 轻量自定义 Markdown 渲染器，支持简洁语法而无需引入不受信任的依赖
  const renderMarkdown = (md: string) => {
    const lines = md.split("\n");
    return (
      <div className="space-y-4 font-sans text-sm text-zinc-300 leading-relaxed">
        {lines.map((line, idx) => {
          const trimmed = line.trim();
          if (!trimmed) return <div key={idx} className="h-2" />;

          // 标题
          if (trimmed.startsWith("# ")) {
            return (
              <h1 key={idx} className="font-serif text-xl md:text-2xl font-black text-[#eae5db] tracking-wider border-b border-zinc-800/80 pb-2 mt-8 mb-4">
                {trimmed.replace("# ", "")}
              </h1>
            );
          }
          if (trimmed.startsWith("## ")) {
            return (
              <h2 key={idx} className="font-serif text-lg font-bold text-[#eae5db] tracking-wide mt-6 mb-3">
                {trimmed.replace("## ", "")}
              </h2>
            );
          }
          if (trimmed.startsWith("### ")) {
            return (
              <h3 key={idx} className="font-serif text-base font-medium text-yellow-500/90 tracking-wide mt-4 mb-2">
                {trimmed.replace("### ", "")}
              </h3>
            );
          }

          // 表格
          if (trimmed.startsWith("|") && lines[idx + 1]?.startsWith("| :---")) {
            // 下一行是表头分隔符，解析表格
            const tableRows: string[][] = [];
            let i = idx;
            // 向下扫描以累积此表格的所有行
            while (i < lines.length && lines[i].trim().startsWith("|")) {
              const cells = lines[i].split("|").map(col => col.trim()).filter((_, index, arr) => index > 0 && index < arr.length - 1);
              tableRows.push(cells);
              i++;
            }
            // 跳过已处理的表格行索引
            lines.splice(idx, i - idx); // 从数组中移除，避免重复处理
            const headers = tableRows[0];
            const dataRows = tableRows.slice(2); // 索引 1 是分隔符行

            return (
              <div key={idx} className="overflow-x-auto my-4 border border-zinc-900 rounded bg-zinc-950/40">
                <table className="min-w-full divide-y divide-zinc-900">
                  <thead className="bg-zinc-950">
                    <tr>
                      {headers.map((h, hIdx) => (
                        <th key={hIdx} className="px-4 py-2.5 text-left text-[10px] font-mono tracking-widest text-[#eae5db] uppercase border-r border-zinc-900 last:border-0">
                          {h.replace(/\*\*/g, "")}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-900/50">
                    {dataRows.map((row, rIdx) => (
                      <tr key={rIdx} className="hover:bg-zinc-900/20">
                        {row.map((cell, cIdx) => (
                          <td key={cIdx} className="px-4 py-2 text-xs border-r border-zinc-900 last:border-0 text-zinc-300 font-sans">
                            {cell.startsWith("**") ? <strong className="text-yellow-500/90">{cell.replace(/\*\*/g, "")}</strong> : cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          }

          // 分隔线
          if (trimmed === "---") {
            return <hr key={idx} className="border-t border-zinc-800 my-4" />;
          }

          // 列表项
          if (trimmed.startsWith("- ")) {
            const content = trimmed.replace("- ", "");
            // 拆分加粗
            const pParts = content.split("**");
            return (
              <ul key={idx} className="list-disc pl-5 my-1.5 space-y-1">
                <li className="text-zinc-300 leading-relaxed text-xs">
                  {pParts.map((part, pIdx) => (
                    pIdx % 2 === 1 ? <strong key={pIdx} className="text-yellow-500/90 font-semibold">{part}</strong> : part
                  ))}
                </li>
              </ul>
            );
          }

          // 标准段落（含加粗格式）
          const parts = line.split("**");
          return (
            <p key={idx} className="text-xs text-zinc-400 leading-relaxed">
              {parts.map((p, pIdx) => (
                pIdx % 2 === 1 ? <strong key={pIdx} className="text-[#eae5db] font-semibold">{p}</strong> : p
              ))}
            </p>
          );
        })}
      </div>
    );
  };

  return (
    <div className="text-zinc-100 max-w-7xl mx-auto py-8 px-4 sm:px-6 md:px-8">
      {/* 1. Header Information Block */}
      <motion.div 
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full mb-6 border-b border-zinc-900 pb-2 flex flex-col md:flex-row items-center justify-between gap-4"
      >
        <div className="flex items-center gap-3 text-xs font-mono text-zinc-400">
          <Link to="/runs" className="hover:text-amber-500 transition-colors flex items-center gap-1.5">
             <ChevronRight className="w-4 h-4 rotate-180" /> 返回
          </Link>
          <span className="text-zinc-700">|</span>
          <span className="tracking-widest">#{runId.slice(0, 16)}</span>
          <span className="text-zinc-700">|</span>
          {run.winner_camp === "VILLAGERS" ? (
             <span className="text-blue-400 flex items-center gap-1 font-bold">🏆好人胜</span>
          ) : (
             <span className="text-red-500 flex items-center gap-1 font-bold">🐺狼人胜</span>
          )}
          <span className="text-zinc-700">|</span>
          <span>{run.initial_players}人</span>
          <span className="text-zinc-700">|</span>
          <span className="uppercase">DEEPSEEK-V4-FLASH</span>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-xs font-mono text-zinc-500 flex items-center gap-2">
            视角:
            <select 
              value={viewScope}
              onChange={(e) => setViewScope(e.target.value)}
              className="bg-zinc-950 border border-zinc-800 text-zinc-300 rounded px-2 py-1 outline-none focus:border-amber-500 transition-colors"
            >
               <option value="ALL">上帝视角</option>
               <option value="PUBLIC">公开视角</option>
               {seatNumbers.map((n) => (
                 <option key={n} value={`P${n}`}>P{n} 视角</option>
               ))}
            </select>
          </label>
        </div>
      </motion.div>

      {/* 2. Custom Tabs Bar and Share */}
      <div className="flex flex-col sm:flex-row items-center border-b border-zinc-900 mb-8 sm:justify-between px-2 gap-4">
        <div className="flex overflow-x-auto scrollbar-none select-none">
          {[
            { key: "timeline", label: "时间线", icon: Calendar },
            { key: "belief", label: "信念矩阵", icon: Grid },
            { key: "vote_swing", label: "投票摇摆", icon: TrendingUp },
            { key: "mvp_report", label: "MVP ∙ 复盘", icon: Award }
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as any)}
                className={`flex items-center gap-2 px-6 py-3.5 border-b-2 text-xs font-mono tracking-widest transition-all whitespace-nowrap cursor-pointer ${
                  isActive 
                    ? "border-amber-500 text-amber-500 font-bold bg-[#eae5db]/[0.02]" 
                    : "border-transparent text-zinc-500 hover:text-zinc-300"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>
        
        <Link
          to={`/share/${runId}`}
          className="flex items-center gap-1.5 px-3 py-1.5 mb-2 sm:mb-0 border border-zinc-800 bg-zinc-950 hover:bg-zinc-900 hover:border-amber-500 hover:text-amber-500 rounded text-xs font-mono text-zinc-400 transition-all uppercase"
        >
          <Compass className="w-3.5 h-3.5" /> 分享
        </Link>
      </div>

      {/* 3. Tab Contents with entry animations */}
      <div>
        {activeTab === "timeline" && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full"
          >
            <TimelinePlayback timeline={timeline} viewScope={viewScope} />
          </motion.div>
        )}

        {activeTab === "mvp_report" && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full"
          >
            <MvpTab 
              mvpRanking={mvp_ranking}
              scores={scores}
              turningPoints={turning_points}
              reportMarkdown={report_markdown}
              runModel="DEEPSEEK-V4-FLASH"
            />
          </motion.div>
        )}

        {activeTab === "vote_swing" && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full"
          >
             <VoteSwing swings={vote_swing_summary} timeline={timeline} />
          </motion.div>
        )}

        {activeTab === "belief" && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-8"
          >
            {/* Interactive Day selector for snapshot view */}
            <div className="flex items-center gap-3">
              <span className="text-xs font-sans text-zinc-500 tracking-wider">审判日期切变: </span>
              <div className="flex bg-zinc-950 border border-zinc-900 p-1 rounded">
                {snapshotDays.map((day) => {
                  const isSel = selectedSnapshotDay === day;
                  return (
                    <button
                      key={day}
                      onClick={() => setSelectedSnapshotDay(day)}
                      className={`px-3 py-1 text-xs font-mono transition-all cursor-pointer ${
                        isSel ? "bg-[#eae5db] text-zinc-950 font-bold rounded" : "text-zinc-500 hover:text-zinc-300"
                      }`}
                    >
                      D{day} 阶段
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Belief snapshots */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Left Column: Player suspect levels */}
              <div className="border border-zinc-950 bg-zinc-950/60 rounded p-6">
                <h3 className="font-serif text-sm font-black tracking-widest text-[#eae5db] uppercase mb-3 border-b border-zinc-900 pb-2.5 flex items-center gap-2">
                  <Eye className="w-4 h-4 text-yellow-500" />
                  好人信念镜鉴 ∙ 怀疑度折线比率
                </h3>

                {belief_snapshots
                  .filter((v) => v.day === selectedSnapshotDay)
                  .map((snap, sIdx) => (
                    <div key={sIdx} className="space-y-6">
                      <p className="text-xs text-zinc-400 italic bg-zinc-900/40 border border-zinc-900 p-3 rounded font-sans leading-relaxed">
                        D{snap.day} 动态: {snap.comment}
                      </p>

                      <div className="space-y-4">
                        {snap.playerBeliefs.map((pb, pbIdx) => (
                          <div key={pbIdx} className="p-4 bg-zinc-900/20 border border-zinc-900 rounded space-y-3">
                            <span className="font-serif text-xs font-bold text-yellow-500 block">
                              【{pb.playerName}】心眼中的怀疑名单：
                            </span>

                            <div className="space-y-2">
                              {pb.targetBeliefs.map((tb, tbIdx) => (
                                <div key={tbIdx} className="space-y-1">
                                  <div className="flex justify-between text-[11px] font-mono">
                                    <span className="text-zinc-400">研判 {tb.targetPlayerName} 为狼人概率:</span>
                                    <span className={`font-bold ${
                                      tb.wolfProbability >= 80 ? "text-red-500" : tb.wolfProbability >= 50 ? "text-orange-400" : "text-zinc-500"
                                    }`}>{tb.wolfProbability}%</span>
                                  </div>
                                  <div className="w-full h-1.5 bg-zinc-900 rounded-full overflow-hidden">
                                    <div 
                                      className={`h-full transition-all ${
                                        tb.wolfProbability >= 80 ? 'bg-red-500' : tb.wolfProbability >= 50 ? 'bg-orange-500' : 'bg-zinc-600'
                                      }`} 
                                      style={{ width: `${tb.wolfProbability}%` }} 
                                    />
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))
                }
              </div>

              {/* Right Column: Wolf camp coordination */}
              <div className="border border-zinc-950 bg-zinc-950/60 rounded p-6 space-y-6">
                <h3 className="font-serif text-sm font-black tracking-widest text-red-500/90 uppercase border-b border-zinc-900 pb-2.5 flex items-center gap-2">
                  <Flame className="w-4 h-4 text-red-500" />
                  邪灵恶狼幽影日志
                </h3>

                {wolf_camp_snapshots
                  .filter((v) => v.day === selectedSnapshotDay)
                  .map((wolfSnap, wIdx) => (
                    <div key={wIdx} className="space-y-4">
                      <div className="p-4 bg-red-950/5 border border-red-900/10 rounded">
                        <span className="text-[10px] font-sans tracking-widest text-red-500/90 block mb-1">狼队核心战术战略</span>
                        <p className="text-xs text-zinc-300 font-sans leading-relaxed">
                          {wolfSnap.campStrategy}
                        </p>
                      </div>

                      <div className="p-4 bg-zinc-900/10 border border-zinc-900 rounded text-xs space-y-3.5">
                        <div className="flex justify-between items-center pb-2 border-b border-zinc-900/60">
                          <span className="text-zinc-500 font-sans text-[10px]">夜猎首要指定目标:</span>
                          <span className="font-serif text-sm font-bold text-[#eae5db]">{wolfSnap.targetSelectionName}</span>
                        </div>

                        <div className="space-y-2">
                          <span className="text-zinc-500 block font-sans text-[10px] mb-1">夜里狼队最终投票倾向：</span>
                          {wolfSnap.wolfVotes.map((wv, wvIdx) => (
                            <div key={wvIdx} className="flex justify-between font-mono text-[11px] bg-zinc-950/40 p-2 rounded">
                              <span className="text-zinc-400">暗桩 【{wv.wolfPlayerName}】 投</span>
                              <span className="text-red-400 font-bold">{wv.votedForName}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))
                }
              </div>
            </div>

            {/* Distrust Distrust Heatmap! Required!! */}
            <BeliefHeatmap anchors={belief_matrix_anchors} />
          </motion.div>
        )}
      </div>
    </div>
  );
}
