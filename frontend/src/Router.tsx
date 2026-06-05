import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import SpectateApp from "./App";
import FeaturesPage from "./pages/FeaturesPage";
import AboutPage from "./pages/AboutPage";
import HowToPlayPage from "./pages/HowToPlayPage";
import StrategyPage from "./pages/StrategyPage";
import RolesPage from "./pages/RolesPage";
import PlaceholderPage from "./pages/PlaceholderPage";

export default function Router() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/game" element={<SpectateApp />} />
        <Route path="/features" element={<FeaturesPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/how-to-play" element={<HowToPlayPage />} />
        <Route path="/strategy" element={<StrategyPage />} />
        <Route path="/roles" element={<RolesPage />} />
        <Route path="/models" element={<PlaceholderPage title="模型竞技场" eyebrow="模型" />} />
        <Route path="/replay/:runId" element={<PlaceholderPage title="复盘" eyebrow="replay" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
