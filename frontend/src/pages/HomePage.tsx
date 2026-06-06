import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiClient } from "../api/client";
import { HomePageData } from "../api/types";
import { 
  Shield, 
  HelpCircle, 
  History, 
  Info, 
  Play, 
  Flame, 
  Calendar, 
  Scroll, 
  Server, 
  Users, 
  Star 
} from "lucide-react";
import { motion } from "motion/react";

export default function HomePage() {
  const [data, setData] = useState<HomePageData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let active = true;
    ApiClient.getHomePageData()
      .then((res) => {
        if (active) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          console.error("Failed loading home data:", err);
          setError("无法呼唤虚境之光，审判厅法阵传输受阻。");
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#07050d] flex flex-col items-center justify-center text-zinc-400 font-mono text-xs uppercase tracking-widest gap-2">
        <div className="w-6 h-6 border-2 border-t-yellow-500 border-zinc-800 rounded-full animate-spin" />
        <span>激活虚境石符中...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-[#07050d] text-zinc-400 flex flex-col items-center justify-center p-4 text-center gap-4">
        <Shield className="w-12 h-12 text-red-500 animate-pulse" />
        <p className="text-sm font-mono tracking-widest">{error || "数据载入失败"}</p>
        <button 
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-zinc-900 border border-zinc-800 rounded font-mono text-xs text-zinc-200 hover:border-yellow-500 hover:text-white"
        >
          重新召唤 (RETRY)
        </button>
      </div>
    );
  }

  // Pick suitable Lucide icons for quick links based on label or path
  const getLinkIcon = (path: string) => {
    if (path === "/" || path.includes("game")) return <Play className="w-5 h-5 text-yellow-500 group-hover:scale-110 transition-transform" />;
    if (path.includes("rules")) return <Scroll className="w-5 h-5 text-indigo-400 group-hover:scale-110 transition-transform" />;
    if (path.includes("runs")) return <History className="w-5 h-5 text-orange-400 group-hover:scale-110 transition-transform" />;
    return <Info className="w-5 h-5 text-zinc-400 group-hover:scale-110 transition-transform" />;
  };

  return (
    <div className="min-h-screen bg-[#07050d] text-zinc-100 font-sans relative overflow-x-hidden select-none antialiased py-12 px-4 md:px-8">
      {/* Immersive Woodcut Borders */}
      <div className="absolute inset-4 pointer-events-none border border-zinc-900/50 rounded z-0" />
      <div className="absolute inset-5 pointer-events-none border-2 border-zinc-950/80 rounded z-0" />

      {/* Decorative dark vector star bursts or circles */}
      <div className="absolute top-10 left-10 w-96 h-96 rounded-full bg-violet-950/10 blur-[80px] pointer-events-none z-0" />
      <div className="absolute bottom-10 right-10 w-96 h-96 rounded-full bg-orange-950/10 blur-[80px] pointer-events-none z-0" />

      <div className="max-w-6xl mx-auto relative z-10 flex flex-col items-stretch gap-12 mt-4">
        
        {/* Core Header Hero block */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center space-y-4 max-w-4xl mx-auto"
        >
          <div className="inline-block py-1.5 px-4 bg-zinc-950/95 border border-zinc-900 rounded-full text-[9px] font-mono uppercase tracking-[0.25em] text-yellow-500/80">
            ★ {data.subtitle} ∙ HIGH-DIMENSION EMPATHY SIMULATION ★
          </div>

          <h1 className="text-4xl md:text-6xl font-black tracking-[0.16em] uppercase font-sans text-transparent bg-clip-text bg-gradient-to-r from-zinc-200 via-yellow-500 to-zinc-200 py-1 drop-shadow-xl">
            {data.title}
          </h1>

          <p className="text-sm md:text-base text-zinc-400 max-w-3xl mx-auto leading-relaxed font-sans font-medium px-4">
            {data.description}
          </p>

          <div className="w-24 h-0.5 bg-yellow-500/30 mx-auto mt-6" />
        </motion.div>

        {/* Global Statistics Grid */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto w-full"
        >
          <div className="bg-zinc-950/95 border border-zinc-900/80 p-5 rounded-lg text-center relative overflow-hidden group hover:border-zinc-800 transition-colors">
            <div className="absolute top-1 right-1 text-[8px] font-mono text-zinc-800">ACTIVE_ARENAS</div>
            <div className="text-2xl font-mono font-black text-yellow-500">{data.stats.activeGames}</div>
            <div className="text-[10px] text-zinc-500 uppercase tracking-widest font-mono mt-1">当前存续对局</div>
          </div>
          <div className="bg-zinc-950/95 border border-zinc-900/80 p-5 rounded-lg text-center relative overflow-hidden group hover:border-zinc-800 transition-colors">
            <div className="absolute top-1 right-1 text-[8px] font-mono text-zinc-800">TOTAL_RECORDS</div>
            <div className="text-2xl font-mono font-black text-indigo-400">{data.stats.totalMatchesPlayed}</div>
            <div className="text-[10px] text-zinc-500 uppercase tracking-widest font-mono mt-1">历史公投卷宗</div>
          </div>
          <div className="bg-zinc-950/95 border border-zinc-900/80 p-5 rounded-lg text-center relative overflow-hidden group hover:border-zinc-800 transition-colors">
            <div className="absolute top-1 right-1 text-[8px] font-mono text-zinc-800">RUNNING_AGENTS</div>
            <div className="text-2xl font-mono font-black text-rose-500">{data.stats.onlineAIs}</div>
            <div className="text-[10px] text-zinc-500 uppercase tracking-widest font-mono mt-1">虚境智能棋子</div>
          </div>
          <div className="bg-zinc-950/95 border border-zinc-900/80 p-5 rounded-lg text-center relative overflow-hidden group hover:border-zinc-800 transition-colors">
            <div className="absolute top-1 right-1 text-[8px] font-mono text-zinc-800">MODEL_SCORE</div>
            <div className="text-2xl font-mono font-black text-emerald-400">{data.stats.averageRating}</div>
            <div className="text-[10px] text-zinc-500 uppercase tracking-widest font-mono mt-1">综合推理评分</div>
          </div>
        </motion.div>

        {/* Main Dashboard Navigation Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-6 pb-20">
          
          {/* BIG CTA: New Game */}
           <Link 
             to="/" 
             className="group relative col-span-1 md:col-span-2 lg:col-span-2 rounded-xl overflow-hidden shadow-2xl border border-yellow-500/40 bg-gradient-to-br from-[#1c1409] to-[#0a0703] p-8 flex flex-col justify-between transition-all hover:border-yellow-400 hover:shadow-[0_0_40px_rgba(234,179,8,0.15)]"
           >
              <div className="absolute top-0 right-0 p-6 pointer-events-none opacity-20 group-hover:opacity-100 group-hover:scale-110 transition-all duration-500 text-yellow-500">
                 <Play className="w-32 h-32" />
              </div>
              <div className="relative z-10 space-y-4 max-w-lg">
                <span className="inline-block px-3 py-1 bg-yellow-500/10 text-yellow-500 border border-yellow-500/20 text-[10px] font-mono tracking-widest uppercase rounded">
                   核心仪式 (Core Gameplay)
                </span>
                <h2 className="text-3xl font-serif font-black text-[#eae5db] tracking-wide">建立全新对局</h2>
                <p className="text-zinc-400 font-sans leading-relaxed">
                  选择您的权能身份（预言家、女巫、猎人或村民），与全智能高维 AI 智囊团（DeepSeek, Doubao 等模型）开展深度的非对称心理博弈。随时开启高维共情模拟对局。
                </p>
              </div>
              <div className="relative z-10 mt-8">
                 <span className="text-xs font-mono font-bold text-yellow-500 tracking-widest flex items-center gap-2 group-hover:translate-x-2 transition-transform">
                   开始博弈 (START GAME) →
                 </span>
              </div>
           </Link>

           {/* BIG CTA: Returns to Replays */}
           <Link 
             to="/runs" 
             className="group relative col-span-1 rounded-xl overflow-hidden shadow-xl border border-blue-500/40 bg-gradient-to-br from-[#0a101c] to-[#05080f] p-8 flex flex-col justify-between transition-all hover:border-blue-400 hover:shadow-[0_0_30px_rgba(59,130,246,0.15)]"
           >
              <div className="absolute -bottom-6 -right-6 pointer-events-none opacity-20 group-hover:opacity-80 transition-all duration-500 text-blue-500">
                 <History className="w-40 h-40" />
              </div>
              <div className="relative z-10 space-y-4">
                <span className="inline-block px-3 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-mono tracking-widest uppercase rounded">
                   档案记录 (Records)
                </span>
                <h2 className="text-2xl font-serif font-black text-blue-100 tracking-wide">战绩中心与复盘</h2>
                <p className="text-zinc-400 font-sans text-sm leading-relaxed">
                  回溯历史对局数据，随时打开先前的「时间线」、「MVP评分图表」以及「信念投票摇摆矩阵」，观看所有棋子视角下的战争推演历程。
                </p>
              </div>
              <div className="relative z-10 mt-6 lg:mt-0">
                 <span className="text-xs font-mono font-bold text-blue-400 tracking-widest flex items-center gap-2 group-hover:translate-x-2 transition-transform">
                   访问复盘库 (REPLAYS) →
                 </span>
              </div>
           </Link>

           {/* Small Box: Models Benchmark */}
           <Link 
             to="/models" 
             className="group relative rounded-xl border border-zinc-800 bg-zinc-950 p-6 transition-all hover:border-emerald-500/50 hover:bg-emerald-950/20"
           >
              <div className="flex items-center gap-3 mb-3">
                 <Server className="w-6 h-6 text-emerald-500" />
                 <h3 className="text-lg font-bold font-sans text-emerald-100">模型对弈跑分</h3>
              </div>
              <p className="text-xs text-zinc-400 leading-relaxed font-sans mt-2">
                 查阅当前接入本环境的所有 AI 语言模型，横向比较它们的说服力、夜间伪装值、整体存活胜率及综合 MVP 得分率。
              </p>
           </Link>

           {/* Small Box: Roles */}
           <Link 
             to="/roles" 
             className="group relative rounded-xl border border-zinc-800 bg-zinc-950 p-6 transition-all hover:border-purple-500/50 hover:bg-purple-950/20"
           >
              <div className="flex items-center gap-3 mb-3">
                 <Users className="w-6 h-6 text-purple-500" />
                 <h3 className="text-lg font-bold font-sans text-purple-100">角色权能圣典</h3>
              </div>
              <p className="text-xs text-zinc-400 leading-relaxed font-sans mt-2">
                 了解经典暗黑角色（女巫、猎人、预言家等）的设计机制、能力特征，以及对弈过程中的策略指导。
              </p>
           </Link>

           {/* Small Box: Rules */}
           <Link 
             to="/rules" 
             className="group relative rounded-xl border border-zinc-800 bg-zinc-950 p-6 transition-all hover:border-pink-500/50 hover:bg-pink-950/20"
           >
              <div className="flex items-center gap-3 mb-3">
                 <Scroll className="w-6 h-6 text-pink-500" />
                 <h3 className="text-lg font-bold font-sans text-pink-100">法官判定规则</h3>
              </div>
              <p className="text-xs text-zinc-400 leading-relaxed font-sans mt-2">
                 详细阐述白天公投阶段、黑夜刀位逻辑，以及 AI 模型间信念流转和胜利条件的核心判定法典。
              </p>
           </Link>

        </div>
        
        {/* Dynamic Chronicles / Highlights below dashboard */}
        <div className="border-t border-zinc-900 pt-8 max-w-4xl mx-auto w-full">
           <div className="flex items-center gap-2 mb-6">
              <Scroll className="w-5 h-5 text-yellow-500" />
              <h2 className="text-sm font-mono tracking-[0.2em] uppercase text-zinc-300 font-extrabold">
                石殿纪要 ∙ 最新风向 (CHRONICLES)
              </h2>
           </div>
           
           <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.highlights.map((item) => (
                <div 
                  key={item.id} 
                  className="bg-zinc-950/80 border border-zinc-900/60 p-5 rounded-lg flex flex-col gap-2 relative"
                >
                  <div className="flex justify-between items-center text-[10px] font-mono mb-1">
                    <span className="text-yellow-600 font-bold bg-yellow-500/5 border border-yellow-500/20 px-2 py-0.5 rounded">
                      {item.category}
                    </span>
                    <span className="text-zinc-500 flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {item.date}
                    </span>
                  </div>
                  <h3 className="text-[13px] font-bold font-sans text-zinc-300">
                    {item.title}
                  </h3>
                  <p className="text-xs text-zinc-500 leading-relaxed font-sans mt-1">
                    {item.summary}
                  </p>
                </div>
              ))}
           </div>
        </div>

      </div>

      {/* Heavy woodcut frame footer overlay */}
      <div className="mt-16 pb-8 text-center text-[10px] font-mono text-zinc-600 relative z-10 max-w-md mx-auto">
        <p className="uppercase tracking-[0.2em]">© 2026 虚境审判法庭 ∙ 全智能棋局</p>
        <p className="text-zinc-700 mt-1">Immersive Woodcut Dark-Anime Artstyle v2.1</p>
      </div>
    </div>
  );
}
