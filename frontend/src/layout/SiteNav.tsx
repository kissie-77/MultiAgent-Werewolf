import { NavLink } from "react-router-dom";
import { Flame } from "lucide-react";

const NAV_ITEMS = [
  { to: "/", label: "首页", end: true },
  { to: "/game", label: "对局" },
  { to: "/roles", label: "角色" },
  { to: "/models", label: "模型" },
  { to: "/features", label: "功能" },
  { to: "/how-to-play", label: "玩法" },
  { to: "/strategy", label: "攻略" },
  { to: "/about", label: "关于" },
] as const;

export default function SiteNav() {
  return (
    <header className="pointer-events-auto shrink-0 border-b border-zinc-900/60 bg-black/50 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-2.5 md:px-6">
        <NavLink to="/" className="group flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded border border-red-900/60 bg-red-950/40">
            <Flame className="h-4 w-4 text-red-500 group-hover:animate-pulse" />
          </div>
          <div className="hidden flex-col sm:flex">
            <span className="font-serif text-xs font-black uppercase tracking-[0.2em] text-zinc-100">
              宿命审判
            </span>
            <span className="font-mono text-[8px] uppercase tracking-widest text-zinc-500">
              AI Werewolf Arena
            </span>
          </div>
        </NavLink>

        <nav className="flex flex-wrap items-center justify-end gap-1 md:gap-2">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={"end" in item ? item.end : false}
              className={({ isActive }) =>
                [
                  "rounded px-2 py-1 font-mono text-[10px] font-bold uppercase tracking-wider transition-colors md:px-3 md:text-[11px]",
                  isActive
                    ? "bg-yellow-500/15 text-yellow-400 ring-1 ring-yellow-500/30"
                    : "text-zinc-400 hover:bg-zinc-900/80 hover:text-zinc-100",
                ].join(" ")
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
