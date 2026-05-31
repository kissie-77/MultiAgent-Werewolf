import React, { useRef, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Line } from "@react-three/drei";
import * as THREE from "three";
import { useGameStore } from "../store";

// Camera controller component to smoothly pan and track the active speaker
function CameraTracker() {
  const { camera } = useThree();
  const gameState = useGameStore((state) => state.state);
  const setupCount = useGameStore((state) => state.setupCount);
  const currentSpeakerId = gameState?.currentSpeakerId;
  const players = gameState?.players || [];
  const phase = gameState?.phase;

  // Targets for camera position and target position
  const targetCamPos = useRef(new THREE.Vector3(0, 8.5, 12.0));
  const targetLookAt = useRef(new THREE.Vector3(0, 0.4, 0));
  const currentLookAt = useRef(new THREE.Vector3(0, 0.4, 0));

  useEffect(() => {
    if (phase === "START_SCREEN") {
      return; // Handled directly in useFrame for slow orbital motion
    }
    if (currentSpeakerId) {
      // Find speaker position
      const speakerIndex = players.findIndex((p) => p.id === currentSpeakerId);
      if (speakerIndex !== -1) {
        const total = players.length;
        const angle = (speakerIndex / total) * Math.PI * 2;
        const radius = Math.max(5, total * 0.72); // Dynamic radius

        // Set camera closer to the speaker
        const sX = Math.sin(angle) * radius;
        const sZ = Math.cos(angle) * radius;

        // Position camera closer to the active speaker hooded figure
        targetCamPos.current.set(sX * 1.55, radius * 1.2, sZ * 1.55);
        targetLookAt.current.set(sX * 0.8, 0.8, sZ * 0.8);
      }
    } else {
      // Return to overall view of the central roundtable
      const radius = Math.max(5, players.length * 0.72);
      targetCamPos.current.set(0, radius * 1.5, radius * 2.2);
      targetLookAt.current.set(0, 0.4, 0);
    }
  }, [currentSpeakerId, players, phase]);

  useFrame((state, delta) => {
    if (phase === "START_SCREEN") {
      // Background orbital slow rotation motion
      const time = state.clock.getElapsedTime();
      const orbitSpeed = 0.08;
      const pCount = setupCount !== null ? setupCount : (players.length || 6);
      const radius = Math.max(5, pCount * 0.72);
      const orbitRadius = radius * 3.4; // majestic outer distance

      const x = Math.sin(time * orbitSpeed) * orbitRadius;
      const z = Math.cos(time * orbitSpeed) * orbitRadius;

      camera.position.lerp(new THREE.Vector3(x, radius * 1.6, z), 0.05);
      currentLookAt.current.lerp(new THREE.Vector3(0, 0.4, 0), 0.05);
      camera.lookAt(currentLookAt.current);
    } else {
      // Smoothly step position
      camera.position.lerp(targetCamPos.current, 0.05);

      // Smoothly step lookAt coordinate
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
    // Draw woodcut magical array on a 512x512 canvas
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      // Dark gothic woodcut theme background
      ctx.fillStyle = "#110b15";
      ctx.fillRect(0, 0, 512, 512);

      // Heavy hand-drawn outlines
      ctx.strokeStyle = "#a855f7"; // purple glow
      ctx.lineWidth = 6;

      // Outer trial boundaries
      ctx.beginPath();
      ctx.arc(256, 256, 220, 0, Math.PI * 2);
      ctx.stroke();

      ctx.strokeStyle = "#3b0764";
      ctx.lineWidth = 14;
      ctx.beginPath();
      ctx.arc(256, 256, 240, 0, Math.PI * 2);
      ctx.stroke();

      // Double ring inner border
      ctx.strokeStyle = "#ec4899"; // pink neon highlights
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(256, 256, 170, 0, Math.PI * 2);
      ctx.stroke();

      // Star of David / Hexagram trial pattern
      ctx.strokeStyle = "#a855f7";
      ctx.lineWidth = 4;
      ctx.shadowColor = "#a855f7";
      ctx.shadowBlur = 10;

      // Triangle 1
      ctx.beginPath();
      ctx.moveTo(256, 70);
      ctx.lineTo(410, 340);
      ctx.lineTo(102, 340);
      ctx.closePath();
      ctx.stroke();

      // Triangle 2
      ctx.beginPath();
      ctx.moveTo(256, 442);
      ctx.lineTo(410, 172);
      ctx.lineTo(102, 172);
      ctx.closePath();
      ctx.stroke();

      // Ink engravings, mystical runes matching gamestate
      ctx.fillStyle = "#facc15"; // neon yellow glow
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

      // Draw stylized high contrast wood scratches
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
  primaryAccent: string;   // colorful sash/belt
  secondaryAccent: string; // glowing chest jewelry/collar glow
  cowlLining: string;      // inner hood contrasts
  beltColor: string;       // waist belt
}

function getPlayerVisualTheme(playerId: number): PlayerVisualTheme {
  // Balanced color patterns based on seat id (1 to 8)
  const themes: Record<number, PlayerVisualTheme> = {
    1: { primaryAccent: "#fbbf24", secondaryAccent: "#fde047", cowlLining: "#713f12", beltColor: "#fbbf24" }, // Gold Seer
    2: { primaryAccent: "#38bdf8", secondaryAccent: "#67e8f9", cowlLining: "#0b5394", beltColor: "#0284c7" }, // Celeste Blue
    3: { primaryAccent: "#f43f5e", secondaryAccent: "#fda4af", cowlLining: "#6b001a", beltColor: "#be123c" }, // Rose-Red Werewolf
    4: { primaryAccent: "#c084fc", secondaryAccent: "#e9d5ff", cowlLining: "#4c1d95", beltColor: "#7c3aed" }, // Cosmic Amethyst Witch
    5: { primaryAccent: "#10b981", secondaryAccent: "#6ee7b7", cowlLining: "#064e3b", beltColor: "#047857" }, // Jade-Green Hunter
    6: { primaryAccent: "#f472b6", secondaryAccent: "#fbcfe8", cowlLining: "#6d183f", beltColor: "#db2777" }, // Sunset Carnation pink
    7: { primaryAccent: "#a855f7", secondaryAccent: "#c084fc", cowlLining: "#3b0764", beltColor: "#a855f7" }, // Amethyst Purple
    8: { primaryAccent: "#f97316", secondaryAccent: "#fdba74", cowlLining: "#7c2d12", beltColor: "#f97316" }, // Sunset Copper Orange
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

// Outer custom Hooded Figure component to render instead of the simple tablet
interface HoodedFigureProps {
  isSpeaking: boolean;
  isUser: boolean;
  isAlive: boolean;
  playerId: number;
}

function HoodedFigure({ isSpeaking, isUser, isAlive, playerId }: HoodedFigureProps) {
  const theme = getPlayerVisualTheme(playerId);

  // Robe and cowl colors: User is indigo/purple, speaking is dark crimson wine, inactive is very dark charcoal
  const robeColor = isSpeaking
    ? "#3f0d1a" // dark speaking burgundy
    : isUser
      ? "#1e1145" // dark purple for user
      : "#141416"; // dark slate charcoal for AI

  const glowColor = isSpeaking
    ? "#10b981" // emerald green speak glow
    : isUser
      ? "#a855f7" // purple user accent
      : "#ef4444"; // red warning eyes for default spectators

  return (
    <group>
      {/* Soft atmospheric breathing self-illuminated glow light source */}
      <pointLight
        position={[0, 0.65, 0.35]}
        distance={2.4}
        intensity={isSpeaking ? 0.8 : 0.45}
        color={theme.primaryAccent}
      />

      {/* 1. Robe/Body (tapered cloak cylinder) */}
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
      {/* Outline block for hand-drawn anime look */}
      <mesh position={[0, 0.45, 0]} scale={[1.03, 1.01, 1.03]}>
        <cylinderGeometry args={[0.13, 0.36, 0.9, 16]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>

      {/* Decorative Waist Sash (腰带/封条裙摆) */}
      <mesh position={[0, 0.32, 0]} rotation={[0.04, 0, 0]}>
        <cylinderGeometry args={[0.26, 0.28, 0.08, 16]} />
        <meshStandardMaterial color={theme.beltColor} roughness={0.6} metalness={0.3} />
      </mesh>
      <mesh position={[0, 0.32, 0]} rotation={[0.04, 0, 0]} scale={[1.03, 1.03, 1.03]}>
        <cylinderGeometry args={[0.26, 0.28, 0.08, 16]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>

      {/* Ornamental Belt Buckle Core (核心皮带扣) */}
      <mesh position={[0, 0.32, 0.28]}>
        <sphereGeometry args={[0.035, 8, 8]} />
        <meshStandardMaterial color="#ffffff" emissive={theme.secondaryAccent} emissiveIntensity={1.0} roughness={0.2} />
      </mesh>
      <mesh position={[0, 0.32, 0.28]} scale={[1.15, 1.15, 1.15]}>
        <sphereGeometry args={[0.035, 8, 8]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>

      {/* 2. Crossed arms / thick sleeve block in front */}
      <mesh position={[0, 0.52, 0.16]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.06, 0.06, 0.32, 8]} />
        <meshStandardMaterial color={robeColor} roughness={0.8} />
      </mesh>
      <mesh position={[0, 0.52, 0.16]} rotation={[0, 0, Math.PI / 2]} scale={[1.04, 1.04, 1.04]}>
        <cylinderGeometry args={[0.06, 0.06, 0.32, 8]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>

      {/* Sleeve Cuffs detailing matching player's primary accent */}
      <mesh position={[-0.14, 0.52, 0.16]} rotation={[0, Math.PI / 2, 0]}>
        <torusGeometry args={[0.062, 0.015, 6, 12]} />
        <meshStandardMaterial color={theme.primaryAccent} roughness={0.3} metalness={0.7} />
      </mesh>
      <mesh position={[0.14, 0.52, 0.16]} rotation={[0, Math.PI / 2, 0]}>
        <torusGeometry args={[0.062, 0.015, 6, 12]} />
        <meshStandardMaterial color={theme.primaryAccent} roughness={0.3} metalness={0.7} />
      </mesh>

      {/* 3. Cape over shoulders / Cowl Collar */}
      <mesh position={[0, 0.76, 0]}>
        <sphereGeometry args={[0.23, 16, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshStandardMaterial color={robeColor} roughness={0.8} />
      </mesh>
      <mesh position={[0, 0.76, 0]} scale={[1.04, 1.04, 1.04]}>
        <sphereGeometry args={[0.23, 16, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>

      {/* Decorative Golden/Colorful High-Priest Neck Ring / Collar */}
      <mesh position={[0, 0.78, 0]} rotation={[Math.PI / 2 + 0.1, 0, 0]}>
        <torusGeometry args={[0.22, 0.018, 8, 24]} />
        <meshStandardMaterial color={theme.primaryAccent} metalness={0.8} roughness={0.2} />
      </mesh>
      <mesh position={[0, 0.78, 0]} rotation={[Math.PI / 2 + 0.1, 0, 0]} scale={[1.04, 1.04, 1.04]}>
        <torusGeometry args={[0.22, 0.018, 8, 24]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>

      {/* 4. Head/Black Void face inside the cowl */}
      <mesh position={[0, 0.98, 0.03]}>
        <sphereGeometry args={[0.16, 16, 16]} />
        <meshStandardMaterial color="#040405" roughness={0.95} />
      </mesh>

      {/* Animated Floating Magic Core Jewel (Spins in front of chest) */}
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

      {/* 6. Cowl / Hood shell surrounding head with custom inner lining color */}
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

      {/* Contrast Edge Trim wrapping the cowl face opening */}
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

// Seat pillar representing each player spot
interface SpeakerPillarProps {
  id: number;
  name: string;
  isAlive: boolean;
  isUser: boolean;
  isSpeaking: boolean;
  angle: number;
}

function SpeakerSeat({ id, name, isAlive, isUser, isSpeaking, angle }: SpeakerPillarProps) {
  const setupCount = useGameStore((state) => state.setupCount);
  const statePlayersCount = useGameStore((state) => state.state?.players?.length) || 0;
  const playersCount = setupCount !== null ? setupCount : (statePlayersCount || 6);
  const radius = Math.max(5, playersCount * 0.72);
  const x = Math.sin(angle) * radius;
  const z = Math.cos(angle) * radius;

  // Track hover/bounce action on active speaking
  const ref = useRef<THREE.Group>(null);
  useFrame((state) => {
    if (ref.current) {
      if (isSpeaking) {
        // Levitate and rotate active card
        ref.current.position.y = 1.2 + Math.sin(state.clock.getElapsedTime() * 4) * 0.15;
        ref.current.rotation.y += 0.02;
      } else {
        // Chill breathing cycle
        ref.current.position.y = 1.0 + Math.sin(state.clock.getElapsedTime() * 1.5 + id) * 0.05;
        ref.current.rotation.y = angle + Math.PI; // look inwards
      }
    }
  });

  // Base rock colors: high contrast grayscale with rough borders
  const stoneColor = isAlive ? "#262626" : "#0d0d0d";
  const neonGlowColor = isSpeaking 
    ? "#3be8b0" // fluorescent green speak glow
    : isUser
      ? "#a855f7" // purple user accent
      : "#3b0764";

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

      {/* Heavy ink outline wireframe effect */}
      <mesh position={[0, 0.5, 0]}>
        <cylinderGeometry args={[0.61, 0.71, 1.21, 6]} />
        <meshBasicMaterial color="#000000" wireframe />
      </mesh>

      {/* Floating 3D Hooded Figure / Soul Sign of Life */}
      <group ref={ref}>
        {isAlive ? (
          <>
            <HoodedFigure
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

// Floating magical elements/embers colored by day/night setting
function MagicalSparks({ isNight }: { isNight: boolean }) {
  const pointsRef = useRef<THREE.Points>(null);
  const count = 75;
  const positions = React.useMemo(() => {
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 12; // X
      pos[i * 3 + 1] = Math.random() * 8; // Y
      pos[i * 3 + 2] = (Math.random() - 0.5) * 12; // Z
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
        // Float upward with subtle speed
        y += 0.02 + Math.sin(time + i) * 0.005;
        if (y > 7.5) {
          y = -0.5; // Recycle from bottom
        }
        posAttr.setY(i, y);

        // Gentle drift sideways
        let x = posAttr.getX(i);
        x += Math.sin(time * 0.3 + i) * 0.008;
        posAttr.setX(i, x);
      }
      posAttr.needsUpdate = true;
    }
  });

  const sparkColor = isNight ? "#c084fc" : "#ff781f"; // Magic Purple is Night, Hot Orange is Day!

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

// Glowing, rotating central core with pulsating light energy
function CentralEnergyOrb({ isNight }: { isNight: boolean }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const lightRef = useRef<THREE.PointLight>(null);

  useFrame((state) => {
    const time = state.clock.getElapsedTime();
    if (meshRef.current) {
      meshRef.current.rotation.x = time * 0.4;
      meshRef.current.rotation.y = time * 0.7;
      // Pulse slightly
      const scale = 1.0 + Math.sin(time * 3.5) * 0.12;
      meshRef.current.scale.set(scale, scale, scale);
    }
    if (lightRef.current) {
      // Extremely active glow pulsation
      lightRef.current.intensity = (isNight ? 14.0 : 9.0) + Math.sin(time * 5) * 3.0;
    }
  });

  const lightColorDef = isNight ? "#d946ef" : "#ff6a00";      // Amethyst Purple vs Lava Orange!
  const matColorDef = isNight ? "#8b5cf6" : "#ea580c";        // Velvet Purple vs Hot Orange!
  const emissiveColorDef = isNight ? "#f472b6" : "#fbbf24";   // Luminous Magenta vs Solar gold!

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
  const phase = useGameStore((state) => state.state?.phase);
  const currentSpeakerId = useGameStore((state) => state.state?.currentSpeakerId);
  const players = useGameStore((state) => state.state?.players || []);
  const setupCount = useGameStore((state) => state.setupCount);

  // Toggle ambient environment coloring depending on transition between day and night
  const isNight = phase?.startsWith("NIGHT");
  const fogColor = isNight ? "#0d0415" : "#1e0b02"; // Mystical deep purple mist vs Burning Terracotta gold-orange dust!
  const lightColor = isNight ? "#7c3aed" : "#ea580c"; // Deep neon amethyst ambient vs Intense sunburst orange-gold ambient!
  const ambientIntensity = isNight ? 0.15 : 0.38; // fine-tuned to make selective beams pop beautifully!

  // Dynamic preview array of seats during START_SCREEN configuration
  const previewPlayers = React.useMemo(() => {
    if (phase === "START_SCREEN" && setupCount !== null) {
      return Array.from({ length: setupCount }, (_, idx) => ({
        id: idx + 1,
        name: `席位 ${idx + 1}`,
        isAlive: true,
        isUser: idx === 0,
        isSpeaking: false,
      }));
    }
    return players.map((p) => ({
      id: p.id,
      name: p.name,
      isAlive: p.isAlive,
      isUser: p.isUser,
      isSpeaking: currentSpeakerId === p.id,
    }));
  }, [phase, setupCount, players, currentSpeakerId]);

  // Compute position of active speaker to focus dramatic lighting on them
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
            intensity={isNight ? 32.0 : 25.0} // Dynamic high power themed beam
            color={isNight ? "#d946ef" : "#ff6a00"} // Royal Purple vs Blazing sunset orange
            castShadow
            shadow-mapSize-width={512}
            shadow-mapSize-height={512}
          />
          {/* Neon secondary light aura on the hooded figure */}
          <pointLight
            position={[sX, 1.8, sZ]}
            intensity={6.0}
            distance={6}
            color={isNight ? "#a855f7" : "#ff781f"} // Neon amethyst purple vs Solar fire orange
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
        camera={{ position: [0, 8.5, 12.0], fov: 45 }}
        style={{ pointerEvents: "auto" }}
      >
        <color attach="background" args={[fogColor]} />
        <fog attach="fog" args={[fogColor, 10, 24]} />

        {/* Cinematic Gothic Lights */}
        <ambientLight intensity={ambientIntensity} color={lightColor} />

        {/* Floating Sparks in the atmospheric space */}
        <MagicalSparks isNight={isNight} />

        {/* Day Mode Sunlight / Night Mode Bloodmoon Beam */}
        {isNight ? (
          <directionalLight
            position={[-10, 14, -5]}
            intensity={4.5}
            color="#d946ef" // Deep Purple moonray
            castShadow
            shadow-mapSize-width={1024}
            shadow-mapSize-height={1024}
          />
        ) : (
          <directionalLight
            position={[10, 15, 5]}
            intensity={5.5}
            color="#ff6a00" // Day mode fire orange sunray
            castShadow
            shadow-mapSize-width={1024}
            shadow-mapSize-height={1024}
          />
        )}

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
                  <meshStandardMaterial
                    color="#0e0c12"
                    roughness={0.8}
                    metalness={0.2}
                  />
                </mesh>
                
                {/* Black outlining ring */}
                <mesh position={[0, 0.2, 0]}>
                  <cylinderGeometry args={[tableRadius + 0.01, tableRadius + 0.21, 0.41, 64]} />
                  <meshBasicMaterial color="#000000" wireframe />
                </mesh>

                {/* Central Trial sigil / Magic trial floor decals */}
                <TrialSigil tableRadius={tableRadius} />
              </>
            );
          })()}

          {/* Central neon glowing magical orb of judgement */}
          <CentralEnergyOrb isNight={isNight} />

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
                angle={angle}
              />
            );
          })}
        </group>

        {/* Smooth camera interpolation assistant */}
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
