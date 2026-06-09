export type SceneMode = "day" | "night" | "murder";

export interface SceneTheme {
  /** Scene background + fog color. */
  bg: string;
  /** Ambient (global fill) light. */
  ambientColor: string;
  ambientIntensity: number;
  /** Key directional light (sun / moon). */
  dirColor: string;
  dirIntensity: number;
  dirPos: [number, number, number];
  /** Primary accent — rims, beams, sigil strokes, ground rings. */
  accent: string;
  /** Soft secondary accent — gems, halos, inner glow. */
  accentSoft: string;
}

/** Murder alert overrides night, which overrides day. */
export function resolveSceneMode(isNight: boolean, isMurderAlert: boolean): SceneMode {
  if (isMurderAlert) return "murder";
  return isNight ? "night" : "day";
}

const THEMES: Record<SceneMode, SceneTheme> = {
  // 明亮暖阳 + 淡蓝天光：环境光从旧的 0.38 拉到 1.2，背景换成淡蓝天色。
  day: {
    bg: "#bcd4e6",
    ambientColor: "#fff4e0",
    ambientIntensity: 1.2,
    dirColor: "#ffe9b0",
    dirIntensity: 6.0,
    dirPos: [12, 18, 8],
    accent: "#f59e0b",
    accentSoft: "#fde047",
  },
  // 深蓝紫夜色 + 冷月光：从旧的暗紫 0.15 提到 0.4，能看清但仍暗，冷色调。
  night: {
    bg: "#0a0e2a",
    ambientColor: "#6a7cb8",
    ambientIntensity: 0.4,
    dirColor: "#aac4ff",
    dirIntensity: 2.0,
    dirPos: [-10, 16, -6],
    accent: "#6366f1",
    accentSoft: "#a5b4fc",
  },
  // 命案警报：保留刺目的赤红档不动。
  murder: {
    bg: "#2a0404",
    ambientColor: "#ff1100",
    ambientIntensity: 0.8,
    dirColor: "#dc2626",
    dirIntensity: 4.5,
    dirPos: [10, 15, 5],
    accent: "#ef4444",
    accentSoft: "#fca5a5",
  },
};

export function sceneTheme(mode: SceneMode): SceneTheme {
  return THEMES[mode];
}
