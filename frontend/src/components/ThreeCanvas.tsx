import React, { useRef, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import * as THREE from "three";
import { useGameStore } from "../store";

function EnvironmentController({ isNight, isMurderAlert }: { isNight: boolean, isMurderAlert?: boolean }) {
  const { scene } = useThree();
  
  const theme = React.useMemo(() => {
     const bg = isMurderAlert ? "#2a0404" : isNight ? "#0d0415" : "#1e0b02";
     const ambientColor = isMurderAlert ? "#ff1100" : isNight ? "#7c3aed" : "#ea580c";
     const ambientIntensity = isMurderAlert ? 0.8 : isNight ? 0.15 : 0.38;
     const dirColor = isMurderAlert ? "#dc2626" : isNight ? "#d946ef" : "#ff6a00";
     const dirPos = isNight ? new THREE.Vector3(-10, 14, -5) : new THREE.Vector3(10, 15, 5);
     const dirIntensity = isNight ? 4.5 : 5.5;

     return {
       bg: new THREE.Color(bg),
       ambientColor: new THREE.Color(ambientColor),
       ambientIntensity,
       dirColor: new THREE.Color(dirColor),
       dirPos,
       dirIntensity
     };
  }, [isNight, isMurderAlert]);

  const ambientRef = useRef<THREE.AmbientLight>(null);
  const dirRef = useRef<THREE.DirectionalLight>(null);

  useEffect(() => {
    scene.fog = new THREE.Fog(theme.bg, 10, 30);
    scene.background = theme.bg.clone();
    return () => {
      scene.fog = null;
      scene.background = null;
    };
  }, [scene]);

  useFrame((state, delta) => {
    const s = 1 - Math.exp(-3 * delta); // Smooth framerate independent decay

    // Background & Fog Lerp
    if (scene.background instanceof THREE.Color) {
      scene.background.lerp(theme.bg, s);
    }
    if (scene.fog && 'color' in scene.fog) {
      (scene.fog as THREE.Fog).color.lerp(theme.bg, s);
    }

    // Ambient Light Lerp
    if (ambientRef.current) {
      ambientRef.current.color.lerp(theme.ambientColor, s);
      ambientRef.current.intensity = THREE.MathUtils.lerp(ambientRef.current.intensity, theme.ambientIntensity, s);
    }

    // Directional Light Lerp
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
      />
    </>
  );
}
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
        const total = Math.max(1, players.length);
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
    // MathUtils.damp parameters: (current, target, lambda, dt)
    // lambda: smoothing factor (higher = faster)
    const dampingSpeedPos = 3.5;
    const dampingSpeedLookAt = 4.0;
    
    if (phase === "START_SCREEN") {
      // Background orbital slow rotation motion
      const time = state.clock.getElapsedTime();
      const orbitSpeed = 0.08;
      const pCount = setupCount !== null ? setupCount : (players.length || 6);
      const radius = Math.max(5, pCount * 0.72);
      const orbitRadius = radius * 3.4; // majestic outer distance

      const x = Math.sin(time * orbitSpeed) * orbitRadius;
      const z = Math.cos(time * orbitSpeed) * orbitRadius;

      targetCamPos.current.set(x, radius * 1.6, z);
      
      // Calculate a local left-offset target based on camera vector 
      // so the table visually shifts to the right of the screen
      const dirVec = new THREE.Vector3().subVectors(new THREE.Vector3(0, 0.4, 0), targetCamPos.current).normalize();
      const upVec = new THREE.Vector3(0, 1, 0);
      const rightVec = new THREE.Vector3().crossVectors(dirVec, upVec).normalize();
      
      // Shift lookTarget slightly to the local left (which moves the visual center to the right)
      // Use window.innerWidth to scale the offset roughly. If width < height, no offset.
      let offsetScale = 0;
      if (typeof window !== 'undefined' && window.innerWidth > window.innerHeight) {
        offsetScale = radius * 0.8;
      }
      
      const lookTarget = new THREE.Vector3(0, 0.4, 0).add(rightVec.multiplyScalar(-offsetScale));
      targetLookAt.current.copy(lookTarget);
    } 

    // Smoothly step position frame-rate independently
    camera.position.x = THREE.MathUtils.damp(camera.position.x, targetCamPos.current.x, dampingSpeedPos, delta);
    camera.position.y = THREE.MathUtils.damp(camera.position.y, targetCamPos.current.y, dampingSpeedPos, delta);
    camera.position.z = THREE.MathUtils.damp(camera.position.z, targetCamPos.current.z, dampingSpeedPos, delta);

    // Smoothly step lookAt coordinate
    currentLookAt.current.x = THREE.MathUtils.damp(currentLookAt.current.x, targetLookAt.current.x, dampingSpeedLookAt, delta);
    currentLookAt.current.y = THREE.MathUtils.damp(currentLookAt.current.y, targetLookAt.current.y, dampingSpeedLookAt, delta);
    currentLookAt.current.z = THREE.MathUtils.damp(currentLookAt.current.z, targetLookAt.current.z, dampingSpeedLookAt, delta);
    
    camera.lookAt(currentLookAt.current);
  });

  return null;
}

// Procedural texture for the trial array magic circle
interface TrialSigilProps {
  tableRadius: number;
  isNight: boolean;
  isMurderAlert?: boolean;
}

function TrialSigil({ tableRadius, isNight, isMurderAlert }: TrialSigilProps) {
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
      ctx.fillStyle = "#050308";
      ctx.fillRect(0, 0, 512, 512);

      // Heavy hand-drawn outlines
      ctx.strokeStyle = isMurderAlert ? "#ef4444" : (isNight ? "#c084fc" : "#fbbf24"); // bright red or bright purple vs bright gold
      ctx.shadowColor = isMurderAlert ? "#dc2626" : (isNight ? "#a855f7" : "#d97706");
      ctx.shadowBlur = 15;
      ctx.lineWidth = 6;

      // Outer trial boundaries
      ctx.beginPath();
      ctx.arc(256, 256, 220, 0, Math.PI * 2);
      ctx.stroke();

      ctx.strokeStyle = isMurderAlert ? "#991b1b" : (isNight ? "#4c1d95" : "#92400e");
      ctx.lineWidth = 14;
      ctx.shadowBlur = 0;
      ctx.beginPath();
      ctx.arc(256, 256, 240, 0, Math.PI * 2);
      ctx.stroke();

      // Double ring inner border
      ctx.strokeStyle = isMurderAlert ? "#fca5a5" : (isNight ? "#f472b6" : "#fef08a"); // light red/pink vs light yellow
      ctx.shadowColor = isMurderAlert ? "#ef4444" : (isNight ? "#ec4899" : "#facc15");
      ctx.shadowBlur = 12;
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.arc(256, 256, 170, 0, Math.PI * 2);
      ctx.stroke();

      // Star of David / Hexagram trial pattern
      ctx.strokeStyle = isMurderAlert ? "#ef4444" : (isNight ? "#d946ef" : "#f59e0b");
      ctx.lineWidth = 5;
      ctx.shadowColor = isMurderAlert ? "#ef4444" : (isNight ? "#d946ef" : "#f59e0b");
      ctx.shadowBlur = 20;

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
      ctx.fillStyle = isMurderAlert ? "#fee2e2" : (isNight ? "#fde047" : "#ffedd5"); // neon yellow glow vs white-gold
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

// High quality Chess Piece component to render instead of the hooded figure
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
    // Base
    pts.push(new THREE.Vector2(0.001, 0));
    for (let i = 0; i <= 5; i++) {
      pts.push(new THREE.Vector2(0.4 + Math.cos((Math.PI / 2) * (i / 5)) * 0.03 - 0.03, 0.04 * (i / 5)));
    }
    pts.push(new THREE.Vector2(0.4, 0.08));
    pts.push(new THREE.Vector2(0.32, 0.15));
    pts.push(new THREE.Vector2(0.32, 0.2));
    pts.push(new THREE.Vector2(0.24, 0.25));
    
    // Stem
    pts.push(new THREE.Vector2(0.2, 0.4));
    pts.push(new THREE.Vector2(0.16, 0.6));
    pts.push(new THREE.Vector2(0.16, 0.7));
    
    // Collar
    pts.push(new THREE.Vector2(0.26, 0.75));
    pts.push(new THREE.Vector2(0.26, 0.82));
    pts.push(new THREE.Vector2(0.14, 0.86));
    
    // Head Sphere
    for (let i = 0; i <= 16; i++) {
      const a = -Math.PI / 2 + (i / 16) * Math.PI;
      const x = Math.max(0.001, Math.cos(a) * 0.22);
      pts.push(new THREE.Vector2(x, 1.08 + Math.sin(a) * 0.22));
    }
    
    // Finial (crown/nub)
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
function MagicalSparks({ isNight, isMurderAlert }: { isNight: boolean, isMurderAlert?: boolean }) {
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

  const targetColor = React.useMemo(() => new THREE.Color(isMurderAlert ? "#ef4444" : (isNight ? "#c084fc" : "#ff781f")), [isNight, isMurderAlert]);
  const matRef = useRef<THREE.PointsMaterial>(null);

  useFrame((state, delta) => {
    if (pointsRef.current) {
      const geo = pointsRef.current.geometry;
      const posAttr = geo.attributes.position as THREE.BufferAttribute;
      const time = state.clock.getElapsedTime();
      for (let i = 0; i < count; i++) {
        let y = posAttr.getY(i);
        // Float upward with subtle speed
        y += delta * 1.5 + Math.sin(time + i) * delta * 0.5;
        if (y > 7.5) {
          y = -0.5; // Recycle from bottom
        }
        posAttr.setY(i, y);

        // Gentle drift sideways
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
    const s = 1 - Math.exp(-3 * delta); // Smooth lerp
    if (meshRef.current) {
      meshRef.current.rotation.x = time * 0.4;
      meshRef.current.rotation.y = time * 0.7;
      // Pulse slightly
      const scale = 1.0 + Math.sin(time * 3.5) * 0.12;
      meshRef.current.scale.set(scale, scale, scale);
    }
    if (lightRef.current) {
      // Extremely active glow pulsation combined with lerp
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

  // Track the most recent "isNight" from the server logs to correctly reflect narrative state
  const lastLogIsNight = gameState?.speechLogs?.[gameState.speechLogs.length - 1]?.isNight;
  // Toggle ambient environment coloring depending on transition between day and night
  const isNight = phase?.startsWith("NIGHT") || lastLogIsNight || false;
  const isMurderAlert = phase === "DAY_ANNOUNCEMENT" && victimId !== null && victimId !== undefined;
  
  const fogColor = isMurderAlert ? "#2a0404" : isNight ? "#0d0415" : "#1e0b02"; // Mystical deep purple mist vs Burning Terracotta gold-orange dust!
  const lightColor = isMurderAlert ? "#ff1100" : isNight ? "#7c3aed" : "#ea580c"; // Deep neon amethyst ambient vs Intense sunburst orange-gold ambient!
  const ambientIntensity = isMurderAlert ? 0.8 : isNight ? 0.15 : 0.38; // fine-tuned to make selective beams pop beautifully!

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
        <EnvironmentController isNight={isNight} isMurderAlert={isMurderAlert} />

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
