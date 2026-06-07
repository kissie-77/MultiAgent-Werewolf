import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "./AppLayout";
import ErrorBoundary from "./ErrorBoundary";
import HomePage from "../pages/HomePage";
import GameApp from "../pages/GameApp";

// 全屏回退组件，防止 GameApp 渲染崩溃（例如损坏的游戏状态）
// 显示可恢复界面而非白屏
const gameErrorFallback = (
  <div className="min-h-screen bg-[#0d0907] flex flex-col items-center justify-center gap-4 text-zinc-200 text-center px-6">
    <span className="text-2xl font-black tracking-widest">对局界面渲染异常</span>
    <span className="font-sans text-xs text-zinc-500">已安全兜底，未白屏。</span>
    <div className="flex gap-3">
      <button onClick={() => window.location.reload()} className="px-4 py-2 bg-zinc-800 border border-zinc-700 rounded text-xs hover:border-zinc-500">重新加载</button>
      <a href="/home" className="px-4 py-2 bg-blue-900/30 border border-blue-700/50 rounded text-xs text-blue-200 hover:border-blue-400">回到主界面</a>
    </div>
  </div>
);
import NotImplementedPage from "./NotImplementedPage";
import RolesPage from "../pages/RolesPage";
import RoleDetailPage from "../pages/RoleDetailPage";
import ModelsPage from "../pages/ModelsPage";
import ModelDetailPage from "../pages/ModelDetailPage";
import ModelComparePage from "../pages/ModelComparePage";
import ReplayPage from "../pages/ReplayPage";
import SharePage from "../pages/SharePage";
import AboutPage from "../pages/AboutPage";
import FeaturesPage from "../pages/FeaturesPage";
import HowToPlayPage from "../pages/HowToPlayPage";
import NightPhasePage from "../pages/NightPhasePage";
import StrategyPage from "../pages/StrategyPage";
import RunsPage from "../pages/RunsPage";

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Full screen gameplay route doesn't use standard AppLayout navigation */}
        <Route path="/" element={<ErrorBoundary label="GameApp" fallback={gameErrorFallback}><GameApp /></ErrorBoundary>} />
        {/* /game renders GameApp directly (NOT a redirect) so ?run_id= survives —
            the backend's start_game returns game_page_path="/game?run_id=..." */}
        <Route path="/game" element={<ErrorBoundary label="GameApp" fallback={gameErrorFallback}><GameApp /></ErrorBoundary>} />

        {/* Roles pages wrapped inside standard interactive AppLayout */}
        <Route
          path="/roles"
          element={
            <AppLayout>
              <RolesPage />
            </AppLayout>
          }
        />
        <Route
          path="/roles/:roleKey"
          element={
            <AppLayout>
              <RoleDetailPage />
            </AppLayout>
          }
        />

        {/* Models pages wrapped inside standard interactive AppLayout */}
        <Route
          path="/models"
          element={
            <AppLayout>
              <ModelsPage />
            </AppLayout>
          }
        />
        <Route
          path="/models/compare"
          element={
            <AppLayout>
              <ModelComparePage />
            </AppLayout>
          }
        />
        <Route
          path="/models/:modelId"
          element={
            <AppLayout>
              <ModelDetailPage />
            </AppLayout>
          }
        />

        {/* Replay related pages wrapped inside standard interactive AppLayout */}
        <Route
          path="/replay/:runId"
          element={
            <AppLayout>
              <ReplayPage />
            </AppLayout>
          }
        />
        <Route
          path="/share/:runId"
          element={
            <AppLayout>
              <SharePage />
            </AppLayout>
          }
        />

        {/* Other routes wrapped inside standard interactive AppLayout */}
        <Route
          path="/home"
          element={
            <AppLayout>
              <HomePage />
            </AppLayout>
          }
        />

        <Route
          path="/rules"
          element={
            <AppLayout>
              <HowToPlayPage />
            </AppLayout>
          }
        />

        <Route
          path="/how-to-play"
          element={
            <AppLayout>
              <HowToPlayPage />
            </AppLayout>
          }
        />

        <Route
          path="/features"
          element={
            <AppLayout>
              <FeaturesPage />
            </AppLayout>
          }
        />

        <Route
          path="/night-phase"
          element={
            <AppLayout>
              <NightPhasePage />
            </AppLayout>
          }
        />

        <Route
          path="/strategy"
          element={
            <AppLayout>
              <StrategyPage />
            </AppLayout>
          }
        />

        <Route
          path="/runs"
          element={
            <AppLayout>
              <RunsPage />
            </AppLayout>
          }
        />

        <Route
          path="/about"
          element={
            <AppLayout>
              <AboutPage />
            </AppLayout>
          }
        />

        {/* Fallback redirecting back to home page */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
