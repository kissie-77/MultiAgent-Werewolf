import React, { useRef, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import * as THREE from "three";
import { useReducedMotion } from "motion/react";
import { useGameStore } from "../store";
import { ESTABLISH_MS, isLobbyPhase } from "../lib/phaseStage";
import { decideCamera, RECENTER_HOLD_MS } from "../lib/cameraDirector";
import { buildPreviewSeats } from "../lib/previewSeats";
import { resolveSceneMode, sceneTheme, type SceneMode } from "../lib/sceneTheme";
import type { GameState } from "../types";

function EnvironmentController({ mode }: { mode: SceneMode }) {
  const { scene } = useThree();

  const theme = React.useMemo(() => {
    const t = sceneTheme(mode);
    return {
      bg: new THREE.Color(t.bg),
      ambientColor: new THREE.Color(t.ambientColor),
      ambientIntensity: t.ambientIntensity,
      dirColor: new THREE.Color(t.dirColor),
      dirPos: new THREE.Vector3(t.dirPos[0], t.dirPos[1], t.dirPos[2]),
      dirIntensity: t.dirIntensity,
    };
  }, [mode]);

  const ambientRef = useRef<THREE.AmbientLight>(null);
  const dirRef = useRef<THREE.DirectionalLight>(null);

  useEffect(() => {
    scene.fog = new THREE.Fog(theme.bg, 12, 38);
    scene.background = theme.bg.clone();
    return () => {
      scene.fog = null;
      scene.background = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene]);

  useFrame((_, delta) => {
    const s = 1 - Math.exp(-3 * delta); // 帧率无关的平滑衰减

    if (scene.background instanceof THREE.Color) {
      scene.background.lerp(theme.bg, s);
    }
    if (scene.fog && "color" in scene.fog) {
      (scene.fog as THREE.Fog).color.lerp(theme.bg, s);
    }
    if (ambientRef.current) {
      ambientRef.current.color.lerp(theme.ambientColor, s);
      ambientRef.current.intensity = THREE.MathUtils.lerp(ambientRef.current.intensity, theme.ambientIntensity, s);
    }
    if (dirRef.current) {
      dirRef.current.color.lerp(theme.dirColor, s);
      dirRef.current.intensity = THREE.MathUtils.lerp(dirRef.current.intensity, theme.dirIntensity, s);
      dirRef.current.position.lerp(theme.dirPos, s);
    }
  });

  return (
    <>
      <ambientLight ref={ambientRef} />
      <directionalLight
        ref={dirRef}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
        shadow-bias={-0.0004}
        shadow-camera-near={1}
        shadow-camera-far={60}
        shadow-camera-left={-24}
        shadow-camera-right={24}
        shadow-camera-top={24}
        shadow-camera-bottom={-24}
      />
    </>
  );
}
function CameraTracker() {
  const { camera } = useThree();
  const gameState = useGameStore((state) => state.state);
  const setupCount = useGameStore((state) => state.setupCount);
  const currentSpeakerId = gameState?.currentSpeakerId ?? null;
  const players = gameState?.players || [];
  const phase = gameState?.phase;
  const reducedMotion = useReducedMotion() ?? false;

  // Damp targets (seeded at the unified home framing for a 6-seat table).
  const targetCamPos = useRef(new THREE.Vector3(0, 9.25, 13));
  const targetLookAt = useRef(new THREE.Vector3(0, 0.4, 0));
  const currentLookAt = useRef(new THREE.Vector3(0, 0.4, 0));

  // "Wide window" timers (performance.now() deadlines; 0 = inactive).
  const establishUntilRef = useRef<number>(0);
  const recenterUntilRef = useRef<number>(0);
  const prevPhaseRef = useRef<GameState["phase"] | undefined>(phase);
  const prevSpeakerRef = useRef<number | null>(currentSpeakerId);

  // Any in-game phase change (coarse day/night OR a sub-phase like vote/sheriff/
  // night-skill) opens a wide "establish" beat. Lobby is excluded (it orbits).
  useEffect(() => {
    const prev = prevPhaseRef.current;
    if (phase && phase !== prev && phase !== "START_SCREEN") {
      establishUntilRef.current = performance.now() + ESTABLISH_MS;
    }
    prevPhaseRef.current = phase;
  }, [phase]);

  // A speech ending (speaker moving away from a previous speaker) opens a wide
  // "hold" beat that deliberately survives into the next speaker's first moments.
  useEffect(() => {
    const prev = prevSpeakerRef.current;
    if (prev != null && currentSpeakerId !== prev) {
      recenterUntilRef.current = performance.now() + RECENTER_HOLD_MS;
    }
    prevSpeakerRef.current = currentSpeakerId;
  }, [currentSpeakerId]);

  useFrame((state, delta) => {
    // Lobby keeps its bespoke slow-orbit framing, untouched.
    // (undefined phase = pre-connect landing page, also lobby — see isLobbyPhase.)
    if (isLobbyPhase(phase)) {
      const time = state.clock.getElapsedTime();
      const orbitSpeed = 0.08;
      const pCount = setupCount !== null ? setupCount : (players.length || 6);
      const radius = Math.max(5, pCount * 0.72);
      const orbitRadius = radius * 3.4; // majestic outer distance

      const x = Math.sin(time * orbitSpeed) * orbitRadius;
      const z = Math.cos(time * orbitSpeed) * orbitRadius;
      targetCamPos.current.set(x, radius * 1.6, z);

      // Offset the look target so the round table sits to the screen's right.
      const dirVec = new THREE.Vector3()
        .subVectors(new THREE.Vector3(0, 0.4, 0), targetCamPos.current)
        .normalize();
      const upVec = new THREE.Vector3(0, 1, 0);
      const rightVec = new THREE.Vector3().crossVectors(dirVec, upVec).normalize();
      let offsetScale = 0;
      if (typeof window !== "undefined" && window.innerWidth > window.innerHeight) {
        offsetScale = radius * 0.8;
      }
      const lookTarget = new THREE.Vector3(0, 0.4, 0).add(rightVec.multiplyScalar(-offsetScale));
      targetLookAt.current.copy(lookTarget);

      camera.position.x = THREE.MathUtils.damp(camera.position.x, targetCamPos.current.x, 3.5, delta);
      camera.position.y = THREE.MathUtils.damp(camera.position.y, targetCamPos.current.y, 3.5, delta);
      camera.position.z = THREE.MathUtils.damp(camera.position.z, targetCamPos.current.z, 3.5, delta);
      currentLookAt.current.x = THREE.MathUtils.damp(currentLookAt.current.x, targetLookAt.current.x, 4.0, delta);
      currentLookAt.current.y = THREE.MathUtils.damp(currentLookAt.current.y, targetLookAt.current.y, 4.0, delta);
      currentLookAt.current.z = THREE.MathUtils.damp(currentLookAt.current.z, targetLookAt.current.z, 4.0, delta);
      camera.lookAt(currentLookAt.current);
      return;
    }

    const count = players.length > 0 ? players.length : (setupCount ?? 6);
    const speakerIndex =
      currentSpeakerId != null ? players.findIndex((p) => p.id === currentSpeakerId) : -1;

    const decision = decideCamera({
      phase,
      speakerIndex: speakerIndex >= 0 ? speakerIndex : null,
      count,
      nowMs: performance.now(),
      establishUntilMs: establishUntilRef.current,
      recenterUntilMs: recenterUntilRef.current,
      reducedMotion,
    });

    targetCamPos.current.set(decision.pos[0], decision.pos[1], decision.pos[2]);
    targetLookAt.current.set(decision.look[0], decision.look[1], decision.look[2]);

    camera.position.x = THREE.MathUtils.damp(camera.position.x, targetCamPos.current.x, decision.posLambda, delta);
    camera.position.y = THREE.MathUtils.damp(camera.position.y, targetCamPos.current.y, decision.posLambda, delta);
    camera.position.z = THREE.MathUtils.damp(camera.position.z, targetCamPos.current.z, decision.posLambda, delta);

    currentLookAt.current.x = THREE.MathUtils.damp(currentLookAt.current.x, targetLookAt.current.x, decision.lookLambda, delta);
    currentLookAt.current.y = THREE.MathUtils.damp(currentLookAt.current.y, targetLookAt.current.y, decision.lookLambda, delta);
    currentLookAt.current.z = THREE.MathUtils.damp(currentLookAt.current.z, targetLookAt.current.z, decision.lookLambda, delta);
    camera.lookAt(currentLookAt.current);
  });

  return null;
}

// 审判法阵的程序化纹理
interface TrialSigilProps {
  tableRadius: number;
  isNight: boolean;
  isMurderAlert?: boolean;
}

function TrialSigil({ tableRadius, isNight, isMurderAlert }: TrialSigilProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const textureRef = useRef<THREE.CanvasTexture | null>(null);

  useEffect(() => {
    // 在 512x512 画布上绘制木刻魔法阵
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      // 暗黑哥特木刻主题背景
      ctx.fillStyle = "#050308";
      ctx.fillRect(0, 0, 512, 512);

      // 厚重手绘轮廓线
      ctx.strokeStyle = isMurderAlert ? "#ef4444" : (isNight ? "#c084fc" : "#fbbf24"); // 鲜红或鲜紫 vs 鲜金
      ctx.shadowColor = isMurderAlert ? "#dc2626" : (isNight ? "#a855f7" : "#d97706");
      ctx.shadowBlur = 15;
      ctx.lineWidth = 6;

      // 审判边界
      ctx.beginPath();
      ctx.arc(256, 256, 220, 0, Math.PI * 2);
      ctx.stroke();

      ctx.strokeStyle = isMurderAlert ? "#991b1b" : (isNight ? "#4c1d95" : "#92400e");
      ctx.lineWidth = 14;
      ctx.shadowBlur = 0;
      ctx.beginPath();
      ctx.arc(256, 256, 240, 0, Math.PI * 2);
      ctx.stroke();

      // 双环内边框
      ctx.strokeStyle = isMurderAlert ? "#fca5a5" : (isNight ? "#f472b6" : "#fef08a"); // 浅红/粉 vs 浅黄
      ctx.shadowColor = isMurderAlert ? "#ef4444" : (isNight ? "#ec4899" : "#facc15");
      ctx.shadowBlur = 12;
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.arc(256, 256, 170, 0, Math.PI * 2);
      ctx.stroke();

      // 大卫之星/六芒星审判图案
      ctx.strokeStyle = isMurderAlert ? "#ef4444" : (isNight ? "#d946ef" : "#f59e0b");
      ctx.lineWidth = 5;
      ctx.shadowColor = isMurderAlert ? "#ef4444" : (isNight ? "#d946ef" : "#f59e0b");
      ctx.shadowBlur = 20;

      // 三角形 1
      ctx.beginPath();
      ctx.moveTo(256, 70);
      ctx.lineTo(410, 340);
      ctx.lineTo(102, 340);
      ctx.closePath();
      ctx.stroke();

      // 三角形 2
      ctx.beginPath();
      ctx.moveTo(256, 442);
      ctx.lineTo(410, 172);
      ctx.lineTo(102, 172);
      ctx.closePath();
      ctx.stroke();

      // 墨水雕刻、与游戏状态匹配的神秘符文
      ctx.fillStyle = isMurderAlert ? "#fee2e2" : (isNight ? "#fde047" : "#ffedd5"); // 霓虹黄光 vs 白金
      ctx.shadowColor = isMurderAlert ? "#fca5a5" : (isNight ? "#facc15" : "#fed7aa");
      ctx.shadowBlur = 15;
      ctx.font = "italic bold 18px 'Courier New', monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      const runes = ["IV", "☠", "VI", "🐺", "预", "W"];
      for (let i = 0; i < 6; i++) {
        const rAngle = (i / 6) * Math.PI * 2 - Math.PI / 2;
        const rX = 256 + Math.sin(rAngle) * 195;
        const rY = 256 + Math.cos(rAngle) * 195;
        ctx.save();
        ctx.translate(rX, rY);
        ctx.rotate(-rAngle);
        ctx.fillText(runes[i], 0, 0);
        ctx.restore();
      }

      // 绘制高对比度木刻划痕风格化图案
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1;
      ctx.shadowBlur = 0;
      ctx.globalAlpha = 0.2;
      for (let i = 0; i < 20; i++) {
        ctx.beginPath();
        ctx.moveTo(Math.random() * 512, Math.random() * 512);
        ctx.lineTo(Math.random() * 512, Math.random() * 512);
        ctx.stroke();
      }
    }

    if (textureRef.current) {
      textureRef.current.needsUpdate = true;
    }
    canvasRef.current = canvas;
  }, [isNight, isMurderAlert]);

  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.46, 0]}>
      <circleGeometry args={[tableRadius * 0.91, 64]} />
      <meshBasicMaterial color="#ffffff" side={THREE.DoubleSide}>
        <canvasTexture attach="map" image={canvasRef.current || undefined} ref={textureRef} />
      </meshBasicMaterial>
    </mesh>
  );
}

interface PlayerVisualTheme {
  primaryAccent: string;   // colorful sash/belt
  secondaryAccent: string; // glowing chest jewelry/collar glow
  cowlLining: string;      // inner hood contrasts
  beltColor: string;       // waist belt
}

function getPlayerVisualTheme(playerId: number): PlayerVisualTheme {
  // 根据座位 ID（1 到 8）平衡颜色模式
  const themes: Record<number, PlayerVisualTheme> = {
    1: { primaryAccent: "#fbbf24", secondaryAccent: "#fde047", cowlLining: "#713f12", beltColor: "#fbbf24" }, // 金色预言家
    2: { primaryAccent: "#38bdf8", secondaryAccent: "#67e8f9", cowlLining: "#0b5394", beltColor: "#0284c7" }, // 天蓝色
    3: { primaryAccent: "#f43f5e", secondaryAccent: "#fda4af", cowlLining: "#6b001a", beltColor: "#be123c" }, // 玫红狼人
    4: { primaryAccent: "#c084fc", secondaryAccent: "#e9d5ff", cowlLining: "#4c1d95", beltColor: "#7c3aed" }, // 宇宙紫女巫
    5: { primaryAccent: "#10b981", secondaryAccent: "#6ee7b7", cowlLining: "#064e3b", beltColor: "#047857" }, // 翡翠绿猎人
    6: { primaryAccent: "#f472b6", secondaryAccent: "#fbcfe8", cowlLining: "#6d183f", beltColor: "#db2777" }, // 日落康乃馨粉
    7: { primaryAccent: "#a855f7", secondaryAccent: "#c084fc", cowlLining: "#3b0764", beltColor: "#a855f7" }, // 紫水晶紫
    8: { primaryAccent: "#f97316", secondaryAccent: "#fdba74", cowlLining: "#7c2d12", beltColor: "#f97316" }, // 日落铜橙
  };
  return themes[playerId] || { primaryAccent: "#94a3b8", secondaryAccent: "#cbd5e1", cowlLining: "#1e293b", beltColor: "#94a3b8" };
}

function ChestGem({ color }: { color: string }) {
  const gemRef = useRef<THREE.Mesh>(null);
  useFrame((state) => {
    if (gemRef.current) {
      gemRef.current.rotation.y = state.clock.getElapsedTime() * 2.5;
      gemRef.current.rotation.z = state.clock.getElapsedTime() * 0.8;
    }
  });
  return (
    <group position={[0, 0.65, 0.22]}>
      {/* Small floating diamond */}
      <mesh ref={gemRef}>
        <octahedronGeometry args={[0.045, 0]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={3.5}
          roughness={0.1}
          metalness={0.9}
        />
      </mesh>
      {/* Ink wireframe to match woodcut aesthetic */}
      <mesh position={[0, 0, 0]} scale={[1.15, 1.15, 1.15]}>
        <octahedronGeometry args={[0.045, 0]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>
    </group>
  );
}

// 高质量棋子组件，替代兜帽人偶
interface HoodedFigureProps {
  isSpeaking: boolean;
  isUser: boolean;
  isAlive: boolean;
  playerId: number;
}

function ChessPiece({ isSpeaking, isUser, isAlive, playerId }: HoodedFigureProps) {
  const theme = getPlayerVisualTheme(playerId);

  const points = React.useMemo(() => {
    const pts = [];
    // 底座
    pts.push(new THREE.Vector2(0.001, 0));
    for (let i = 0; i <= 5; i++) {
      pts.push(new THREE.Vector2(0.4 + Math.cos((Math.PI / 2) * (i / 5)) * 0.03 - 0.03, 0.04 * (i / 5)));
    }
    pts.push(new THREE.Vector2(0.4, 0.08));
    pts.push(new THREE.Vector2(0.32, 0.15));
    pts.push(new THREE.Vector2(0.32, 0.2));
    pts.push(new THREE.Vector2(0.24, 0.25));
    
    // 柱身
    pts.push(new THREE.Vector2(0.2, 0.4));
    pts.push(new THREE.Vector2(0.16, 0.6));
    pts.push(new THREE.Vector2(0.16, 0.7));
    
    // 衣领
    pts.push(new THREE.Vector2(0.26, 0.75));
    pts.push(new THREE.Vector2(0.26, 0.82));
    pts.push(new THREE.Vector2(0.14, 0.86));
    
    // 头部球体
    for (let i = 0; i <= 16; i++) {
      const a = -Math.PI / 2 + (i / 16) * Math.PI;
      const x = Math.max(0.001, Math.cos(a) * 0.22);
      pts.push(new THREE.Vector2(x, 1.08 + Math.sin(a) * 0.22));
    }
    
    // 顶部装饰（皇冠/小圆球）
    pts.push(new THREE.Vector2(0.08, 1.3));
    pts.push(new THREE.Vector2(0.08, 1.38));
    pts.push(new THREE.Vector2(0.001, 1.4));
    return pts;
  }, []);

  const baseColor = isSpeaking 
    ? theme.primaryAccent 
    : isUser
      ? "#2e1065" // deep violet
      : "#0f0f11"; // glossy dark slate

  const materialProps = {
    color: baseColor,
    roughness: isSpeaking ? 0.05 : 0.1,
    metalness: isSpeaking ? 0.4 : 0.8,
    clearcoat: 1.0,
    clearcoatRoughness: 0.1,
    transmission: isSpeaking ? 0.2 : 0, 
    emissive: theme.primaryAccent,
    emissiveIntensity: isSpeaking ? 0.7 : (isUser ? 0.2 : 0.05),
  };

  return (
    <group position={[0, 0.4, 0]}>
       <pointLight
        position={[0, 1.5, 0]}
        distance={4.0}
        intensity={isSpeaking ? 1.5 : 0.3}
        color={theme.primaryAccent}
      />
      {/* Main body lathe */}
      <mesh>
        <latheGeometry args={[points, 64]} />
        <meshPhysicalMaterial {...materialProps} />
      </mesh>
      
      {/* Wireframe overlay for stylized anime/cel-shaded look */}
      <mesh scale={[1.01, 1.01, 1.01]}>
        <latheGeometry args={[points, 32]} />
        <meshBasicMaterial color={isSpeaking ? "#ffffff" : "#000000"} wireframe transparent opacity={Math.max(0.08, isSpeaking ? 0.2 : 0)} />
      </mesh>

      {/* Floating Magic Core Jewel (Spins in front of chest/body) */}
      {isAlive && <ChestGem color={theme.secondaryAccent} />}
      
      {/* Halo/Ring above head if speaking */}
      {isSpeaking && (
        <mesh position={[0, 1.6, 0]} rotation={[Math.PI/2, 0, 0]}>
          <torusGeometry args={[0.35, 0.015, 16, 64]} />
          <meshBasicMaterial color={theme.secondaryAccent} />
        </mesh>
      )}
    </group>
  );
}

// 代表每个玩家席位的石柱
interface SpeakerPillarProps {
  id: number;
  name: string;
  isAlive: boolean;
  isUser: boolean;
  isSpeaking: boolean;
  isThinking: boolean;
  isTargeted: boolean;
  angle: number;
}

function SpeakerSeat({ id, name, isAlive, isUser, isSpeaking, isThinking, isTargeted, angle }: SpeakerPillarProps) {
  const setupCount = useGameStore((state) => state.setupCount);
  const statePlayersCount = useGameStore((state) => state.state?.players?.length) || 0;
  const playersCount = setupCount !== null ? setupCount : (statePlayersCount || 6);
  const radius = Math.max(5, playersCount * 0.72);
  const x = Math.sin(angle) * radius;
  const z = Math.cos(angle) * radius;

  // 跟踪活跃发言时的悬浮/弹跳动画
  const ref = useRef<THREE.Group>(null);
  useFrame((state) => {
    if (ref.current) {
      if (isSpeaking) {
        // 活跃卡牌悬浮并旋转
        ref.current.position.y = 1.2 + Math.sin(state.clock.getElapsedTime() * 4) * 0.15;
        ref.current.rotation.y += 0.02;
      } else {
        // 平稳呼吸循环
        ref.current.position.y = 1.0 + Math.sin(state.clock.getElapsedTime() * 1.5 + id) * 0.05;
        ref.current.rotation.y = angle + Math.PI; // look inwards
      }
    }
  });

  // 基础岩石颜色：高对比度灰度配粗糙边缘
  const stoneColor = isAlive ? "#262626" : "#0d0d0d";
  const neonGlowColor = isSpeaking 
    ? "#3be8b0" // 荧光绿发言光晕
    : isUser
      ? "#a855f7" // 紫色用户强调色
      : "#3b0764";

  return (
    <group position={[x, 0, z]}>
      {/* Stone Pillar / Obelisk Base */}
      <mesh position={[0, 0.5, 0]}>
        <cylinderGeometry args={[0.6, 0.75, 1.2, 8]} />
        <meshPhysicalMaterial
          color={stoneColor}
          roughness={0.3}
          metalness={0.8}
          clearcoat={0.7}
          clearcoatRoughness={0.1}
          wireframe={isSpeaking}
        />
      </mesh>

      {/* Heavy ink outline wireframe effect */}
      <mesh position={[0, 0.5, 0]}>
        <cylinderGeometry args={[0.61, 0.76, 1.21, 8]} />
        <meshBasicMaterial color="#000000" wireframe transparent opacity={0.3} />
      </mesh>

      {/* Floating 3D Hooded Figure / Soul Sign of Life */}
      <group ref={ref}>
        {isAlive ? (
          <>
            <ChessPiece
              isSpeaking={isSpeaking}
              isUser={isUser}
              isAlive={isAlive}
              playerId={id}
            />
            {/* Glowing ring under speak flow */}
            {isSpeaking && (
              <mesh position={[0, -0.1, 0]} rotation={[Math.PI / 2, 0, 0]}>
                <ringGeometry args={[0.45, 0.65, 16]} />
                <meshBasicMaterial color="#ec4899" side={THREE.DoubleSide} />
              </mesh>
            )}
            {/* Soft cyan halo while waiting on the LLM (候场, distinct from speaking) */}
            {isThinking && !isSpeaking && (
              <mesh position={[0, -0.05, 0]} rotation={[Math.PI / 2, 0, 0]}>
                <ringGeometry args={[0.5, 0.62, 24]} />
                <meshBasicMaterial color="#22d3ee" transparent opacity={0.45} side={THREE.DoubleSide} />
              </mesh>
            )}
            {/* Amber targeting ring — the seat the human is selecting as a skill/vote target */}
            {isTargeted && (
              <mesh position={[0, 0.0, 0]} rotation={[Math.PI / 2, 0, 0]}>
                <ringGeometry args={[0.7, 0.92, 32]} />
                <meshBasicMaterial color="#f59e0b" transparent opacity={0.8} side={THREE.DoubleSide} />
              </mesh>
            )}
          </>
        ) : (
          /* Dead Tombstone Shape */
          <group position={[0, -0.3, 0]}>
            <mesh>
              <boxGeometry args={[0.5, 0.6, 0.15]} />
              <meshStandardMaterial color="#0a0a0c" roughness={1.0} />
            </mesh>
            {/* Engraved Crimson Cross */}
            <mesh position={[0, 0, 0.08]}>
              <boxGeometry args={[0.1, 0.4, 0.02]} />
              <meshBasicMaterial color="#dc2626" />
            </mesh>
            <mesh position={[0, 0.1, 0.08]}>
              <boxGeometry args={[0.3, 0.1, 0.02]} />
              <meshBasicMaterial color="#dc2626" />
            </mesh>
          </group>
        )}
      </group>
    </group>
  );
}

// 悬浮魔法元素/余烬，颜色随昼夜设置变化
function MagicalSparks({ isNight, isMurderAlert }: { isNight: boolean, isMurderAlert?: boolean }) {
  const pointsRef = useRef<THREE.Points>(null);
  const count = 75;
  const positions = React.useMemo(() => {
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 12; // X 坐标
      pos[i * 3 + 1] = Math.random() * 8; // Y 坐标
      pos[i * 3 + 2] = (Math.random() - 0.5) * 12; // Z 坐标
    }
    return pos;
  }, []);

  const targetColor = React.useMemo(() => new THREE.Color(isMurderAlert ? "#ef4444" : (isNight ? "#c084fc" : "#ff781f")), [isNight, isMurderAlert]);
  const matRef = useRef<THREE.PointsMaterial>(null);

  useFrame((state, delta) => {
    if (pointsRef.current) {
      const geo = pointsRef.current.geometry;
      const posAttr = geo.attributes.position as THREE.BufferAttribute;
      const time = state.clock.getElapsedTime();
      for (let i = 0; i < count; i++) {
        let y = posAttr.getY(i);
        // 缓慢上浮
        y += delta * 1.5 + Math.sin(time + i) * delta * 0.5;
        if (y > 7.5) {
          y = -0.5; // 从底部重新循环
        }
        posAttr.setY(i, y);

        // 轻微侧向漂移
        let x = posAttr.getX(i);
        x += Math.sin(time * 0.3 + i) * delta * 0.5;
        posAttr.setX(i, x);
      }
      posAttr.needsUpdate = true;
    }
    
    if (matRef.current) {
      matRef.current.color.lerp(targetColor, 1 - Math.exp(-3 * delta));
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        ref={matRef}
        size={0.16}
        sizeAttenuation={true}
        transparent
        opacity={0.8}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
}

function TableRim({ tableRadius, isNight, isMurderAlert }: { tableRadius: number, isNight: boolean, isMurderAlert?: boolean }) {
  const targetWireColor = React.useMemo(() => new THREE.Color(isMurderAlert ? "#dc2626" : isNight ? "#a855f7" : "#ea580c"), [isNight, isMurderAlert]);
  const targetSolidColor = React.useMemo(() => new THREE.Color(isMurderAlert ? "#ef4444" : isNight ? "#d946ef" : "#fbbf24"), [isNight, isMurderAlert]);
  
  const wireMatRef = useRef<THREE.MeshBasicMaterial>(null);
  const solidMatRef = useRef<THREE.MeshBasicMaterial>(null);

  useFrame((state, delta) => {
    const s = 1 - Math.exp(-3 * delta);
    if (wireMatRef.current) wireMatRef.current.color.lerp(targetWireColor, s);
    if (solidMatRef.current) solidMatRef.current.color.lerp(targetSolidColor, s);
  });

  return (
    <>
      <mesh position={[0, 0.2, 0]}>
        <cylinderGeometry args={[tableRadius + 0.01, tableRadius + 0.21, 0.41, 64]} />
        <meshBasicMaterial ref={wireMatRef} wireframe transparent opacity={0.3} />
      </mesh>
      <mesh position={[0, 0.4, 0]} rotation={[Math.PI/2, 0, 0]}>
        <torusGeometry args={[tableRadius, 0.015, 16, 64]} />
        <meshBasicMaterial ref={solidMatRef} />
      </mesh>
    </>
  );
}
function CentralEnergyOrb({ isNight, isMurderAlert }: { isNight: boolean, isMurderAlert?: boolean }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const lightRef = useRef<THREE.PointLight>(null);

  const targetLightColor = React.useMemo(() => new THREE.Color(isMurderAlert ? "#ef4444" : (isNight ? "#d946ef" : "#ff6a00")), [isNight, isMurderAlert]);
  const targetMatColor = React.useMemo(() => new THREE.Color(isMurderAlert ? "#dc2626" : (isNight ? "#8b5cf6" : "#ea580c")), [isNight, isMurderAlert]);
  const targetEmissiveColor = React.useMemo(() => new THREE.Color(isMurderAlert ? "#fca5a5" : (isNight ? "#f472b6" : "#fbbf24")), [isNight, isMurderAlert]);

  const matRef = useRef<THREE.MeshStandardMaterial>(null);

  useFrame((state, delta) => {
    const time = state.clock.getElapsedTime();
    const s = 1 - Math.exp(-3 * delta); // 平滑线性插值
    if (meshRef.current) {
      meshRef.current.rotation.x = time * 0.4;
      meshRef.current.rotation.y = time * 0.7;
      // 轻微脉动
      const scale = 1.0 + Math.sin(time * 3.5) * 0.12;
      meshRef.current.scale.set(scale, scale, scale);
    }
    if (lightRef.current) {
      // 极度活跃的光晕脉动结合线性插值
      const targetIntensity = (isNight ? 14.0 : 9.0) + Math.sin(time * 5) * 3.0;
      lightRef.current.intensity = THREE.MathUtils.lerp(lightRef.current.intensity, targetIntensity, s);
      lightRef.current.color.lerp(targetLightColor, s);
    }
    if (matRef.current) {
      matRef.current.color.lerp(targetMatColor, s);
      matRef.current.emissive.lerp(targetEmissiveColor, s);
    }
  });

  return (
    <group position={[0, 1.2, 0]}>
      <pointLight
        ref={lightRef}
        intensity={10}
        distance={12}
        castShadow
        shadow-bias={-0.0005}
      />
      <mesh ref={meshRef}>
        <dodecahedronGeometry args={[0.32, 1]} />
        <meshStandardMaterial
          ref={matRef}
          emissiveIntensity={3.5}
          roughness={0.1}
        />
      </mesh>
      <mesh position={[0, 0, 0]} scale={[1.12, 1.12, 1.12]}>
        <dodecahedronGeometry args={[0.32, 1]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>
    </group>
  );
}

const ThreeCanvas = React.memo(function ThreeCanvas() {
  const gameState = useGameStore((state) => state.state);
  const phase = gameState?.phase;
  const currentSpeakerId = gameState?.currentSpeakerId;
  const players = gameState?.players || [];
  const setupCount = useGameStore((state) => state.setupCount);
  const victimId = gameState?.victimId;
  const thinkingSeat = gameState?.liveCue?.thinking?.seat ?? null;
  const selectedTargetSeat = useGameStore((state) => state.selectedTargetSeat);

  // 跟踪服务器日志中最近的 isNight 状态以正确反映叙事状态
  const lastLogIsNight = gameState?.speechLogs?.[gameState.speechLogs.length - 1]?.isNight;
  // 根据昼夜切换切换环境颜色
  const isNight = phase?.startsWith("NIGHT") || lastLogIsNight || false;
  const isMurderAlert = phase === "DAY_ANNOUNCEMENT" && victimId !== null && victimId !== undefined;
  const sceneMode: SceneMode = resolveSceneMode(Boolean(isNight), Boolean(isMurderAlert));

  // START_SCREEN / 落地页（phase=undefined）渲染预览圆桌；否则映射真实玩家。
  const previewPlayers = React.useMemo(
    () =>
      buildPreviewSeats({
        phase,
        setupCount,
        players,
        currentSpeakerId: currentSpeakerId ?? null,
      }),
    [phase, setupCount, players, currentSpeakerId],
  );

  // 计算活跃发言者位置以将戏剧性灯光聚焦于其上
  let speakerLight = null;
  if (currentSpeakerId !== null && currentSpeakerId !== undefined) {
    const speakerIndex = previewPlayers.findIndex((p) => p.id === currentSpeakerId);
    if (speakerIndex !== -1) {
      const total = previewPlayers.length;
      const angle = (speakerIndex / total) * Math.PI * 2;
      const radius = Math.max(5, total * 0.72);
      const sX = Math.sin(angle) * radius;
      const sZ = Math.cos(angle) * radius;
      speakerLight = (
        <group>
          {/* Spotlight beam representing the divine/guilt trial beam */}
          <spotLight
            position={[sX, 6.5, sZ]}
            angle={0.4}
            penumbra={0.7}
            intensity={isNight ? 32.0 : 25.0} // 动态高功率主题光束
            color={isNight ? "#d946ef" : "#ff6a00"} // 皇家紫 vs 炽烈日落橙
            castShadow
            shadow-mapSize-width={512}
            shadow-mapSize-height={512}
          />
          {/* Neon secondary light aura on the hooded figure */}
          <pointLight
            position={[sX, 1.8, sZ]}
            intensity={6.0}
            distance={6}
            color={isNight ? "#a855f7" : "#ff781f"} // 霓虹紫水晶紫 vs 太阳烈焰橙
          />
          {/* Volumetric Visual Light Cone Cylinder (Additive spectacular atmosphere beam!) */}
          <mesh position={[sX, 3.4, sZ]}>
            <cylinderGeometry args={[0.08, 1.5, 6.0, 32, 1, true]} />
            <meshBasicMaterial
              color={isNight ? "#d946ef" : "#ff6a00"}
              transparent
              opacity={isNight ? 0.18 : 0.14}
              blending={THREE.AdditiveBlending}
              side={THREE.DoubleSide}
              depthWrite={false}
            />
          </mesh>
        </group>
      );
    }
  }

  return (
    <div className="absolute inset-0 w-full h-full z-0 pointer-events-none">
      <Canvas
        shadows
        gl={{ antialias: true }}
        camera={{ position: [0, 9.25, 13], fov: 45 }}
        style={{ pointerEvents: "auto" }}
      >
        <EnvironmentController mode={sceneMode} />

        {/* Floating Sparks in the atmospheric space */}
        <MagicalSparks isNight={isNight} isMurderAlert={isMurderAlert} />

        {/* Theatrical speaking spot highlight */}
        {speakerLight}

        {/* 3D Round Consultation Table (审判大议事桌) */}
        <group position={[0, -0.5, 0]}>
          {(() => {
            const playersCount = previewPlayers.length;
            const radius = Math.max(5, playersCount * 0.72);
            const tableRadius = Math.max(3.5, radius * 0.7);
            return (
              <>
                <mesh receiveShadow position={[0, 0.2, 0]}>
                  <cylinderGeometry args={[tableRadius, tableRadius + 0.2, 0.4, 64]} />
                  <meshPhysicalMaterial
                    color="#050505"
                    roughness={0.05}
                    metalness={0.9}
                    clearcoat={1.0}
                    clearcoatRoughness={0.05}
                  />
                </mesh>
                
                {/* Glowing neon edge rim */}
                <TableRim tableRadius={tableRadius} isNight={isNight} isMurderAlert={isMurderAlert} />

                {/* Central Trial sigil / Magic trial floor decals */}
                <TrialSigil tableRadius={tableRadius} isNight={isNight} isMurderAlert={isMurderAlert} />
              </>
            );
          })()}

          {/* Central neon glowing magical orb of judgement */}
          <CentralEnergyOrb isNight={isNight} isMurderAlert={isMurderAlert} />

          {/* Render circular array of players sitting seats */}
          {previewPlayers.map((p, idx) => {
            const angle = (idx / previewPlayers.length) * Math.PI * 2;
            return (
              <SpeakerSeat
                key={p.id}
                id={p.id}
                name={p.name}
                isAlive={p.isAlive}
                isUser={p.isUser}
                isSpeaking={p.isSpeaking}
                isThinking={thinkingSeat === p.id}
                isTargeted={selectedTargetSeat === p.id}
                angle={angle}
              />
            );
          })}
        </group>

        {/* Smooth camera interpolation assistant */}
        <CameraTracker />
      </Canvas>
    </div>
  );
});

export default ThreeCanvas;
