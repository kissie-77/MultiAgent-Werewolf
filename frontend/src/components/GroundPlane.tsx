import React, { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { sceneTheme, type SceneMode } from "../lib/sceneTheme";

/** 程序化石质地面贴图：暗石底 + 中心微亮的径向渐变 + 随机刻痕。 */
function makeGroundTexture(): THREE.CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = 1024;
  canvas.height = 1024;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.fillStyle = "#15131a";
    ctx.fillRect(0, 0, 1024, 1024);

    const grad = ctx.createRadialGradient(512, 512, 80, 512, 512, 512);
    grad.addColorStop(0, "rgba(70,64,86,0.9)");
    grad.addColorStop(0.6, "rgba(28,26,38,0.7)");
    grad.addColorStop(1, "rgba(8,7,12,1)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 1024, 1024);

    ctx.globalAlpha = 0.16;
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1;
    for (let i = 0; i < 120; i++) {
      const x = Math.random() * 1024;
      const y = Math.random() * 1024;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x + (Math.random() - 0.5) * 70, y + (Math.random() - 0.5) * 70);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }
  return new THREE.CanvasTexture(canvas);
}

const GROUND_TINT: Record<SceneMode, string> = {
  day: "#9a8f7a",
  night: "#1b1830",
  murder: "#2a1010",
};

export default function GroundPlane({ mode, tableRadius }: { mode: SceneMode; tableRadius: number }) {
  const theme = sceneTheme(mode);
  const texture = React.useMemo(() => makeGroundTexture(), []);

  const matRef = useRef<THREE.MeshStandardMaterial>(null);
  const ring0 = useRef<THREE.MeshBasicMaterial>(null);
  const ring1 = useRef<THREE.MeshBasicMaterial>(null);
  const ring2 = useRef<THREE.MeshBasicMaterial>(null);
  const ringRefs = [ring0, ring1, ring2];

  const targetGround = React.useMemo(() => new THREE.Color(GROUND_TINT[mode]), [mode]);
  const targetAccent = React.useMemo(() => new THREE.Color(theme.accent), [theme.accent]);

  useFrame((_, delta) => {
    const s = 1 - Math.exp(-3 * delta);
    if (matRef.current) matRef.current.color.lerp(targetGround, s);
    for (const r of ringRefs) if (r.current) r.current.color.lerp(targetAccent, s);
  });

  const ringRadii = [tableRadius * 1.4, tableRadius * 2.0, tableRadius * 2.8];

  return (
    <group position={[0, -0.5, 0]}>
      {/* 接收唯一方向光阴影的大地面 */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]} receiveShadow>
        <circleGeometry args={[tableRadius * 4.2, 96]} />
        <meshStandardMaterial ref={matRef} map={texture} roughness={0.95} metalness={0.1} />
      </mesh>

      {/* 同心发光法阵环（加色混合，不投影、不写深度） */}
      {ringRadii.map((r, i) => (
        <mesh key={i} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01 + i * 0.004, 0]}>
          <ringGeometry args={[r, r + 0.07, 128]} />
          <meshBasicMaterial
            ref={ringRefs[i]}
            transparent
            opacity={0.34 - i * 0.08}
            blending={THREE.AdditiveBlending}
            side={THREE.DoubleSide}
            depthWrite={false}
          />
        </mesh>
      ))}
    </group>
  );
}
