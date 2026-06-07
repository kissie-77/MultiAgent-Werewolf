import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ApiClient } from "../api/client";
import { RoleSummary } from "../api/types";
import { ArrowRight, BookOpen, Sparkles, Skull, Scroll, Users, Filter } from "lucide-react";
import { motion } from "motion/react";
import { getRoleImage } from "../utils/roles";

type CampFilter = "all" | "werewolf" | "villager" | "neutral";

const CAMP_LABELS: Record<CampFilter, string> = {
  all: "全部刻印",
  werewolf: "狼人阵营",
  villager: "好人阵营",
  neutral: "第三方",
};

export default function RolesPage() {
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [campStats, setCampStats] = useState<Record<string, number>>({});
  const [introTitle, setIntroTitle] = useState("");
  const [introText, setIntroText] = useState("");
  const [campFilter, setCampFilter] = useState<CampFilter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    ApiClient.getRolesPageData()
      .then((data) => {
        if (active) {
          setRoles(data.roles || []);
          setCampStats(data.campStats ?? {});
          setIntroTitle(data.introTitle || "圣誓宿命圣徽一览");
          setIntroText(data.introText || "");
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          console.error(err);
          setError("暗海翻卷，圣史官卷宗传输受阻，无法读取身份碑。");
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const filteredRoles = useMemo(() => {
    if (campFilter === "all") return roles;
    return roles.filter((role) => {
      if (campFilter === "werewolf") return role.alignment === "EVIL";
      if (campFilter === "villager") return role.alignment === "GOOD";
      return role.alignment === "NEUTRAL";
    });
  }, [roles, campFilter]);

  const getAlignmentBadge = (align: RoleSummary["alignment"]) => {
    switch (align) {
      case "GOOD":
        return (
          <span className="px-2 py-0.5 rounded text-[9px] font-sans font-bold bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 tracking-widest">
            神圣忠良
          </span>
        );
      case "EVIL":
        return (
          <span className="px-2 py-0.5 rounded text-[9px] font-sans font-bold bg-red-500/10 border border-red-500/20 text-red-400 tracking-widest">
            暗夜恶狼
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[9px] font-sans font-bold bg-zinc-800 border border-zinc-700 text-zinc-300 tracking-widest">
            中立阵营
          </span>
        );
    }
  };

  const getDifficultyColor = (diff: RoleSummary["difficulty"]) => {
    switch (diff) {
      case "EASY":
        return "text-emerald-400";
      case "MEDIUM":
        return "text-yellow-500";
      default:
        return "text-red-500 font-black";
    }
  };

  const difficultyLabel = (diff: RoleSummary["difficulty"]) => {
    switch (diff) {
      case "EASY":
        return "简易";
      case "HEAVY":
        return "艰深";
      default:
        return "中等";
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center text-zinc-400 font-sans text-xs tracking-widest gap-2">
        <div className="w-6 h-6 border-2 border-t-yellow-500 border-zinc-900 rounded-full animate-spin" />
        <span>翻阅远古圣史卷宗...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center text-center p-4 gap-4">
        <Skull className="w-10 h-10 text-red-500 animate-pulse" />
        <p className="text-zinc-400 font-sans text-xs tracking-wider">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-zinc-950 border border-zinc-800 hover:border-yellow-500 text-xs font-sans text-zinc-300 hover:text-white"
        >
          重新召唤
        </button>
      </div>
    );
  }

  if (roles.length === 0) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center text-center p-4">
        <p className="text-zinc-500 font-sans text-xs tracking-widest">圣殿空虚 · 暂无角色刻印</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-12 md:py-16 relative">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-4 mb-10 text-center"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-zinc-950 border border-zinc-900 rounded-full text-[9px] font-mono text-yellow-500 uppercase tracking-widest">
          <Sparkles className="w-3 h-3 text-yellow-500" />
          SACRED ALIGNMENT EPICS · {roles.length} ROLES
        </div>
        <h1 className="text-3xl md:text-4xl font-extrabold tracking-widest font-sans bg-clip-text bg-gradient-to-r from-zinc-100 to-yellow-600 inline-block text-transparent">
          {introTitle}
        </h1>
        <p className="text-xs text-zinc-400 max-w-2xl mx-auto leading-relaxed">{introText}</p>
        <div className="w-16 h-px bg-zinc-800 mx-auto" />
      </motion.div>

      <div className="flex flex-wrap items-center justify-center gap-2 mb-8">
        <Filter className="w-3.5 h-3.5 text-zinc-600" />
        {(Object.keys(CAMP_LABELS) as CampFilter[]).map((camp) => {
          const count =
            camp === "all"
              ? roles.length
              : campStats[camp] ??
                roles.filter((r) => {
                  if (camp === "werewolf") return r.alignment === "EVIL";
                  if (camp === "villager") return r.alignment === "GOOD";
                  return r.alignment === "NEUTRAL";
                }).length;
          const active = campFilter === camp;
          return (
            <button
              key={camp}
              type="button"
              onClick={() => setCampFilter(camp)}
              className={`px-3 py-1.5 rounded text-[10px] font-sans tracking-wider border transition-all ${
                active
                  ? "bg-yellow-500/10 border-yellow-500/40 text-yellow-400"
                  : "bg-zinc-950 border-zinc-800 text-zinc-500 hover:border-zinc-700 hover:text-zinc-300"
              }`}
            >
              {CAMP_LABELS[camp]} ({count})
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
        {filteredRoles.map((role) => (
          <Link
            key={role.key}
            to={`/roles/${role.key}`}
            className="group block bg-zinc-950 hover:bg-zinc-900/90 border border-zinc-900 hover:border-yellow-500/40 rounded-lg overflow-hidden transition-all text-left"
          >
            <div className="relative aspect-[3/4] overflow-hidden bg-zinc-900">
              <img
                src={getRoleImage(role.key)}
                alt={role.chineseName}
                className="w-full h-full object-cover object-top opacity-90 group-hover:opacity-100 group-hover:scale-105 transition-all duration-500"
                loading="lazy"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/20 to-transparent" />
              <div className="absolute top-2 right-2">{getAlignmentBadge(role.alignment)}</div>
              <div className="absolute bottom-0 left-0 right-0 p-3">
                <h3 className="text-sm font-black tracking-wider text-zinc-100 font-sans group-hover:text-yellow-500 transition-colors">
                  {role.chineseName}
                </h3>
                <p className="text-[9px] text-zinc-500 font-mono uppercase">{role.name}</p>
              </div>
            </div>

            <div className="p-4 space-y-3">
              <p className="text-[10px] text-yellow-600/80 font-serif italic line-clamp-1">
                「 {role.tagline} 」
              </p>
              <p className="text-[11px] text-zinc-400 line-clamp-2 leading-relaxed min-h-[2.5rem]">
                {role.shortDesc}
              </p>

              <div className="flex items-center gap-3 text-[9px] font-sans text-zinc-500">
                <span className="inline-flex items-center gap-1">
                  <BookOpen className="w-3 h-3 text-violet-400" />
                  提升词 {role.promptVersion ?? "v1"}
                  <span className="text-zinc-600">({role.promptCount ?? 0})</span>
                </span>
                <span className="inline-flex items-center gap-1">
                  <Scroll className="w-3 h-3 text-fuchsia-400" />
                  技能 {role.skillVersion ?? "v1"}
                  <span className="text-zinc-600">({role.skillCount ?? 0})</span>
                </span>
                <span className={`ml-auto ${getDifficultyColor(role.difficulty)}`}>
                  {difficultyLabel(role.difficulty)}
                </span>
              </div>

              <div className="pt-2 border-t border-zinc-900/50 flex justify-between items-center text-[9px] font-sans text-zinc-500 group-hover:text-zinc-300">
                <span>展开完整档案</span>
                <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
              </div>
            </div>
          </Link>
        ))}
      </div>

      {filteredRoles.length === 0 && (
        <div className="text-center py-16 text-zinc-500 font-sans text-xs tracking-widest flex flex-col items-center gap-2">
          <Users className="w-8 h-8 text-zinc-700" />
          该阵营暂无角色刻印
        </div>
      )}
    </div>
  );
}
