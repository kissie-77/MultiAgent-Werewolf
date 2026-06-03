import React, { useRef, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { useGameStore } from "../store";

// Derive current speaker seat from the most recent speech log
function useCurrentSpeakerSeat(): number | null {
  const logs = useGameStore((state) => state.logs);
  for (let i = logs.length - 1; i >= 0; i--) {
    if (logs[i].kind === "speech" && logs[i].speakerSeat != null) {
      return logs[i].speakerSeat;
    }
  }
  return null;
}

// Camera controller component to smoothly pan and track the active speaker
function CameraTracker() {
  const { camera } = useThree();
  const snapshot = useGameStore((state) => state.snapshot);
  const status = useGameStore((state) => state.status);
  const currentSpeakerSeat = useCurrentSpeakerSeat();

  const players = snapshot?.players || [];
  const phase = snapshot?.phase ?? "";

  // Targets for camera position and target position
  const targetCamPos = useRef(new THREE.Vector3(0, 8.5, 12.0));
  const targetLookAt = useRef(new THREE.Vector3(0, 0.4, 0));
  const currentLookAt = useRef(new THREE.Vector3(0, 0.4, 0));

  useEffect(() => {
    if (status === "idle") {
      return; // Handled directly in useFrame for slow orbital motion
    }
    if (currentSpeakerSeat != null) {
      // Find speaker position
      const speakerIndex = players.findIndex((p) => p.seat === currentSpeakerSeat);
      if (speakerIndex !== -1) {
        const total = players.length;
        const angle = (speakerIndex / total) * Math.PI * 2;
        const radius = Math.max(5, total * 0.72);

        const sX = Math.sin(angle) * radius;
        const sZ = Math.cos(angle) * radius;

        targetCamPos.current.set(sX * 1.55, radius * 1.2, sZ * 1.55);
        targetLookAt.current.set(sX * 0.8, 0.8, sZ * 0.8);
      }
    } else {
      // Return to overall view of the central roundtable
      const radius = Math.max(5, players.length * 0.72);
      targetCamPos.current.set(0, radius * 1.5, radius * 2.2);
      targetLookAt.current.set(0, 0.4, 0);
    }
  }, [currentSpeakerSeat, players, phase, status]);

  useFrame((state, delta) => {
    if (status === "idle") {
      // Background orbital slow rotation motion
      const time = state.clock.getElapsedTime();
      const orbitSpeed = 0.08;
      const pCount = players.length || 6;
      const radius = Math.max(5, pCount * 0.72);
      const orbitRadius = radius * 3.4;

      const x = Math.sin(time * orbitSpeed) * orbitRadius;
      const z = Math.cos(time * orbitSpeed) * orbitRadius;

      camera.position.lerp(new THREE.Vector3(x, radius * 1.6, z), 0.05);
      currentLookAt.current.lerp(new THREE.Vector3(0, 0.4, 0), 0.05);
      camera.lookAt(currentLookAt.current);
    } else {
      camera.position.lerp(targetCamPos.current, 0.05);
      currentLookAt.current.lerp(targetLookAt.current, 0.05);
      camera.lookAt(currentLookAt.current);
    }
  });

  return null;
}

// Procedural texture for the trial array magic circle
interface TrialSigilProps {
  tableRadius: number;
}

function TrialSigil({ tableRadius }: TrialSigilProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const textureRef = useRef<THREE.CanvasTexture | null>(null);

  useEffect(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.fillStyle = "#110b15";
      ctx.fillRect(0, 0, 512, 512);

      ctx.strokeStyle = "#a855f7";
      ctx.lineWidth = 6;
      ctx.beginPath();
      ctx.arc(256, 256, 220, 0, Math.PI * 2);
      ctx.stroke();

      ctx.strokeStyle = "#3b0764";
      ctx.lineWidth = 14;
      ctx.beginPath();
      ctx.arc(256, 256, 240, 0, Math.PI * 2);
      ctx.stroke();

      ctx.strokeStyle = "#ec4899";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(256, 256, 170, 0, Math.PI * 2);
      ctx.stroke();

      ctx.strokeStyle = "#a855f7";
      ctx.lineWidth = 4;
      ctx.shadowColor = "#a855f7";
      ctx.shadowBlur = 10;

      ctx.beginPath();
      ctx.moveTo(256, 70);
      ctx.lineTo(410, 340);
      ctx.lineTo(102, 340);
      ctx.closePath();
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(256, 442);
      ctx.lineTo(410, 172);
      ctx.lineTo(102, 172);
      ctx.closePath();
      ctx.stroke();

      ctx.fillStyle = "#facc15";
      ctx.shadowBlur = 5;
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
  }, []);

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
  primaryAccent: string;
  secondaryAccent: string;
  cowlLining: string;
  beltColor: string;
}

function getPlayerVisualTheme(seat: number): PlayerVisualTheme {
  const themes: Record<number, PlayerVisualTheme> = {
    1: { primaryAccent: "#fbbf24", secondaryAccent: "#fde047", cowlLining: "#713f12", beltColor: "#fbbf24" },
    2: { primaryAccent: "#38bdf8", secondaryAccent: "#67e8f9", cowlLining: "#0b5394", beltColor: "#0284c7" },
    3: { primaryAccent: "#f43f5e", secondaryAccent: "#fda4af", cowlLining: "#6b001a", beltColor: "#be123c" },
    4: { primaryAccent: "#c084fc", secondaryAccent: "#e9d5ff", cowlLining: "#4c1d95", beltColor: "#7c3aed" },
    5: { primaryAccent: "#10b981", secondaryAccent: "#6ee7b7", cowlLining: "#064e3b", beltColor: "#047857" },
    6: { primaryAccent: "#f472b6", secondaryAccent: "#fbcfe8", cowlLining: "#6d183f", beltColor: "#db2777" },
    7: { primaryAccent: "#a855f7", secondaryAccent: "#c084fc", cowlLining: "#3b0764", beltColor: "#a855f7" },
    8: { primaryAccent: "#f97316", secondaryAccent: "#fdba74", cowlLining: "#7c2d12", beltColor: "#f97316" },
  };
  return themes[seat] || { primaryAccent: "#94a3b8", secondaryAccent: "#cbd5e1", cowlLining: "#1e293b", beltColor: "#94a3b8" };
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
      <mesh position={[0, 0, 0]} scale={[1.15, 1.15, 1.15]}>
        <octahedronGeometry args={[0.045, 0]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>
    </group>
  );
}

interface HoodedFigureProps {
  isSpeaking: boolean;
  isAlive: boolean;
  seat: number;
}

function HoodedFigure({ isSpeaking, isAlive, seat }: HoodedFigureProps) {
  const theme = getPlayerVisualTheme(seat);

  const robeColor = isSpeaking ? "#3f0d1a" : "#141416";
  const glowColor = isSpeaking ? "#10b981" : "#ef4444";

  return (
    <group>
      <pointLight
        position={[0, 0.65, 0.35]}
        distance={2.4}
        intensity={isSpeaking ? 0.8 : 0.45}
        color={theme.primaryAccent}
      />

      {/* 1. Robe/Body */}
      <mesh position={[0, 0.45, 0]}>
        <cylinderGeometry args={[0.13, 0.36, 0.9, 16]} />
        <meshStandardMaterial
          color={robeColor}
          roughness={0.8}
          metalness={0.15}
          emissive={theme.primaryAccent}
          emissiveIntensity={0.15}
        />
      </mesh>
      <mesh position={[0, 0.45, 0]} scale={[1.03, 1.01, 1.03]}>
        <cylinderGeometry args={[0.13, 0.36, 0.9, 16]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>

      {/* Decorative Waist Sash */}
      <mesh position={[0, 0.32, 0]} rotation={[0.04, 0, 0]}>
        <cylinderGeometry args={[0.26, 0.28, 0.08, 16]} />
        <meshStandardMaterial color={theme.beltColor} roughness={0.6} metalness={0.3} />
      </mesh>
      <mesh position={[0, 0.32, 0]} rotation={[0.04, 0, 0]} scale={[1.03, 1.03, 1.03]}>
        <cylinderGeometry args={[0.26, 0.28, 0.08, 16]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>

      {/* Ornamental Belt Buckle */}
      <mesh position={[0, 0.32, 0.28]}>
        <sphereGeometry args={[0.035, 8, 8]} />
        <meshStandardMaterial color="#ffffff" emissive={theme.secondaryAccent} emissiveIntensity={1.0} roughness={0.2} />
      </mesh>
      <mesh position={[0, 0.32, 0.28]} scale={[1.15, 1.15, 1.15]}>
        <sphereGeometry args={[0.035, 8, 8]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>

      {/* 2. Crossed arms / thick sleeve block */}
      <mesh position={[0, 0.52, 0.16]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.06, 0.06, 0.32, 8]} />
        <meshStandardMaterial color={robeColor} roughness={0.8} />
      </mesh>
      <mesh position={[0, 0.52, 0.16]} rotation={[0, 0, Math.PI / 2]} scale={[1.04, 1.04, 1.04]}>
        <cylinderGeometry args={[0.06, 0.06, 0.32, 8]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>

      {/* Sleeve Cuffs */}
      <mesh position={[-0.14, 0.52, 0.16]} rotation={[0, Math.PI / 2, 0]}>
        <torusGeometry args={[0.062, 0.015, 6, 12]} />
        <meshStandardMaterial color={theme.primaryAccent} roughness={0.3} metalness={0.7} />
      </mesh>
      <mesh position={[0.14, 0.52, 0.16]} rotation={[0, Math.PI / 2, 0]}>
        <torusGeometry args={[0.062, 0.015, 6, 12]} />
        <meshStandardMaterial color={theme.primaryAccent} roughness={0.3} metalness={0.7} />
      </mesh>

      {/* 3. Cape over shoulders */}
      <mesh position={[0, 0.76, 0]}>
        <sphereGeometry args={[0.23, 16, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshStandardMaterial color={robeColor} roughness={0.8} />
      </mesh>
      <mesh position={[0, 0.76, 0]} scale={[1.04, 1.04, 1.04]}>
        <sphereGeometry args={[0.23, 16, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>

      {/* Decorative Collar */}
      <mesh position={[0, 0.78, 0]} rotation={[Math.PI / 2 + 0.1, 0, 0]}>
        <torusGeometry args={[0.22, 0.018, 8, 24]} />
        <meshStandardMaterial color={theme.primaryAccent} metalness={0.8} roughness={0.2} />
      </mesh>
      <mesh position={[0, 0.78, 0]} rotation={[Math.PI / 2 + 0.1, 0, 0]} scale={[1.04, 1.04, 1.04]}>
        <torusGeometry args={[0.22, 0.018, 8, 24]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>

      {/* 4. Head/Void face */}
      <mesh position={[0, 0.98, 0.03]}>
        <sphereGeometry args={[0.16, 16, 16]} />
        <meshStandardMaterial color="#040405" roughness={0.95} />
      </mesh>

      {/* Animated Floating Magic Core Jewel */}
      {isAlive && <ChestGem color={theme.secondaryAccent} />}

      {/* 5. Glowing magical eyes */}
      {isAlive && (
        <group>
          <mesh position={[-0.05, 1.0, 0.15]}>
            <sphereGeometry args={[0.016, 8, 8]} />
            <meshStandardMaterial
              color={glowColor}
              emissive={glowColor}
              emissiveIntensity={1.8}
            />
          </mesh>
          <mesh position={[0.05, 1.0, 0.15]}>
            <sphereGeometry args={[0.016, 8, 8]} />
            <meshStandardMaterial
              color={glowColor}
              emissive={glowColor}
              emissiveIntensity={1.8}
            />
          </mesh>
        </group>
      )}

      {/* 6. Cowl / Hood */}
      <mesh position={[0, 0.98, 0.01]}>
        <torusGeometry args={[0.16, 0.042, 8, 24]} />
        <meshStandardMaterial
          color={robeColor}
          roughness={0.8}
          emissive={theme.primaryAccent}
          emissiveIntensity={0.1}
        />
      </mesh>
      <mesh position={[0, 0.98, 0.01]} scale={[1.03, 1.03, 1.03]}>
        <torusGeometry args={[0.16, 0.042, 8, 24]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>

      {/* Contrast Edge Trim */}
      <mesh position={[0, 0.98, 0.02]}>
        <torusGeometry args={[0.15, 0.01, 8, 24]} />
        <meshBasicMaterial color={theme.primaryAccent} />
      </mesh>

      {/* Pointy tip of the hood at back */}
      <mesh position={[0, 1.08, -0.09]} rotation={[Math.PI / 7, 0, 0]}>
        <coneGeometry args={[0.13, 0.35, 12]} />
        <meshStandardMaterial
          color={robeColor}
          roughness={0.8}
          emissive={theme.primaryAccent}
          emissiveIntensity={0.1}
        />
      </mesh>
      <mesh position={[0, 1.08, -0.09]} rotation={[Math.PI / 7, 0, 0]} scale={[1.03, 1.03, 1.03]}>
        <coneGeometry args={[0.13, 0.35, 12]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>
    </group>
  );
}

interface SpeakerSeatProps {
  seat: number;
  name: string;
  isAlive: boolean;
  isSpeaking: boolean;
  angle: number;
  playersCount: number;
}

function SpeakerSeat({ seat, name, isAlive, isSpeaking, angle, playersCount }: SpeakerSeatProps) {
  const radius = Math.max(5, playersCount * 0.72);
  const x = Math.sin(angle) * radius;
  const z = Math.cos(angle) * radius;

  const ref = useRef<THREE.Group>(null);
  useFrame((state) => {
    if (ref.current) {
      if (isSpeaking) {
        ref.current.position.y = 1.2 + Math.sin(state.clock.getElapsedTime() * 4) * 0.15;
        ref.current.rotation.y += 0.02;
      } else {
        ref.current.position.y = 1.0 + Math.sin(state.clock.getElapsedTime() * 1.5 + seat) * 0.05;
        ref.current.rotation.y = angle + Math.PI;
      }
    }
  });

  const stoneColor = isAlive ? "#262626" : "#0d0d0d";

  return (
    <group position={[x, 0, z]}>
      {/* Stone Pillar / Obelisk Base */}
      <mesh position={[0, 0.5, 0]}>
        <cylinderGeometry args={[0.6, 0.7, 1.2, 6]} />
        <meshStandardMaterial
          color={stoneColor}
          roughness={0.9}
          metalness={0.1}
          wireframe={isSpeaking}
        />
      </mesh>

      <mesh position={[0, 0.5, 0]}>
        <cylinderGeometry args={[0.61, 0.71, 1.21, 6]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>

      <group ref={ref}>
        {isAlive ? (
          <>
            <HoodedFigure
              isSpeaking={isSpeaking}
              isAlive={isAlive}
              seat={seat}
            />
            {isSpeaking && (
              <mesh position={[0, -0.1, 0]} rotation={[Math.PI / 2, 0, 0]}>
                <ringGeometry args={[0.45, 0.65, 16]} />
                <meshBasicMaterial color="#ec4899" side={THREE.DoubleSide} />
              </mesh>
            )}
          </>
        ) : (
          <group position={[0, -0.3, 0]}>
            <mesh>
              <boxGeometry args={[0.5, 0.6, 0.15]} />
              <meshStandardMaterial color="#0a0a0c" roughness={1.0} />
            </mesh>
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

function MagicalSparks({ isNight }: { isNight: boolean }) {
  const pointsRef = useRef<THREE.Points>(null);
  const count = 75;
  const positions = React.useMemo(() => {
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 12;
      pos[i * 3 + 1] = Math.random() * 8;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 12;
    }
    return pos;
  }, []);

  useFrame((state) => {
    if (pointsRef.current) {
      const geo = pointsRef.current.geometry;
      const posAttr = geo.attributes.position as THREE.BufferAttribute;
      const time = state.clock.getElapsedTime();
      for (let i = 0; i < count; i++) {
        let y = posAttr.getY(i);
        y += 0.02 + Math.sin(time + i) * 0.005;
        if (y > 7.5) {
          y = -0.5;
        }
        posAttr.setY(i, y);

        let x = posAttr.getX(i);
        x += Math.sin(time * 0.3 + i) * 0.008;
        posAttr.setX(i, x);
      }
      posAttr.needsUpdate = true;
    }
  });

  const sparkColor = isNight ? "#c084fc" : "#ff781f";

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        color={sparkColor}
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

function CentralEnergyOrb({ isNight }: { isNight: boolean }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const lightRef = useRef<THREE.PointLight>(null);

  useFrame((state) => {
    const time = state.clock.getElapsedTime();
    if (meshRef.current) {
      meshRef.current.rotation.x = time * 0.4;
      meshRef.current.rotation.y = time * 0.7;
      const scale = 1.0 + Math.sin(time * 3.5) * 0.12;
      meshRef.current.scale.set(scale, scale, scale);
    }
    if (lightRef.current) {
      lightRef.current.intensity = (isNight ? 14.0 : 9.0) + Math.sin(time * 5) * 3.0;
    }
  });

  const lightColorDef = isNight ? "#d946ef" : "#ff6a00";
  const matColorDef = isNight ? "#8b5cf6" : "#ea580c";
  const emissiveColorDef = isNight ? "#f472b6" : "#fbbf24";

  return (
    <group position={[0, 1.2, 0]}>
      <pointLight
        ref={lightRef}
        intensity={isNight ? 14.0 : 9.0}
        color={lightColorDef}
        distance={12}
        castShadow
        shadow-bias={-0.0005}
      />
      <mesh ref={meshRef}>
        <dodecahedronGeometry args={[0.32, 1]} />
        <meshStandardMaterial
          color={matColorDef}
          emissive={emissiveColorDef}
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
  const snapshot = useGameStore((state) => state.snapshot);
  const status = useGameStore((state) => state.status);
  const currentSpeakerSeat = useCurrentSpeakerSeat();

  const phase = snapshot?.phase ?? "";
  // Derive night from phase name (Python backend uses lowercase phase names)
  const isNight = phase === "night" || phase === "setup" || status === "idle";
  const fogColor = isNight ? "#0d0415" : "#1e0b02";
  const lightColor = isNight ? "#7c3aed" : "#ea580c";
  const ambientIntensity = isNight ? 0.15 : 0.38;

  // Build preview players: during idle use 6 placeholder seats; during game use snapshot players
  const previewPlayers = React.useMemo(() => {
    if (status === "idle" || !snapshot) {
      // Show 6 placeholder seats during setup screen
      return Array.from({ length: 6 }, (_, idx) => ({
        seat: idx + 1,
        name: `席位 ${idx + 1}`,
        is_alive: true,
        isSpeaking: false,
      }));
    }
    return (snapshot.players || []).map((p) => ({
      seat: p.seat,
      name: p.name,
      is_alive: p.is_alive,
      isSpeaking: currentSpeakerSeat === p.seat,
    }));
  }, [status, snapshot, currentSpeakerSeat]);

  const playersCount = previewPlayers.length;

  // Compute position of active speaker for dramatic lighting
  let speakerLight = null;
  if (currentSpeakerSeat != null) {
    const speakerIndex = previewPlayers.findIndex((p) => p.seat === currentSpeakerSeat);
    if (speakerIndex !== -1) {
      const total = previewPlayers.length;
      const angle = (speakerIndex / total) * Math.PI * 2;
      const radius = Math.max(5, total * 0.72);
      const sX = Math.sin(angle) * radius;
      const sZ = Math.cos(angle) * radius;
      speakerLight = (
        <group>
          <spotLight
            position={[sX, 6.5, sZ]}
            angle={0.4}
            penumbra={0.7}
            intensity={isNight ? 32.0 : 25.0}
            color={isNight ? "#d946ef" : "#ff6a00"}
            castShadow
            shadow-mapSize-width={512}
            shadow-mapSize-height={512}
          />
          <pointLight
            position={[sX, 1.8, sZ]}
            intensity={6.0}
            distance={6}
            color={isNight ? "#a855f7" : "#ff781f"}
          />
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
        camera={{ position: [0, 8.5, 12.0], fov: 45 }}
        style={{ pointerEvents: "auto" }}
      >
        <color attach="background" args={[fogColor]} />
        <fog attach="fog" args={[fogColor, 10, 24]} />

        <ambientLight intensity={ambientIntensity} color={lightColor} />

        <MagicalSparks isNight={isNight} />

        {isNight ? (
          <directionalLight
            position={[-10, 14, -5]}
            intensity={4.5}
            color="#d946ef"
            castShadow
            shadow-mapSize-width={1024}
            shadow-mapSize-height={1024}
          />
        ) : (
          <directionalLight
            position={[10, 15, 5]}
            intensity={5.5}
            color="#ff6a00"
            castShadow
            shadow-mapSize-width={1024}
            shadow-mapSize-height={1024}
          />
        )}

        {speakerLight}

        <group position={[0, -0.5, 0]}>
          {(() => {
            const radius = Math.max(5, playersCount * 0.72);
            const tableRadius = Math.max(3.5, radius * 0.7);
            return (
              <>
                <mesh receiveShadow position={[0, 0.2, 0]}>
                  <cylinderGeometry args={[tableRadius, tableRadius + 0.2, 0.4, 64]} />
                  <meshStandardMaterial
                    color="#0e0c12"
                    roughness={0.8}
                    metalness={0.2}
                  />
                </mesh>

                <mesh position={[0, 0.2, 0]}>
                  <cylinderGeometry args={[tableRadius + 0.01, tableRadius + 0.21, 0.41, 64]} />
                  <meshBasicMaterial color="#000000" wireframe />
                </mesh>

                <TrialSigil tableRadius={tableRadius} />
              </>
            );
          })()}

          <CentralEnergyOrb isNight={isNight} />

          {previewPlayers.map((p, idx) => {
            const angle = (idx / previewPlayers.length) * Math.PI * 2;
            return (
              <SpeakerSeat
                key={p.seat}
                seat={p.seat}
                name={p.name}
                isAlive={p.is_alive}
                isSpeaking={p.isSpeaking}
                angle={angle}
                playersCount={playersCount}
              />
            );
          })}
        </group>

        <CameraTracker />

        <OrbitControls
          enableZoom={true}
          maxPolarAngle={Math.PI / 2 - 0.05}
          minDistance={5}
          maxDistance={18}
        />
      </Canvas>
    </div>
  );
});

export default ThreeCanvas;
