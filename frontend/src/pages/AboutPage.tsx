import React, { useEffect, useState, useCallback } from "react";
import { ApiClient } from "../api/client";
import { AboutPageData } from "../api/types";
import ProjectPresentation from "../components/about/ProjectPresentation";
import PageLoadState from "../components/PageLoadState";
import { Link } from "react-router-dom";

export default function AboutPage() {
  const [meta, setMeta] = useState<AboutPageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    ApiClient.getAboutPageData()
      .then((res) => {
        if (cancelled) return;
        setMeta(res);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error(err);
        setError("项目介绍加载失败，请稍后重试。");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const retryFetch = useCallback(() => {
    setLoading(true);
    setError(null);
    ApiClient.getAboutPageData()
      .then((res) => {
        setMeta(res);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setError("项目介绍加载失败，请稍后重试。");
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <PageLoadState variant="loading" loadingText="加载项目介绍..." />;
  }

  if (error) {
    return (
      <PageLoadState
        variant="error"
        errorText={error}
        onRetry={retryFetch}
        action={
          <Link
            to="/"
            className="px-5 py-2.5 bg-zinc-900 border border-zinc-800 hover:border-yellow-500 hover:text-yellow-500 text-xs font-mono tracking-widest text-zinc-300 rounded transition-colors"
          >
            返回首页
          </Link>
        }
      />
    );
  }

  return (
    <ProjectPresentation
      roleCount={meta?.roleCount}
      configCount={meta?.configCount}
    />
  );
}
