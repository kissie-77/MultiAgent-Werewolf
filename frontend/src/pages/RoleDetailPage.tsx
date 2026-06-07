import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiClient } from "../api/client";
import { RoleDetail } from "../api/types";
import {
  ArrowLeft,
  Scroll,
  BookOpen,
  Flame,
  Compass,
  Skull,
  Sparkles,
  Layers,
} from "lucide-react";
import { motion } from "motion/react";
import { getRoleImage } from "../utils/roles";

export default function RoleDetailPage() {
  const { roleKey } = useParams<{ roleKey: string }>();
  const [role, setRole] = useState<RoleDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!roleKey) return;
    let active = true;

    ApiClient.getRoleDetail(roleKey)
      .then((data) => {
        if (active) {
          setRole(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          console.error(err);
          setError("命运卷宗残破，可能星盘中并无此角色印记，或审判传输错误。");
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [roleKey]);

  const getAlignmentBadge = (align?: RoleDetail["alignment"]) => {
    switch (align) {
      case "GOOD":
        return (
          <span className="px-3 py-1 rounded-full text-xs font-sans font-bold bg-yellow-500/10 border border-yellow-500/30 text-yellow-500 tracking-wider">
            ★ 神圣忠良阵营
          </span>
        );
      case "EVIL":
        return (
          <span className="px-3 py-1 rounded-full text-xs font-sans font-bold bg-red-500/10 border border-red-500/30 text-red-500 tracking-wider">
            ★ 暗夜深渊恶狼
          </span>
        );
      default:
        return (
          <span className="px-3 py-1 rounded-full text-xs font-sans font-bold bg-zinc-800 border border-zinc-700 text-zinc-300 tracking-wider">
            ★ 中立第三方
          </span>
        );
    }
  };

  const getTimingBadge = (timing: "NIGHT" | "DAY" | "PASSIVE") => {
    switch (timing) {
      case "NIGHT":
        return "bg-violet-950/40 border-violet-500/40 text-violet-300";
      case "DAY":
        return "bg-yellow-950/40 border-yellow-500/40 text-yellow-300";
      default:
        return "bg-zinc-800/40 border-zinc-700 text-zinc-300";
    }
  };

  const timingLabel = (timing: "NIGHT" | "DAY" | "PASSIVE") => {
    switch (timing) {
      case "NIGHT":
        return "暗夜发动";
      case "DAY":
        return "白昼论断";
      default:
        return "被动刻印";
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center text-zinc-400 font-sans text-xs tracking-widest gap-2">
        <div className="w-6 h-6 border-2 border-t-yellow-500 border-zinc-900 rounded-full animate-spin" />
        <span>翻阅圣约古籍中...</span>
      </div>
    );
  }

  if (error || !role) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center text-center p-6 gap-6 relative">
        <div className="absolute inset-10 border border-red-500/10 pointer-events-none rounded" />
        <Skull className="w-14 h-14 text-red-500/80 animate-pulse" />
        <div className="space-y-1">
          <h2 className="text-lg font-bold font-sans tracking-widest text-zinc-200">卷宗已被黑夜吞噬</h2>
          <p className="text-zinc-500 font-sans text-xs max-w-sm">{error || "找不到该角色的古老事迹。"}</p>
        </div>
        <Link
          to="/roles"
          className="px-5 py-2.5 bg-zinc-950 border border-zinc-800 text-xs font-sans text-zinc-300 hover:border-yellow-500 hover:text-white rounded"
        >
          返回圣约主廊 (BACK)
        </Link>
      </div>
    );
  }

  const promptByCategory = role.promptLibrary.reduce<Record<string, typeof role.promptLibrary>>(
    (acc, entry) => {
      acc[entry.category] = acc[entry.category] ?? [];
      acc[entry.category].push(entry);
      return acc;
    },
    {}
  );

  return (
    <div className="max-w-5xl mx-auto px-4 py-12 md:py-16">
      <div className="mb-8">
        <Link
          to="/roles"
          className="inline-flex items-center gap-2 text-xs font-sans tracking-widest text-zinc-400 hover:text-yellow-500 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          返回角色刻印主廊
        </Link>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-zinc-950/90 border border-zinc-900 rounded shadow-2xl overflow-hidden"
      >
        <div className="grid grid-cols-1 md:grid-cols-12 gap-0">
          <div className="md:col-span-4 relative aspect-[3/4] md:aspect-auto md:min-h-[320px] bg-zinc-900">
            <img
              src={getRoleImage(role.key)}
              alt={role.chineseName}
              className="w-full h-full object-cover object-top"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-transparent to-transparent md:bg-gradient-to-r" />
          </div>

          <div className="md:col-span-8 p-6 md:p-10 space-y-6 border-b border-zinc-900">
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
              <div>
                <div className="inline-flex items-center gap-2 px-2 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-[9px] font-mono text-yellow-600 uppercase tracking-widest mb-2">
                  <Sparkles className="w-3 h-3" />
                  {role.promptRoleKey || role.key}
                </div>
                <h1 className="text-2xl md:text-3xl font-black font-sans tracking-wider text-zinc-100">
                  {role.chineseName}
                </h1>
                <span className="text-zinc-600 font-mono text-sm uppercase">({role.name})</span>
                <p className="text-xs text-yellow-600/90 font-serif italic mt-2">「 {role.tagline} 」</p>
              </div>
              <div className="flex flex-col items-start md:items-end gap-2 shrink-0">
                {getAlignmentBadge(role.alignment)}
                <span className="text-[10px] font-sans text-zinc-500">
                  提升词 {role.promptVersion ?? "v1"} ({role.promptLibrary.length}) · 技能{" "}
                  {role.skillVersion ?? "v1"} ({role.skillLibrary.length})
                </span>
              </div>
            </div>

            <p className="text-xs text-zinc-400 leading-relaxed font-sans">{role.lore}</p>

            {role.suggestion && (
              <p className="text-[11px] text-zinc-500 border-l-2 border-yellow-500/30 pl-3 italic">
                {role.suggestion}
              </p>
            )}
          </div>
        </div>

        <div className="p-6 md:p-10 space-y-10">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-zinc-300 border-b border-zinc-900 pb-1.5">
                <Scroll className="w-4 h-4 text-fuchsia-400" />
                <h2 className="text-xs font-sans font-extrabold tracking-widest">规则权能</h2>
              </div>
              <div className="space-y-3">
                {role.skills.map((skill, i) => (
                  <div
                    key={i}
                    className="bg-zinc-900/40 border border-zinc-900 p-4 rounded flex flex-col gap-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-zinc-200">{skill.name}</h4>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[8px] font-mono border uppercase ${getTimingBadge(skill.timing)}`}
                      >
                        {timingLabel(skill.timing)}
                      </span>
                    </div>
                    <p className="text-[11px] text-zinc-400 leading-relaxed">{skill.description}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-2 text-zinc-300 border-b border-zinc-900 pb-1.5">
                <Flame className="w-4 h-4 text-orange-400" />
                <h2 className="text-xs font-sans font-extrabold tracking-widest">智术韬略</h2>
              </div>
              <ul className="space-y-2.5">
                {role.strategies.map((strat, i) => (
                  <li key={i} className="flex gap-2 text-xs text-zinc-400 leading-relaxed font-sans">
                    <span className="text-yellow-500 font-mono font-bold shrink-0">[{i + 1}]</span>
                    <span>{strat}</span>
                  </li>
                ))}
                {role.strategies.length === 0 && (
                  <li className="text-xs text-zinc-600 font-sans">暂无策略词条</li>
                )}
              </ul>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-900 pb-1.5">
              <div className="flex items-center gap-2 text-zinc-300">
                <BookOpen className="w-4 h-4 text-violet-400" />
                <h2 className="text-xs font-sans font-extrabold tracking-widest">
                  提升词库 · PROMPT LIBRARY
                </h2>
              </div>
              <span className="text-[9px] font-mono text-violet-500/80 uppercase">
                @{role.promptVersion ?? role.promptLibrary[0]?.version ?? "v1"}
              </span>
            </div>
            {role.promptLibrary.length === 0 ? (
              <p className="text-xs text-zinc-600 font-sans">该角色暂无提升词条</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(promptByCategory).map(([category, entries]) => (
                  <div
                    key={category}
                    className="bg-zinc-900/30 border border-zinc-900 rounded p-4 space-y-2"
                  >
                    <div className="flex items-center gap-2">
                      <Layers className="w-3.5 h-3.5 text-violet-500" />
                      <h3 className="text-[10px] font-sans font-bold text-violet-300 tracking-widest">
                        {category}
                      </h3>
                      <span className="text-[9px] text-zinc-600 font-mono ml-auto">{entries.length}</span>
                    </div>
                    <ul className="space-y-2">
                      {entries.map((entry) => (
                        <li key={entry.id} className="text-[11px] text-zinc-400 leading-relaxed">
                          {entry.title !== category && (
                            <span className="text-zinc-300 font-semibold block text-[10px] mb-0.5">
                              {entry.title}
                            </span>
                          )}
                          {entry.content}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-900 pb-1.5">
              <div className="flex items-center gap-2 text-zinc-300">
                <Scroll className="w-4 h-4 text-fuchsia-400" />
                <h2 className="text-xs font-sans font-extrabold tracking-widest">
                  技能库 · SKILL LIBRARY
                </h2>
              </div>
              <span className="text-[9px] font-mono text-fuchsia-500/80 uppercase">
                @{role.skillVersion ?? role.skillLibrary[0]?.version ?? "v1"} · {role.skillLibrary.length} 条
              </span>
            </div>
            {role.skillLibrary.length === 0 ? (
              <p className="text-xs text-zinc-600 font-sans">该角色暂无对局技能卡片</p>
            ) : (
              <div className="space-y-3">
                {role.skillLibrary.map((skill) => (
                  <div
                    key={skill.id}
                    className="bg-zinc-900/40 border border-zinc-900 p-4 rounded flex flex-col gap-2"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h4 className="text-xs font-bold text-zinc-200 font-mono">{skill.id}</h4>
                      <div className="flex items-center gap-2 text-[8px] font-mono uppercase">
                        <span className="px-1.5 py-0.5 rounded border border-emerald-500/30 text-emerald-400 bg-emerald-950/30">
                          {skill.status}
                        </span>
                        <span className="text-zinc-600">w={skill.weight.toFixed(2)}</span>
                        <span className="text-zinc-600">@{skill.version}</span>
                      </div>
                    </div>
                    <p className="text-[11px] text-zinc-400 leading-relaxed">{skill.description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {role.relationships.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-zinc-300 border-b border-zinc-900 pb-1.5">
                <Compass className="w-4 h-4 text-emerald-400" />
                <h2 className="text-xs font-sans font-extrabold tracking-widest">关联角色</h2>
              </div>
              <div className="flex flex-wrap gap-2">
                {role.relationships.map((rel, i) => (
                  <Link
                    key={i}
                    to={`/roles/${rel.targetRoleName}`}
                    className="px-3 py-1.5 bg-zinc-900 border border-zinc-800 hover:border-yellow-500/40 rounded text-[10px] font-sans text-zinc-400 hover:text-yellow-500 transition-colors"
                  >
                    {rel.targetRoleName}
                  </Link>
                ))}
              </div>
            </div>
          )}

          <div className="pt-4 border-t border-zinc-900/50 flex justify-between items-center text-[9px] font-mono text-zinc-600">
            <span>ROLE ARCHIVE · {role.key}</span>
            <span>
              {role.boardSizes && role.boardSizes.length > 0
                ? `出现于 ${role.boardSizes.join("/")} 人局`
                : "ARCANUM DECK"}
            </span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
