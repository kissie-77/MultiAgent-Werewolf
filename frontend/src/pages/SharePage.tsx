import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ApiClient } from "../api/client";
import { ShareReplayPageData } from "../api/types";
import { Trophy, Play, Hexagon } from "lucide-react";
import { motion } from "motion/react";

export default function SharePage() {
  const { runId } = useParams();
  const [data, setData] = useState<ShareReplayPageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    if (runId) {
      ApiClient.getShareReplayData(runId)
        .then(res => {
          if (active) {
            setData(res);
            setLoading(false);
          }
        })
        .catch(e => {
          if (active) {
            setError(e.message);
            setLoading(false);
          }
        });
    }
    return () => { active = false; };
  }, [runId]);

  useEffect(() => {
    if (data) {
      document.title = `${data.share_title} - 狼人杀战报`;
      // We would normally inject og tags here for a real SPA with helmet
    }
  }, [data]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#07050d] text-zinc-100 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-zinc-500">
           <Hexagon className="w-8 h-8 animate-spin text-amber-500" />
           <p className="font-mono text-xs uppercase tracking-widest">提取灵能战报中...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-[#07050d] text-zinc-100 flex items-center justify-center pb-20">
        <div className="text-center">
          <p className="text-zinc-500 font-mono text-sm tracking-wider">星盘残影流失，无此战报存库</p>
          <Link to="/runs" className="mt-4 block hover:text-amber-500 font-mono text-xs text-zinc-400">返回战绩中心</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[100dvh] bg-[#07050d] flex flex-col items-center justify-center p-4 selection:bg-amber-500/30">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="w-full max-w-[1000px] aspect-[1200/630] bg-zinc-950/80 border border-zinc-800 rounded-xl overflow-hidden relative shadow-[0_10px_60px_-15px_rgba(0,0,0,0.8)]"
      >
        {/* Background Decorative */}
        <div className="absolute inset-0 z-0">
          <div className={`absolute -top-[40%] -left-[10%] w-[80%] h-[80%] rounded-full blur-[120px] opacity-20 ${data.winner_camp === "WOLVES" ? 'bg-red-500' : 'bg-blue-500'}`} />
          <div className="absolute -bottom-[20%] -right-[10%] w-[70%] h-[70%] bg-amber-500 blur-[150px] opacity-[0.15] rounded-full" />
          <div className="absolute inset-0 bg-[url('https://transparenttextures.com/patterns/cubes.png')] opacity-10 mix-blend-overlay" />
        </div>

        <div className="relative z-10 w-full h-full flex flex-col p-8 md:p-14 justify-between">
           {/* Top Brand & Title */}
           <div className="flex justify-between items-start">
             <div>
               <div className="font-serif text-amber-500 text-lg md:text-xl font-bold tracking-[0.2em] uppercase flex items-center gap-3">
                 <Hexagon className="w-6 h-6 fill-amber-500/20" /> 
                 🐺 AI 狼人杀 · 战报
               </div>
               <div className="text-zinc-500 font-mono text-xs uppercase tracking-widest mt-2 ml-10">
                 RECORD ID: #{runId}
               </div>
             </div>
             
             <div className="text-right">
               <div className="font-mono text-xs text-zinc-400 border border-zinc-800 bg-zinc-950 px-3 py-1 rounded">
                 {data.stats_line}
               </div>
             </div>
           </div>

           {/* Center Content Area */}
           <div className="text-center space-y-6 md:space-y-8 flex-1 flex flex-col items-center justify-center max-w-3xl mx-auto w-full">
              {/* Winner Announcement */}
              <div className="flex flex-col items-center justify-center">
                 <div className="flex items-center gap-4 text-4xl md:text-6xl font-black font-sans uppercase tracking-widest">
                   <Trophy className={`w-10 h-10 md:w-14 md:h-14 ${data.winner_camp === "WOLVES" ? "text-red-500" : "text-blue-500"}`} />
                   <span className={data.winner_camp === "WOLVES" ? "text-red-500" : "text-blue-500"}>
                     {data.winner_camp === "WOLVES" ? "狼人阵营获胜" : "✨ 好人阵营获胜"}
                   </span>
                 </div>
              </div>

              {/* MVP Tag */}
              <div className="inline-flex flex-col items-center p-6 border border-zinc-800 bg-zinc-900/60 rounded-xl backdrop-blur-sm relative">
                 <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-amber-500 text-black font-black font-mono text-[10px] px-3 py-1 rounded uppercase tracking-widest">
                    全场 MVP
                 </div>
                 <div className="text-2xl md:text-3xl font-sans font-bold text-zinc-100 flex items-center gap-3">
                    🥇 {data.mvp_winner.playerName}
                 </div>
                 <div className="text-sm font-mono text-zinc-400 mt-2 flex items-center gap-2">
                    <span className="text-amber-500">{data.mvp_winner.role}</span>
                    <span className="opacity-50">·</span>
                    <span className="uppercase text-yellow-600/80 tracking-widest">引爆了关键战略节点</span>
                 </div>
                 <p className="text-xs text-zinc-300 font-sans mt-4 max-w-lg mx-auto italic text-center opacity-90 leading-relaxed border-t border-zinc-800 pt-4">
                   “{data.mvp_winner.citation}”
                 </p>
              </div>
           </div>

           {/* Footer area & Moment */}
           <div className="flex justify-between items-end border-t border-zinc-800/60 pt-6">
              <div className="max-w-xl">
                 <p className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-1.5 flex items-center gap-2">
                   <span className="w-1.5 h-1.5 bg-yellow-500 rounded-full animate-pulse" /> 关键节点 (Key Moment)
                 </p>
                 <p className="font-sans text-sm md:text-base text-zinc-300">
                   {data.share_summary}
                 </p>
              </div>
              <div className="shrink-0 ml-6">
                {/* Logo or visual brand marker */}
                <div className="font-mono text-xs uppercase tracking-[0.3em] text-zinc-600 font-bold mb-1">
                  AI.STUDIO.PLAY
                </div>
              </div>
           </div>
        </div>
      </motion.div>
      
      {/* Action to actually go to replay */}
      <div className="mt-12 flex items-center justify-center gap-6">
        <Link 
          to={`/replay/${runId}`} 
          className="flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded font-mono text-sm uppercase tracking-widest transition-colors shadow-lg shadow-indigo-600/20"
        >
          <Play className="w-4 h-4 fill-current" /> 看完整复盘
        </Link>
        <Link 
          to="/runs" 
          className="flex items-center gap-2 px-6 py-3 bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-zinc-300 rounded font-mono text-sm uppercase tracking-widest transition-colors"
        >
          返回战绩中心
        </Link>
      </div>
    </div>
  );
}
