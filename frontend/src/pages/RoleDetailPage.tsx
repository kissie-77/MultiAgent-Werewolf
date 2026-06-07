import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiClient } from "../api/client";
import { RoleDetail } from "../api/types";
import { Eye, Shield, Zap, Skull, Users, ArrowLeft, Scroll, BookOpen, Flame, Compass } from "lucide-react";
import { motion } from "motion/react";

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

  const getRoleIcon = (key?: string) => {
    switch (key) {
      case "seer":
        return <Eye className="w-8 h-8 text-yellow-500" />;
      case "witch":
        return <Shield className="w-8 h-8 text-fuchsia-400" />;
      case "hunter":
        return <Zap className="w-8 h-8 text-emerald-400" />;
      case "wolf":
        return <Skull className="w-8 h-8 text-red-500" />;
      default:
        return <Users className="w-8 h-8 text-zinc-400" />;
    }
  };

  const getAlignmentBadge = (align?: "GOOD" | "EVIL" | "NEUTRAL") => {
    switch (align) {
      case "GOOD":
        return (
          <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-yellow-500/10 border border-yellow-500/30 text-yellow-500 tracking-wider">
            ★ 神圣忠良阵营
          </span>
        );
      case "EVIL":
        return (
          <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-red-500/10 border border-red-500/30 text-red-500 tracking-wider">
            ★ 幽暗深渊恶狼
          </span>
        );
      default:
        return (
          <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-zinc-800 border border-zinc-700 text-zinc-300 tracking-wider">
            ★ 中立灵体
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
        return "bg-zinc-805/40 border-zinc-700 text-zinc-300";
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center text-zinc-400 font-mono text-xs uppercase tracking-widest gap-2">
        <div className="w-6 h-6 border-2 border-t-yellow-500 border-zinc-900 rounded-full animate-spin" />
        <span>翻研圣约典籍中...</span>
      </div>
    );
  }

  if (error || !role) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center text-center p-6 gap-6 relative">
        <div className="absolute inset-10 border border-red-500/10 pointer-events-none rounded" />
        <Skull className="w-14 h-14 text-red-500/80 animate-pulse" />
        <div className="space-y-1">
          <h2 className="text-lg font-bold font-sans uppercase tracking-widest text-zinc-200">卷宗已被黑夜吞噬</h2>
          <p className="text-zinc-500 font-sans text-xs max-w-sm">{error || "找不到该角色的古老事迹。"}</p>
        </div>
        <Link
          to="/roles"
          className="px-5 py-2.5 bg-zinc-950 border border-zinc-800 text-xs font-mono text-zinc-300 hover:border-yellow-500 hover:text-white rounded"
        >
          返回圣约主廊 (BACK)
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-12 md:py-16">
      {/* Return Navigation */}
      <div className="mb-8">
        <Link
          to="/roles"
          className="inline-flex items-center gap-2 text-xs font-mono tracking-widest uppercase text-zinc-400 hover:text-yellow-500 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          返回角色刻印主廊
        </Link>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-zinc-950/90 border border-zinc-900 rounded shadow-2xl overflow-hidden p-6 md:p-10 space-y-10"
      >
        {/* Title Deck */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-zinc-900 pb-8">
          <div className="flex items-center gap-5">
            <div className="w-14 h-14 rounded-lg bg-zinc-900 border-2 border-zinc-800 flex items-center justify-center shrink-0">
              {getRoleIcon(role.key)}
            </div>
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-2xl md:text-3xl font-black font-sans uppercase tracking-wider text-zinc-100">
                  {role.chineseName}
                </h1>
                <span className="text-zinc-600 font-mono text-sm uppercase">({role.name})</span>
              </div>
              <p className="text-xs text-yellow-600/90 font-serif italic mt-0.5">
                「 {role.tagline} 」
              </p>
            </div>
          </div>

          <div className="flex flex-col items-start md:items-end gap-1 shrink-0">
            {getAlignmentBadge(role.alignment)}
            <span className="text-[10px] font-mono text-zinc-500 mt-1 uppercase">
              宿命难度: <span className="text-zinc-200">{role.difficulty}</span>
            </span>
          </div>
        </div>

        {/* Double-Column Content Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Left Area (Lore, Strategy - 7 Cols) */}
          <div className="lg:col-span-7 space-y-8">
            
            {/* Backstory */}
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-zinc-300 border-b border-zinc-900 pb-1.5">
                <BookOpen className="w-4 h-4 text-yellow-500" />
                <h2 className="text-xs font-mono font-extrabold uppercase tracking-widest text-zinc-300">
                  传奇事迹 ∙ 灵魂碑文
                </h2>
              </div>
              <p className="text-xs text-zinc-400 leading-relaxed font-sans text-justify">
                {role.lore}
              </p>
            </div>

            {/* Winning Strategies */}
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-zinc-300 border-b border-zinc-900 pb-1.5">
                <Flame className="w-4 h-4 text-orange-400" />
                <h2 className="text-xs font-mono font-extrabold uppercase tracking-widest text-zinc-300">
                  智术韬略 ∙ 破局技巧
                </h2>
              </div>
              <ul className="space-y-2.5">
                {role.strategies.map((strat, i) => (
                  <li key={i} className="flex gap-2 text-xs text-zinc-400 leading-relaxed font-sans">
                    <span className="text-yellow-500 font-mono font-bold shrink-0">[{i+1}]</span>
                    <span>{strat}</span>
                  </li>
                ))}
              </ul>
            </div>

          </div>

          {/* Right Area (Skills, Relationships - 5 Cols) */}
          <div className="lg:col-span-5 space-y-8">
            
            {/* Actives/Skills */}
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-zinc-300 border-b border-zinc-900 pb-1.5">
                <Scroll className="w-4 h-4 text-fuchsia-400" />
                <h2 className="text-xs font-mono font-extrabold uppercase tracking-widest text-zinc-300">
                  权能指令
                </h2>
              </div>
              <div className="space-y-3">
                {role.skills.map((skill, i) => (
                  <div key={i} className="bg-zinc-900/40 border border-zinc-900 p-4 rounded flex flex-col gap-1.5">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-zinc-200">{skill.name}</h4>
                      <span className={`px-1.5 py-0.5 rounded text-[8px] font-mono border uppercase ${getTimingBadge(skill.timing)}`}>
                        {skill.timing === "NIGHT" ? "暗夜发动" : skill.timing === "DAY" ? "白昼论断" : "被动刻印"}
                      </span>
                    </div>
                    <p className="text-[11px] text-zinc-400 leading-relaxed">
                      {skill.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Relationships */}
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-zinc-300 border-b border-zinc-900 pb-1.5">
                <Compass className="w-4 h-4 text-emerald-400" />
                <h2 className="text-xs font-mono font-extrabold uppercase tracking-widest text-zinc-300">
                  审判合纵
                </h2>
              </div>
              <div className="space-y-3">
                {role.relationships.map((rel, i) => (
                  <div key={i} className="text-xs space-y-0.5">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-zinc-300 font-sans">{rel.targetRoleName}</span>
                      <span className={`text-[9px] font-mono tracking-widest ${
                        rel.type === "ALLIED" 
                          ? "text-emerald-400" 
                          : rel.type === "THREAT" 
                          ? "text-red-500 font-bold animate-pulse" 
                          : "text-zinc-500"
                      }`}>
                        {rel.type === "ALLIED" ? "純白同盟" : rel.type === "THREAT" ? "极危宿敌" : "中立羁绊"}
                      </span>
                    </div>
                    <p className="text-[11px] text-zinc-500 leading-relaxed font-sans">{rel.description}</p>
                  </div>
                ))}
              </div>
            </div>

          </div>

        </div>

        {/* Outer woodcut accent footer */}
        <div className="pt-6 border-t border-zinc-900/50 flex justify-between items-center text-[9px] font-mono text-zinc-650">
          <span>COSMIC TRIAL LORE v2.1</span>
          <span>ARCANUM DECK INSCRIBED</span>
        </div>
      </motion.div>
    </div>
  );
}
