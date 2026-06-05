import { ReactNode } from "react";
import SiteNav from "./SiteNav";

interface SiteShellProps {
  children: ReactNode;
  /** 全宽内容（如游戏页）时不限制 max-width */
  fullBleed?: boolean;
  /** 隐藏顶栏（游戏页自带 HUD） */
  hideNav?: boolean;
}

export default function SiteShell({ children, fullBleed = false, hideNav = false }: SiteShellProps) {
  return (
    <div className="relative min-h-screen bg-[#0b0914] text-zinc-100 antialiased">
      <div className="pointer-events-none absolute inset-0 woodcut-texture opacity-40" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-[#a855f7]/10 to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 left-0 w-px bg-gradient-to-b from-[#a855f7]/30 via-transparent to-transparent" />

      <div className="relative z-10 flex min-h-screen flex-col">
        {!hideNav && <SiteNav />}
        <main className={fullBleed ? "flex-1" : "mx-auto w-full max-w-7xl flex-1 px-4 py-8 md:px-6"}>
          {children}
        </main>
      </div>

      <div className="pointer-events-none absolute inset-0 z-50 rounded border-4 border-zinc-950/80" />
    </div>
  );
}
