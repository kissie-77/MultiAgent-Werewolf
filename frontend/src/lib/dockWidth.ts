export const DOCK_MIN_WIDTH = 300;
export const DOCK_MAX_WIDTH = 720;

/** 夹取面板宽度：下限 300，上限 min(720, 视口 90%)。极窄视口下仍保证 ≥ 300。 */
export function clampDockWidth(raw: number, viewportWidth: number): number {
  const upper = Math.min(DOCK_MAX_WIDTH, Math.floor(viewportWidth * 0.9));
  const hi = Math.max(DOCK_MIN_WIDTH, upper);
  return Math.round(Math.max(DOCK_MIN_WIDTH, Math.min(hi, raw)));
}
