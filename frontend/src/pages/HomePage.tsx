import { Link } from "react-router-dom";
import ThreeCanvas from "../components/ThreeCanvas";
import LaunchHero from "../components/LaunchHero";
import { fetchPage } from "../api/client";
import { usePageData } from "../hooks/usePageData";
import { Flame } from "lucide-react";

interface HomePageData {
  stats_cards: { label: string; value: string | number }[];
}

/** 全站启动页：3D 圆桌 + 哥特 Hero，风格与对局 START_SCREEN 一致 */
export default function HomePage() {
  const { data: homeData } = usePageData(() => fetchPage<HomePageData>("/pages/home"));

  return (
    <div className="relative flex h-screen w-screen flex-col overflow-hidden bg-[#0b0914] font-sans text-zinc-100 antialiased">
      <ThreeCanvas />

      {/* 顶栏 */}
      <header className="pointer-events-auto relative z-20 flex items-center justify-between border-b border-zinc-900/50 bg-black/40 px-5 py-2 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <Flame className="h-4 w-4 text-red-500" />
          <span className="font-serif text-xs font-black uppercase tracking-[0.15em]">宿命审判</span>
        </div>
        <nav className="flex gap-3 font-mono text-[10px] font-bold uppercase tracking-wider">
          <Link to="/features" className="text-zinc-500 hover:text-zinc-200">
            功能
          </Link>
          <Link to="/roles" className="text-zinc-500 hover:text-zinc-200">
            角色
          </Link>
          <Link to="/game" className="text-yellow-500 hover:text-yellow-300">
            对局 →
          </Link>
        </nav>
      </header>

      {/* Hero */}
      <div className="pointer-events-auto relative z-10 flex flex-1 flex-col items-center justify-center">
        <LaunchHero />
      </div>

      {homeData && homeData.stats_cards.length > 0 && (
        <div className="pointer-events-none relative z-10 border-t border-zinc-900/40 bg-black/30 py-2 text-center font-mono text-[9px] uppercase tracking-widest text-zinc-600">
          {homeData.stats_cards.slice(0, 2).map((c) => `${c.label} ${c.value}`).join(" · ")}
        </div>
      )}

      <div className="pointer-events-none absolute inset-0 z-50 rounded border-4 border-zinc-950/80" />
      <div className="pointer-events-none absolute inset-x-0 top-0 z-50 h-1 bg-gradient-to-b from-[#a855f7]/30 to-transparent" />
    </div>
  );
}
