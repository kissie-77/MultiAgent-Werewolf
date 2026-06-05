import { ReactNode } from "react";

interface PageHeroProps {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  children?: ReactNode;
}

export default function PageHero({ eyebrow, title, subtitle, children }: PageHeroProps) {
  return (
    <section className="mb-10 text-center">
      {eyebrow && (
        <div className="mb-4 inline-block border border-zinc-800 bg-zinc-900/80 px-3 py-1 font-mono text-[9px] uppercase tracking-[0.25em] text-yellow-500">
          {eyebrow}
        </div>
      )}
      <h1 className="font-serif text-3xl font-black uppercase tracking-[0.15em] text-[#e5e5e0] ink-shadow md:text-4xl">
        {title}
      </h1>
      {subtitle && (
        <p className="mx-auto mt-4 max-w-2xl font-mono text-[11px] leading-relaxed tracking-wide text-zinc-400">
          {subtitle}
        </p>
      )}
      {children && <div className="mt-6 flex flex-wrap items-center justify-center gap-3">{children}</div>}
    </section>
  );
}
