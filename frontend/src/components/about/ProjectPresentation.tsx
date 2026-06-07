import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ChevronDown, Sparkles } from "lucide-react";
import {
  MVP_CHECKLIST,
  PRESENTATION_HERO,
  PRESENTATION_NAV,
  PRESENTATION_SECTIONS,
  PRESENTATION_STATS,
  ROLE_CHIPS,
  SCORE_ROWS,
  type PresentationCard,
  type PresentationSection,
} from "../../content/projectPresentation";

interface ProjectPresentationProps {
  roleCount?: number;
  configCount?: number;
}

function CollapsePanel({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-4 py-2.5 rounded-lg border border-zinc-800 bg-zinc-950/60 text-left text-xs text-zinc-400 hover:border-yellow-500/30 hover:text-zinc-200 transition-colors"
      >
        <ChevronDown className={`w-3.5 h-3.5 shrink-0 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
        {label}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-2 px-1">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function CardGrid({ cards }: { cards: PresentationCard[] }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
      {cards.map((card) => (
        <motion.div
          key={card.title}
          initial={{ opacity: 0, y: 8 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ duration: 0.3 }}
          whileHover={{ y: -2, borderColor: "rgba(234,179,8,0.2)" }}
          className="bg-zinc-950/70 border border-zinc-900 rounded-lg p-4 transition-colors"
        >
          <h4 className="text-xs font-bold text-zinc-200 mb-1.5">{card.title}</h4>
          <p className="text-[11px] text-zinc-400 leading-relaxed">{card.description}</p>
          {card.badges && card.badges.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {card.badges.map((b) => (
                <span
                  key={b}
                  className="text-[9px] font-mono px-2 py-0.5 rounded border border-yellow-500/20 text-yellow-600/90 bg-yellow-500/5"
                >
                  {b}
                </span>
              ))}
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
}

function SectionBlock({ section }: { section: PresentationSection }) {
  return (
    <motion.section
      id={section.id}
      className="scroll-mt-24 py-10 border-b border-zinc-900/80 last:border-0"
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.4 }}
    >
      <div className="flex flex-wrap items-center gap-3 mb-5 pb-3 border-b border-zinc-900">
        <span className="text-[10px] font-mono font-bold text-yellow-500 bg-yellow-500/10 px-2.5 py-0.5 rounded">
          {section.num}
        </span>
        <h2 className="text-base sm:text-lg font-bold text-zinc-100 tracking-wide flex-1 min-w-[200px]">
          {section.title}
        </h2>
        <span className="text-[9px] font-mono uppercase tracking-widest text-zinc-600 border border-zinc-800 px-2 py-0.5 rounded">
          {section.tag}
        </span>
      </div>

      {section.intro && (
        <div className="mb-4 p-3 rounded-lg border-l-2 border-yellow-500/40 bg-yellow-500/[0.03] text-xs text-zinc-400 leading-relaxed">
          {section.intro}
        </div>
      )}

      {section.id === "agents" && (
        <div className="flex flex-wrap gap-2 mb-5">
          {ROLE_CHIPS.map((chip) => (
            <span
              key={chip}
              className="role-chip text-[11px] px-3 py-1 rounded-full border border-yellow-500/20 text-yellow-500/90 bg-yellow-500/5 hover:-translate-y-0.5 transition-transform cursor-default"
            >
              {chip}
            </span>
          ))}
        </div>
      )}

      {section.cards && <CardGrid cards={section.cards} />}

      {section.bullets && (
        <ul className="mt-3 space-y-2">
          {section.bullets.map((b) => (
            <li key={b} className="flex gap-2 text-xs text-zinc-400 leading-relaxed">
              <span className="text-yellow-600 shrink-0">•</span>
              <span>{b}</span>
            </li>
          ))}
        </ul>
      )}

      {section.highlights && (
        <div className="flex flex-wrap gap-2 mt-4">
          {section.highlights.map((h) => (
            <span
              key={h}
              className="text-[10px] font-mono px-2.5 py-1 rounded border border-zinc-800 text-zinc-500 bg-zinc-900/40"
            >
              {h}
            </span>
          ))}
        </div>
      )}

      {section.subsections?.map((sub) => (
        <div key={sub.title} className="mt-6">
          <h3 className="text-sm font-bold text-zinc-300 mb-2 flex items-center gap-2">
            <span className="w-1 h-4 rounded-full bg-yellow-500/60" />
            {sub.title}
          </h3>
          {sub.highlights && (
            <div className="space-y-2 mb-2">
              {sub.highlights.map((h) => (
                <div
                  key={h}
                  className="text-[11px] text-zinc-400 border-l-2 border-yellow-500/40 pl-3 leading-relaxed"
                >
                  {h}
                </div>
              ))}
            </div>
          )}
          {sub.bullets && (
            <ul className="space-y-1.5">
              {sub.bullets.map((b) => (
                <li key={b} className="text-xs text-zinc-400 flex gap-2">
                  <span className="text-yellow-600">→</span>
                  {b}
                </li>
              ))}
            </ul>
          )}
          {sub.cards && <CardGrid cards={sub.cards} />}
          {sub.collapsible && (
            <CollapsePanel label={sub.collapsible.label}>
              {sub.collapsible.bullets && (
                <ul className="space-y-2 pl-2">
                  {sub.collapsible.bullets.map((b) => (
                    <li key={b} className="text-xs text-zinc-400 leading-relaxed">
                      {b}
                    </li>
                  ))}
                </ul>
              )}
              {sub.collapsible.cards && <CardGrid cards={sub.collapsible.cards} />}
            </CollapsePanel>
          )}
        </div>
      ))}
    </motion.section>
  );
}

export default function ProjectPresentation({ roleCount, configCount }: ProjectPresentationProps) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const onScroll = () => {
      const el = document.documentElement;
      const max = el.scrollHeight - el.clientHeight;
      setProgress(max > 0 ? (window.scrollY / max) * 100 : 0);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const stats = PRESENTATION_STATS.map((s) =>
    s.label === "可扮演角色" && roleCount ? { ...s, value: String(roleCount) } : s
  );

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="relative">
      <div
        className="fixed top-0 left-0 right-0 h-0.5 z-50 bg-gradient-to-r from-yellow-500 to-violet-500 transition-[width]"
        style={{ width: `${progress}%` }}
      />

      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center py-12 md:py-16 px-4 border-b border-zinc-900/80"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 border border-yellow-500/20 rounded-full text-[9px] font-mono text-yellow-500 tracking-[0.2em] uppercase mb-5">
          <Sparkles className="w-3 h-3" />
          {PRESENTATION_HERO.badge}
        </div>
        <h1 className="text-2xl sm:text-4xl font-black tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-zinc-100 via-yellow-400 to-yellow-600">
          {PRESENTATION_HERO.title}
          <br className="hidden sm:block" />
          <span className="sm:ml-0">{PRESENTATION_HERO.titleLine2}</span>
        </h1>
        <p className="mt-3 text-[11px] font-mono text-zinc-500 tracking-wider uppercase">
          {PRESENTATION_HERO.subtitle}
        </p>
        <p className="mt-4 text-xs text-zinc-400 max-w-2xl mx-auto leading-relaxed">
          {PRESENTATION_HERO.description}
        </p>

        <div className="flex flex-wrap justify-center gap-8 sm:gap-12 mt-8">
          {stats.map((s) => (
            <div key={s.label} className="text-center">
              <div className="text-2xl sm:text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-br from-yellow-400 to-violet-400">
                {s.value}
              </div>
              <div className="text-[9px] font-mono text-zinc-600 uppercase tracking-widest mt-1">
                {s.label}
              </div>
            </div>
          ))}
        </div>

        {configCount !== undefined && configCount > 0 && (
          <p className="mt-6 text-[10px] font-mono text-zinc-600">
            平台已配置 {configCount} 套模型方案 · 支持 6–20 人标准板子
          </p>
        )}
      </motion.div>

      <div className="sticky top-0 z-40 bg-zinc-950/90 backdrop-blur-md border-b border-zinc-900 px-4 py-2 overflow-x-auto scrollbar-none">
        <div className="max-w-5xl mx-auto flex gap-2 min-w-max">
          {PRESENTATION_NAV.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => scrollTo(item.id)}
              className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider rounded border border-zinc-800 text-zinc-500 hover:text-yellow-500 hover:border-yellow-500/30 transition-colors whitespace-nowrap"
            >
              {item.label}
            </button>
          ))}
          <button
            type="button"
            onClick={() => scrollTo("scoring")}
            className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider rounded border border-zinc-800 text-zinc-500 hover:text-yellow-500 hover:border-yellow-500/30 transition-colors whitespace-nowrap"
          >
            评分对照
          </button>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 pb-16">
        {PRESENTATION_SECTIONS.map((section) => (
          <SectionBlock key={section.id} section={section} />
        ))}

        <section id="scoring" className="scroll-mt-24 py-10">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.4 }}
          >
            <div className="flex items-center gap-3 mb-6 pb-3 border-b border-zinc-900">
              <span className="text-[10px] font-mono font-bold text-yellow-500 bg-yellow-500/10 px-2.5 py-0.5 rounded">
                07
              </span>
              <h2 className="text-lg font-bold text-zinc-100">评分维度对照</h2>
            </div>

            <div className="overflow-x-auto rounded-lg border border-zinc-900">
              <table className="w-full text-left text-[11px] min-w-[640px]">
                <thead>
                  <tr className="bg-zinc-900/60 text-zinc-300">
                    <th className="p-3 font-semibold">维度</th>
                    <th className="p-3 w-12">权重</th>
                    <th className="p-3">满分标准</th>
                    <th className="p-3">项目实现</th>
                    <th className="p-3 w-20">档位</th>
                  </tr>
                </thead>
                <tbody>
                  {SCORE_ROWS.map((row) => (
                    <tr key={row.dimension} className="border-t border-zinc-900 hover:bg-yellow-500/[0.02]">
                      <td className="p-3 text-zinc-200 font-medium">{row.dimension}</td>
                      <td className="p-3 text-zinc-500 font-mono">{row.weight}</td>
                      <td className="p-3 text-zinc-400 leading-relaxed">{row.standard}</td>
                      <td className="p-3 text-zinc-400 leading-relaxed">{row.implementation}</td>
                      <td className="p-3">
                        <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-yellow-500/10 text-yellow-500 border border-yellow-500/20">
                          {row.tier}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-6 p-4 rounded-lg border border-yellow-500/20 bg-yellow-500/5 text-xs text-zinc-300 leading-relaxed border-l-2 border-l-yellow-500">
              <strong className="text-yellow-400">总结：</strong>
              本项目覆盖课题基础要求、加分项与进阶双方向全选，在 Agent 调优、多智能体系统设计与工程完整度三个维度均达到可演示、可评测、可演进的生产级水准。
            </div>

            <h3 className="text-sm font-bold text-zinc-300 mt-8 mb-4">MVP Checklist</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {MVP_CHECKLIST.map((item) => (
                <motion.div
                  key={item}
                  initial={{ opacity: 0, x: -8 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.3 }}
                  className="flex items-start gap-2 p-3 rounded-lg border border-zinc-900 bg-zinc-950/50 text-xs text-zinc-400"
                >
                  <span className="text-emerald-500 font-bold shrink-0">✓</span>
                  <span>{item}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </section>

        <footer className="text-center py-8 text-[10px] font-mono text-zinc-600 tracking-widest uppercase border-t border-zinc-900">
          Agent Teams 实践 — AI 狼人杀 · 2026
        </footer>
      </div>
    </div>
  );
}
