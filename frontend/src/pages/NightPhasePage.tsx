import React, { useState, useEffect } from "react";
import { ApiClient } from "../api/client";
import { NightPhasePageData } from "../api/types";
import ContentPageLayout from "../components/ContentPageLayout";
import { motion } from "motion/react";
import { 
  Moon, 
  EyeOff, 
  Clock, 
  HelpCircle,
  Users,
  ShieldAlert,
  Loader2 
} from "lucide-react";

export default function NightPhasePage() {
  const [data, setData] = useState<NightPhasePageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    ApiClient.getNightPhasePageData()
      .then((res) => {
        if (active) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError("虚境网络受到暗流屏蔽，未寻获黑夜行纪规度。");
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center text-zinc-400">
        <Loader2 className="w-8 h-8 animate-spin text-yellow-500 mb-2" />
        <span className="font-sans text-xs text-zinc-400">召来深沉黑夜古书...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center text-center p-4">
        <p className="text-sm font-sans text-stone-500 mb-2">{error || "数据载入失败"}</p>
      </div>
    );
  }

  return (
    <ContentPageLayout
      title={data.title}
      subtitle={data.subtitle}
      description={data.description}
      sections={data.sections}
    >
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-8"
      >
        {/* 1. Sequential Steps of Night Actions */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-900 pb-2">
            <span className="font-serif text-xs font-black tracking-widest text-[#eae5db] uppercase flex items-center gap-2">
              <Moon className="w-4 h-4 text-violet-400" />
              黑夜运转行动次第 (SEQUENTIAL ACTIONS)
            </span>
            <span className="text-[10px] text-zinc-500 font-mono tracking-wider">3 CHRONO STEPS</span>
          </div>

          <div className="relative pl-6 border-l border-zinc-900 space-y-6">
            {data.steps.map((step) => (
              <div key={step.seq} className="relative group">
                {/* Node badge */}
                <div className="absolute -left-[30px] top-1.5 w-4 h-4 rounded-full border border-violet-700 bg-[#07050d] text-violet-400 flex items-center justify-center text-[9px] font-mono font-black">
                  {step.seq}
                </div>

                <div className="bg-zinc-950/60 border border-zinc-900 rounded p-4 group-hover:border-zinc-805 transition-all">
                  <h4 className="font-serif text-sm font-bold text-[#eae5db] mb-1.5">
                    {step.title}
                  </h4>
                  <p className="text-xs text-zinc-400 font-sans leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 2. Grid split: Active roles & Blind rules */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Active Roles in the darkness */}
          <div className="space-y-4">
            <h4 className="font-serif text-xs font-black text-zinc-300 tracking-wider flex items-center gap-1.5">
              <Users className="w-4 h-4 text-zinc-500" />
              深夜醒转角色 (INVOLVED AWAKENERS)
            </h4>

            <div className="space-y-3">
              {data.involved_roles.map((val, idx) => (
                <div key={idx} className="bg-zinc-950/60 border border-zinc-900 rounded p-3 text-xs">
                  <span className="font-serif font-bold text-yellow-500 block mb-1">
                    {val.name}
                  </span>
                  <p className="text-zinc-400 font-sans leading-relaxed">
                    {val.action_description}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Blind / black box privacy rules */}
          <div className="space-y-4">
            <h4 className="font-serif text-xs font-black text-zinc-300 tracking-wider flex items-center gap-1.5">
              <EyeOff className="w-4 h-4 text-zinc-500" />
              黑盒蔽天规则 (VISIBILITY & DATA RULES)
            </h4>

            <div className="space-y-3">
              {data.visibility_rules.map((rule, idx) => (
                <div key={idx} className="bg-zinc-950/60 border border-zinc-900 rounded p-3 text-xs relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-8 h-8 opacity-5 text-stone-300 font-bold font-serif pointer-events-none">
                    §
                  </div>
                  <span className="font-serif font-black text-[#eae5db] block mb-1">
                    {rule.title}
                  </span>
                  <p className="text-zinc-400 font-sans leading-relaxed">
                    {rule.rule}
                  </p>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* 3. Operational timeout and compute anomalies */}
        <div className="bg-zinc-950/40 border border-zinc-900 rounded p-5 space-y-3">
          <span className="font-serif text-[10px] tracking-widest text-[#eae5db]/60 font-bold block uppercase pb-1.5 border-b border-zinc-900 flex items-center gap-1.5">
            <Clock className="w-4 h-4 text-yellow-600 animate-pulse" />
            黑夜延迟上限与算力波动 (TIMEOUTS & COMPUTING STABILITY)
          </span>

          <ul className="space-y-2">
            {data.timeout_hints.map((hint, idx) => (
              <li key={idx} className="flex gap-2 text-xs text-zinc-400 leading-normal font-sans">
                <span className="text-violet-500 font-bold">•</span>
                <span>{hint}</span>
              </li>
            ))}
          </ul>
        </div>
      </motion.div>
    </ContentPageLayout>
  );
}
