export interface MatrixScale {
  cell: number;
  font: number;
}

/** n = 总座位数（players.length）。分档缩小；最小格宽 17px，超限由调用方允许横滚。 */
export function matrixScale(n: number): MatrixScale {
  if (n <= 6) return { cell: 34, font: 10 };
  if (n <= 9) return { cell: 28, font: 9 };
  if (n <= 12) return { cell: 22, font: 8 };
  return { cell: 17, font: 7 };
}

/** 0.25 -> "25%"; 0.05 -> "5%"; 1 -> "100%"; 0.333 -> "33%" */
export function formatWolfProb(p: number): string {
  return `${Math.round(p * 100)}%`;
}

/** 连续热力色。p<=0.5: 深蓝->琥珀；p>0.5: 琥珀->暗红。从 BeliefMatrixPanel 抽出共用。 */
export function heatColor(p: number): string {
  if (p <= 0.5) {
    const ratio = p * 2;
    const r = Math.round(15 + ratio * (217 - 15));
    const g = Math.round(50 + ratio * (119 - 50));
    const b = Math.round(100 + ratio * (6 - 100));
    return `rgb(${r},${g},${b})`;
  }
  const ratio = (p - 0.5) * 2;
  const r = Math.round(217 + ratio * (153 - 217));
  const g = Math.round(119 + ratio * (27 - 119));
  const b = Math.round(6 + ratio * (27 - 6));
  return `rgb(${r},${g},${b})`;
}
