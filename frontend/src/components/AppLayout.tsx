import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Shield, Home, Scroll, History, Info, Users, Cpu, ArrowLeft, AlertTriangle } from "lucide-react";
import ErrorBoundary from "./ErrorBoundary";

interface AppLayoutProps {
  children: React.ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const currentPath = location.pathname;
  const isHome = currentPath === "/home";

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-950 via-slate-900 to-blue-950 text-slate-100 flex flex-col relative">
      {!isHome && (
        <header className="border-b border-indigo-900/50 bg-slate-950/60 backdrop-blur-md sticky top-0 z-50 px-6 py-4 flex items-center justify-between select-none shadow-md">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate(-1)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900/50 hover:bg-zinc-800 border border-zinc-700/50 rounded font-sans text-[10px] text-zinc-300 tracking-widest transition-colors cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              返回上一页
            </button>
            <div className="h-4 w-px bg-zinc-700 mx-1" />
            <Link
              to="/home"
              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-900/20 hover:bg-blue-900/40 border border-blue-700/50 rounded font-sans text-[10px] text-blue-300 tracking-widest transition-colors cursor-pointer"
            >
              <Shield className="w-3.5 h-3.5" />
              回到主界面
            </Link>
          </div>

          <nav className="flex items-center gap-5 text-[10px] font-sans tracking-widest shadow-sm bg-slate-900/50 px-4 py-2 rounded-full border border-indigo-500/20">
            <Link to="/home" className={`hover:text-blue-400 transition-colors flex items-center gap-1.2 ${currentPath === "/home" ? "text-blue-400 font-bold drop-shadow-[0_0_8px_rgba(96,165,250,0.8)]" : "text-slate-400"}`}>
              <Home className="w-3.5 h-3.5" />首页 (HOME)
            </Link>
            <Link to="/roles" className={`hover:text-purple-400 transition-colors flex items-center gap-1.2 ${currentPath.startsWith("/roles") ? "text-purple-400 font-bold drop-shadow-[0_0_8px_rgba(192,132,252,0.8)]" : "text-slate-400"}`}>
              <Users className="w-3.5 h-3.5" />角色 (ROLES)
            </Link>
            <Link to="/models" className={`hover:text-emerald-400 transition-colors flex items-center gap-1.2 ${currentPath.startsWith("/models") ? "text-emerald-400 font-bold drop-shadow-[0_0_8px_rgba(52,211,153,0.8)]" : "text-slate-400"}`}>
              <Cpu className="w-3.5 h-3.5" />模型 (MODELS)
            </Link>
            <Link to="/rules" className={`hover:text-pink-400 transition-colors flex items-center gap-1.2 ${currentPath === "/rules" ? "text-pink-400 font-bold drop-shadow-[0_0_8px_rgba(244,114,182,0.8)]" : "text-slate-400"}`}>
              <Scroll className="w-3.5 h-3.5" />规则 (RULES)
            </Link>
            <Link to="/runs" className={`hover:text-amber-400 transition-colors flex items-center gap-1.2 ${currentPath.startsWith("/runs") ? "text-amber-400 font-bold drop-shadow-[0_0_8px_rgba(251,191,36,0.8)]" : "text-slate-400"}`}>
              <History className="w-3.5 h-3.5" />战绩 (RUNS)
            </Link>
            <Link to="/about" className={`hover:text-cyan-400 transition-colors flex items-center gap-1.2 ${currentPath === "/about" ? "text-cyan-400 font-bold drop-shadow-[0_0_8px_rgba(34,211,238,0.8)]" : "text-slate-400"}`}>
              <Info className="w-3.5 h-3.5" />关于 (ABOUT)
            </Link>
          </nav>

          <Link to="/" className="px-5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-500 hover:to-indigo-500 font-sans font-black text-[10px] tracking-wider rounded-lg shadow-[0_4px_15px_rgba(79,70,229,0.4)] transition-all transform hover:scale-105">
            重返星盘 →
          </Link>
        </header>
      )}

      <main className="flex-grow z-10">
        <ErrorBoundary
          key={currentPath}
          label={currentPath}
          fallback={
            <div className="min-h-[70vh] flex flex-col items-center justify-center text-center gap-4 px-4">
              <AlertTriangle className="w-12 h-12 text-amber-500" />
              <p className="font-sans text-sm text-zinc-300 tracking-wider">页面渲染异常，已安全兜底。</p>
              <div className="flex gap-3">
                <button onClick={() => window.location.reload()} className="px-4 py-2 bg-zinc-900 border border-zinc-700 rounded font-sans text-xs text-zinc-200 hover:border-amber-500">重新加载</button>
                <Link to="/home" className="px-4 py-2 bg-blue-900/30 border border-blue-700/50 rounded font-sans text-xs text-blue-200 hover:border-blue-400">回到主界面</Link>
              </div>
            </div>
          }
        >
          {children}
        </ErrorBoundary>
      </main>
    </div>
  );
}