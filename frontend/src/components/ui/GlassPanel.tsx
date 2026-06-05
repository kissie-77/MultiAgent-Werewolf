import { ReactNode } from "react";

interface GlassPanelProps {
  children: ReactNode;
  className?: string;
  title?: string;
}

export default function GlassPanel({ children, className = "", title }: GlassPanelProps) {
  return (
    <div
      className={`rounded border border-zinc-800/60 bg-black/45 p-5 shadow-[0_8px_32px_rgba(0,0,0,0.45)] backdrop-blur-md ${className}`}
    >
      {title && (
        <h2 className="mb-4 border-b border-zinc-800/80 pb-2 font-serif text-sm font-black uppercase tracking-widest text-zinc-100">
          {title}
        </h2>
      )}
      {children}
    </div>
  );
}
