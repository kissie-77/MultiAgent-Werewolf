import React, { useState, useEffect } from "react";
import { ApiClient } from "../api/client";
import { FeaturesPageData } from "../api/types";
import ContentPageLayout from "../components/ContentPageLayout";
import { motion } from "motion/react";
import { 
  Eye, 
  Grid, 
  TrendingUp, 
  BrainCircuit, 
  Layers,
  Loader2 
} from "lucide-react";

const itemIconMap: { [key: string]: any } = {
  Eye: Eye,
  Grid: Grid,
  TrendingUp: TrendingUp,
  BrainCircuit: BrainCircuit
};

export default function FeaturesPage() {
  const [data, setData] = useState<FeaturesPageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    ApiClient.getFeaturesPageData()
      .then((res) => {
        if (active) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          console.error(err);
          setError("虚空网络拥塞，无法检索高级对决特性之页。");
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
        <span className="font-mono text-xs tracking-widest uppercase">重铸法典碑谱特性页...</span>
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
        <div className="flex items-center justify-between border-b border-zinc-900 pb-2 mb-4">
          <span className="font-serif text-xs font-black tracking-widest text-[#eae5db] uppercase block">
            虚境四大神兵工具 (TACTICAL COMPASS)
          </span>
          <span className="text-[10px] text-zinc-500 font-mono tracking-wider">4 CORE MODULES</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.feature_cards.map((card, index) => {
            const IconComponent = itemIconMap[card.icon] || Layers;

            return (
              <div 
                key={index}
                className="bg-zinc-950/90 border border-zinc-900 hover:border-zinc-800 p-6 rounded relative overflow-hidden group transition-all"
              >
                {/* Visual woodcut-inspired grid corner decorations */}
                <div className="absolute top-0 right-0 w-8 h-8 border-r border-t border-zinc-800/60 pointer-events-none" />
                <div className="absolute bottom-0 left-0 w-8 h-8 border-l border-b border-zinc-800/60 pointer-events-none" />

                <div className="flex items-start justify-between gap-4 mb-4">
                  <div className="w-10 h-10 rounded bg-[#eae5db]/5 border border-[#eae5db]/10 flex items-center justify-center text-yellow-500 group-hover:scale-110 transition-transform">
                    <IconComponent className="w-5 h-5 text-yellow-500" />
                  </div>
                  {card.badge && (
                    <span className="px-2 py-0.5 text-[8px] font-mono tracking-widest bg-yellow-500 text-zinc-950 font-black rounded uppercase">
                      {card.badge}
                    </span>
                  )}
                </div>

                <h3 className="font-serif text-sm font-black text-zinc-200 tracking-wider mb-2">
                  {card.title}
                </h3>
                
                <p className="text-xs text-zinc-400 font-sans leading-relaxed mb-4">
                  {card.description}
                </p>

                {card.value_stat && (
                  <div className="pt-3 border-t border-zinc-905 w-full flex justify-between items-center text-[10px] font-mono">
                    <span className="text-zinc-600 uppercase">当前参数标准 (SPEC)</span>
                    <span className="text-yellow-500 font-bold">{card.value_stat}</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </motion.div>
    </ContentPageLayout>
  );
}
