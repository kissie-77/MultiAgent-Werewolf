import React, { useState, useEffect } from "react";
import { ApiClient } from "../api/client";
import { AboutPageData } from "../api/types";
import ContentPageLayout from "../components/ContentPageLayout";
import { motion } from "motion/react";
import { Lightbulb, Fingerprint, Award, Loader2 } from "lucide-react";

export default function AboutPage() {
  const [data, setData] = useState<AboutPageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    ApiClient.getAboutPageData()
      .then((res) => {
        if (active) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          console.error(err);
          setError("虚空回响低迷，无法载入关于虚境之页。");
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
        <span className="font-mono text-xs tracking-widest uppercase">重雕大碑刻印关于页...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center text-center p-4">
        <p className="text-sm font-mono text-stone-500 tracking-wider mb-2">{error || "数据载入失败"}</p>
      </div>
    );
  }

  const decorativeIcons = [Lightbulb, Fingerprint, Award];

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
        className="space-y-6"
      >
        <span className="font-serif text-xs font-black tracking-widest text-[#eae5db] uppercase border-b border-zinc-900 pb-2 mb-4 block">
          虚境最高实验准则 (DESIGN PRINCIPLES)
        </span>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {data.design_principles.map((principle, index) => {
            const Icon = decorativeIcons[index % decorativeIcons.length];
            const parts = principle.split("：");
            const head = parts[0];
            const body = parts[1] || "";

            return (
              <div 
                key={index}
                className="bg-zinc-950/40 border border-zinc-900/60 p-5 rounded hover:border-zinc-800 transition-all group relative overflow-hidden"
              >
                <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-tr from-transparent via-yellow-500/5 to-transparent rotate-45" />
                <div className="w-8 h-8 rounded bg-yellow-500/5 border border-yellow-500/10 flex items-center justify-center text-yellow-500 mb-3 group-hover:scale-110 transition-transform">
                  <Icon className="w-4 h-4" />
                </div>
                <h4 className="font-serif text-sm font-black text-yellow-500 tracking-wider mb-1">
                  {head}
                </h4>
                <p className="text-[11px] text-zinc-400 font-sans leading-relaxed">
                  {body}
                </p>
              </div>
            );
          })}
        </div>
      </motion.div>
    </ContentPageLayout>
  );
}
