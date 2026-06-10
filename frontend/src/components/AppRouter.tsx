import React from "react";
import { BrowserRouter, Routes, Route, Navigate, Link } from "react-router-dom";
import AppLayout from "./AppLayout";
import ErrorBoundary from "./ErrorBoundary";
import GlobalAudioController from "./GlobalAudioController";

const GameApp = React.lazy(() => import("../pages/GameApp"));
const HomePage = React.lazy(() => import("../pages/HomePage"));
const RolesPage = React.lazy(() => import("../pages/RolesPage"));
const RoleDetailPage = React.lazy(() => import("../pages/RoleDetailPage"));
const ModelsPage = React.lazy(() => import("../pages/ModelsPage"));
const ModelDetailPage = React.lazy(() => import("../pages/ModelDetailPage"));
const ModelComparePage = React.lazy(() => import("../pages/ModelComparePage"));
const ModelOverallPage = React.lazy(() => import("../pages/ModelOverallPage"));
const ReplayPage = React.lazy(() => import("../pages/ReplayPage"));
const SharePage = React.lazy(() => import("../pages/SharePage"));
const AboutPage = React.lazy(() => import("../pages/AboutPage"));
const FeaturesPage = React.lazy(() => import("../pages/FeaturesPage"));
const HowToPlayPage = React.lazy(() => import("../pages/HowToPlayPage"));
const NightPhasePage = React.lazy(() => import("../pages/NightPhasePage"));
const StrategyPage = React.lazy(() => import("../pages/StrategyPage"));
const RunsPage = React.lazy(() => import("../pages/RunsPage"));

const PageLoader = () => (
  <div className="min-h-screen bg-[#0d0907] flex flex-col items-center justify-center text-zinc-400 font-mono text-xs uppercase tracking-widest gap-2">
    <div className="w-6 h-6 border-2 border-t-amber-500 border-zinc-800 rounded-full animate-spin" />
    <span>Loading...</span>
  </div>
);

const gameErrorFallback = (
  <div className="min-h-screen bg-[#0d0907] flex flex-col items-center justify-center gap-4 text-zinc-200 text-center px-6">
    <span className="text-2xl font-black tracking-widest">对局界面渲染异常</span>
    <span className="font-sans text-xs text-zinc-500">已安全兜底，未白屏。</span>
    <div className="flex gap-3">
      <button onClick={() => window.location.reload()} className="px-4 py-2 bg-zinc-800 border border-zinc-700 rounded text-xs hover:border-zinc-500">重新加载</button>
      <Link to="/home" className="px-4 py-2 bg-blue-900/30 border border-blue-700/50 rounded text-xs text-blue-200 hover:border-blue-400">回到主界面</Link>
    </div>
  </div>
);

function LazyRoute({ children }: { children: React.ReactNode }) {
  return <React.Suspense fallback={<PageLoader />}>{children}</React.Suspense>;
}

export default function AppRouter() {
  return (
    <BrowserRouter>
      <GlobalAudioController />
      <Routes>
        <Route path="/" element={
          <LazyRoute>
            <ErrorBoundary label="GameApp" fallback={gameErrorFallback}>
              <GameApp />
            </ErrorBoundary>
          </LazyRoute>
        } />
        <Route path="/game" element={
          <LazyRoute>
            <ErrorBoundary label="GameApp" fallback={gameErrorFallback}>
              <GameApp />
            </ErrorBoundary>
          </LazyRoute>
        } />

        <Route path="/roles" element={<LazyRoute><AppLayout><RolesPage /></AppLayout></LazyRoute>} />
        <Route path="/roles/:roleKey" element={<LazyRoute><AppLayout><RoleDetailPage /></AppLayout></LazyRoute>} />

        <Route path="/models" element={<LazyRoute><AppLayout><ModelsPage /></AppLayout></LazyRoute>} />
        <Route path="/models/compare" element={<LazyRoute><AppLayout><ModelComparePage /></AppLayout></LazyRoute>} />
        <Route path="/models/overall" element={<LazyRoute><AppLayout><ModelOverallPage /></AppLayout></LazyRoute>} />
        <Route path="/models/:modelId" element={<LazyRoute><AppLayout><ModelDetailPage /></AppLayout></LazyRoute>} />

        <Route path="/replay/:runId" element={<LazyRoute><AppLayout><ReplayPage /></AppLayout></LazyRoute>} />
        <Route path="/share/:runId" element={<LazyRoute><AppLayout><SharePage /></AppLayout></LazyRoute>} />

        <Route path="/home" element={<LazyRoute><AppLayout><HomePage /></AppLayout></LazyRoute>} />
        <Route path="/rules" element={<LazyRoute><AppLayout><HowToPlayPage /></AppLayout></LazyRoute>} />
        <Route path="/how-to-play" element={<LazyRoute><AppLayout><HowToPlayPage /></AppLayout></LazyRoute>} />
        <Route path="/features" element={<LazyRoute><AppLayout><FeaturesPage /></AppLayout></LazyRoute>} />
        <Route path="/night-phase" element={<LazyRoute><AppLayout><NightPhasePage /></AppLayout></LazyRoute>} />
        <Route path="/strategy" element={<LazyRoute><AppLayout><StrategyPage /></AppLayout></LazyRoute>} />
        <Route path="/runs" element={<LazyRoute><AppLayout><RunsPage /></AppLayout></LazyRoute>} />
        <Route path="/about" element={<LazyRoute><AppLayout><AboutPage /></AppLayout></LazyRoute>} />

        <Route path="*" element={<Navigate to="/home" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
