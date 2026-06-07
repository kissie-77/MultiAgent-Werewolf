import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "./AppLayout";
import HomePage from "../pages/HomePage";
import GameApp from "../pages/GameApp";
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
        <Route path="/" element={<GameApp />} />
        {/* /game renders GameApp directly (NOT a redirect) so ?run_id= survives —
            the backend's start_game returns game_page_path="/game?run_id=..." */}
        <Route path="/game" element={<GameApp />} />

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
