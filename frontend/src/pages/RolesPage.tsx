import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiClient } from "../api/client";
import { RoleSummary } from "../api/types";
import { Eye, Shield, Zap, Skull, Users, ArrowRight, Sparkles } from "lucide-react";
import { motion } from "motion/react";

export default function RolesPage() {
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [introTitle, setIntroTitle] = useState("");
  const [introText, setIntroText] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    ApiClient.getRolesPageData()
      .then((data) => {
        if (active) {
          setRoles(data.roles || []);
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

  const getRoleIcon = (key: string) => {
    switch (key) {
      case "seer":
        return <Eye className="w-5 h-5 text-yellow-500" />;
      case "witch":
        return <Shield className="w-5 h-5 text-fuchsia-400" />;
      case "hunter":
        return <Zap className="w-5 h-5 text-emerald-400" />;
      case "wolf":
        return <Skull className="w-5 h-5 text-red-500" />;
      default:
        return <Users className="w-5 h-5 text-zinc-400" />;
    }
  };

  const getAlignmentBadge = (align: "GOOD" | "EVIL" | "NEUTRAL") => {
    switch (align) {
      case "GOOD":
        return (
          <span className="px-2 py-0.5 rounded text-[9px] font-mono font-bold bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 uppercase tracking-widest">
            神圣忠良
          </span>
        );
      case "EVIL":
        return (
          <span className="px-2 py-0.5 rounded text-[9px] font-mono font-bold bg-red-500/10 border border-red-500/20 text-red-400 uppercase tracking-widest">
            暗夜恶狼
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[9px] font-mono font-bold bg-zinc-800 border border-zinc-700 text-zinc-300 uppercase tracking-widest">
            中立阵营
          </span>
        );
    }
  };

  const getDifficultyColor = (diff: "EASY" | "MEDIUM" | "HEAVY") => {
    switch (diff) {
      case "EASY":
        return "text-emerald-400";
      case "MEDIUM":
        return "text-yellow-500";
      default:
        return "text-red-500 font-black";
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center text-zinc-400 font-mono text-xs uppercase tracking-widest gap-2">
        <div className="w-6 h-6 border-2 border-t-yellow-500 border-zinc-900 rounded-full animate-spin" />
        <span>翻阅远古圣史卷宗...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center text-center p-4 gap-4">
        <Skull className="w-10 h-10 text-red-500 animate-pulse" />
        <p className="text-zinc-400 font-mono text-xs tracking-wider">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-zinc-950 border border-zinc-800 hover:border-yellow-500 text-xs font-mono text-zinc-300 hover:text-white"
        >
          重新召唤
        </button>
      </div>
    );
  }

  if (roles.length === 0) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center text-center p-4">
        <p className="text-zinc-500 font-mono text-xs uppercase tracking-widest">圣殿空虚 ∙ 暂无角色刻印</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-12 md:py-16 relative">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-4 mb-12 text-center"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-zinc-950 border border-zinc-900 rounded-full text-[9px] font-mono text-yellow-500 uppercase tracking-widest">
          <Sparkles className="w-3 h-3 text-yellow-500" />
          SACRED ALIGNMENT EPICS
        </div>
        <h1 className="text-3xl md:text-4xl font-extrabold uppercase tracking-widest font-sans bg-clip-text bg-gradient-to-r from-zinc-100 to-yellow-600 inline-block text-transparent">
          {introTitle}
        </h1>
        <p className="text-xs text-zinc-400 max-w-2xl mx-auto leading-relaxed">
          {introText}
        </p>
        <div className="w-16 h-px bg-zinc-800 mx-auto" />
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {roles.map((role) => (
          <Link
            key={role.key}
            to={`/roles/${role.key}`}
            className="group block bg-zinc-950 hover:bg-zinc-900/90 border border-zinc-900 hover:border-yellow-550/60 rounded-lg p-5 transition-all text-left relative overflow-hidden flex flex-col justify-between"
          >
            <div className="space-y-4">
              <div className="flex items-start justify-between">
                <div className="w-10 h-10 rounded bg-zinc-900 border border-zinc-800 flex items-center justify-center">
                  {getRoleIcon(role.key)}
                </div>
                <div className="flex flex-col items-end gap-1">
                  {getAlignmentBadge(role.alignment)}
                  <span className="text-[9px] font-mono text-zinc-500 uppercase">
                    上手难度:{" "}
                    <span className={getDifficultyColor(role.difficulty)}>
                      {role.difficulty}
                    </span>
                  </span>
                </div>
              </div>

              <div>
                <h3 className="text-base font-black tracking-widest text-zinc-100 font-sans group-hover:text-yellow-500 transition-colors">
                  {role.chineseName}{" "}
                  <span className="text-zinc-500 font-mono text-xs uppercase font-normal">
                    ({role.name})
                  </span>
                </h3>
                <p className="text-[10px] text-yellow-600/80 font-serif italic mt-0.5">
                  「 {role.tagline} 」
                </p>
                <p className="text-xs text-zinc-400 mt-2 line-clamp-2 leading-relaxed">
                  {role.shortDesc}
                </p>
              </div>
            </div>

            <div className="mt-5 pt-3 border-t border-zinc-900/50 flex justify-between items-center text-[10px] font-mono text-zinc-500 group-hover:text-zinc-300">
              <span className="uppercase">解封传记与作战诡计</span>
              <span className="flex items-center gap-0.5 font-bold">
                VIEW LORE
                <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
