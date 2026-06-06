import React from "react";
import { Link, useLocation } from "react-router-dom";
import { motion } from "motion/react";
import { 
  Info, 
  Sparkles, 
  BookOpen, 
  Moon, 
  Flame, 
  HelpCircle,
  Scroll,
  ArrowRight
} from "lucide-react";

interface ContentPageLayoutProps {
  title: string;
  subtitle: string;
  description: string;
  sections?: { title: string; value: string }[];
  children?: React.ReactNode;
}

export default function ContentPageLayout({
  title,
  subtitle,
  description,
  sections,
  children
}: ContentPageLayoutProps) {
  const location = useLocation();
  const currentPath = location.pathname;

  const tabs = [
    { name: "关于虚境 (ABOUT)", path: "/about", icon: Info },
    { name: "核心特性 (FEATURES)", path: "/features", icon: Sparkles },
    { name: "法典法章 (GUIDE)", path: "/how-to-play", icon: BookOpen },
    { name: "黑夜行纪 (NIGHT ACTIONS)", path: "/night-phase", icon: Moon },
    { name: "智斗秘卷 (STRATEGY)", path: "/strategy", icon: Flame }
  ];

  return (
    <div className="text-zinc-100 max-w-7xl mx-auto py-8 px-4 sm:px-6 md:px-8 select-none antialiased">
      {/* 1. Sub-navigation tabs matching the tactical manual aesthetic */}
      <div className="flex border-b border-zinc-900 mb-8 overflow-x-auto scrollbar-none select-none">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = currentPath === tab.path;
          return (
            <Link
              key={tab.path}
              to={tab.path}
              className={`flex items-center gap-2 px-6 py-4 border-b-2 text-[10px] font-mono tracking-widest transition-all whitespace-nowrap uppercase ${
                isActive 
                  ? "border-yellow-500 text-yellow-500 font-bold bg-[#eae5db]/[0.02]" 
                  : "border-transparent text-zinc-500 hover:text-zinc-300"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.name}
            </Link>
          );
        })}
      </div>

      {/* 2. Page Header Block */}
      <motion.div 
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden border border-zinc-900 rounded bg-gradient-to-br from-zinc-950 via-zinc-900/90 to-zinc-950 p-6 sm:p-8 mb-8"
      >
        <div className="absolute top-0 right-0 w-64 h-64 blur-3xl opacity-10 pointer-events-none rounded-full bg-yellow-500/30" />
        
        <div className="relative z-10 space-y-3 max-w-4xl">
          <span className="px-2.5 py-0.5 text-[9px] font-mono tracking-widest text-[#eae5db] border border-zinc-800 rounded bg-zinc-900/60 uppercase">
            {subtitle}
          </span>
          <h1 className="font-serif text-xl sm:text-2xl font-black text-[#eae5db] tracking-widest uppercase">
            {title}
          </h1>
          <p className="text-xs text-zinc-400 leading-relaxed font-sans max-w-3xl">
            {description}
          </p>
        </div>
      </motion.div>

      {/* 3. Core Grid Split Layout: Common metadata/sections left, specific components right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* Left Column: Handbook sections (Standardized Content) */}
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-zinc-950/80 border border-zinc-900 rounded p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1 h-full bg-yellow-500/20" />
            <span className="font-serif text-[10px] tracking-widest text-zinc-400 font-bold uppercase block mb-6 pb-2 border-b border-zinc-900/60 flex items-center gap-1.5">
              <Scroll className="w-3.5 h-3.5 text-yellow-600" />
              法理与研究编目 (CATALOGUE)
            </span>

            <div className="space-y-6">
              {sections && sections.map((sec, idx) => (
                <div key={idx} className="space-y-1.5">
                  <h4 className="font-serif text-zinc-200 text-xs font-black tracking-wider block">
                    {sec.title}
                  </h4>
                  <p className="text-[11px] text-zinc-400 leading-relaxed font-sans">
                    {sec.value}
                  </p>
                </div>
              ))}

              {!sections || sections.length === 0 ? (
                <p className="text-[11px] text-zinc-500 italic">暂无归档内容页备注。</p>
              ) : null}
            </div>
            
            <div className="mt-8 pt-4 border-t border-zinc-905 bg-gradient-to-r from-zinc-950 to-zinc-900/25 p-3 rounded text-[10px] font-mono text-zinc-500 leading-normal">
              <HelpCircle className="w-4 h-4 text-zinc-400 inline mr-1 mb-0.5" />
              本章出自落暮圣堂撰写的历史法典编篡，旨在向棋子兜帽大模型及人类引航者提供最高阶的博弈参数索引。
            </div>
          </div>
        </div>

        {/* Right Column: Dynamic Specific Components Layout */}
        <div className="lg:col-span-8">
          {children}
        </div>

      </div>
    </div>
  );
}
