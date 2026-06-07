import React, { useEffect, useState } from "react";
import { ApiClient } from "../api/client";
import { AboutPageData } from "../api/types";
import ProjectPresentation from "../components/about/ProjectPresentation";
import { Loader2 } from "lucide-react";

export default function AboutPage() {
  const [meta, setMeta] = useState<AboutPageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    ApiClient.getAboutPageData()
      .then((res) => {
        if (active) {
          setMeta(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          console.error(err);
          setError("项目介绍加载失败，请稍后重试。");
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
        <span className="font-mono text-xs tracking-widest uppercase">加载项目介绍...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center text-center p-4">
        <p className="text-sm font-mono text-stone-500 tracking-wider">{error}</p>
      </div>
    );
  }

  return (
    <ProjectPresentation
      roleCount={meta?.roleCount}
      configCount={meta?.configCount}
    />
  );
}
