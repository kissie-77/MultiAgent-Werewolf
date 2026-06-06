import React, { useEffect, useState } from "react";
import { useGameStore } from "../store";
import { motion, AnimatePresence } from "motion/react";
import { Sparkles, Eye, Skull, Flame, Crosshair, HelpCircle, ShieldAlert } from "lucide-react";
import { getRoleImage } from "../utils/roles";
import {
  playInspectSFX,
  playHealSFX,
  playPoisonSFX,
  playBiteSFX,
  playShootSFX,
  playVoteSFX
} from "../utils/audio";

export default function CastSkillOverlay() {
  const activeCast = useGameStore((state) => state.activeCast);
  const clearCast = useGameStore((state) => state.clearCast);
  const [particleList, setParticleList] = useState<{ id: number; x: number; y: number; speed: number; size: number }[]>([]);

  // Trigger audio on cast update
  useEffect(() => {
    if (!activeCast) return;
    
    // Play SFX matching effect type
    switch (activeCast.effectType) {
      case "inspect":
        playInspectSFX();
        break;
      case "heal":
        playHealSFX();
        break;
      case "poison":
        playPoisonSFX();
        break;
      case "bite":
        playBiteSFX();
        break;
      case "shoot":
        playShootSFX();
        break;
      case "vote":
      case "rally":
        playVoteSFX();
        break;
    }

    // Auto generate floating particle details
    const list = Array.from({ length: 25 }).map((_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100 + 50,
      speed: Math.random() * 3 + 1,
      size: Math.random() * 6 + 2
    }));
    setParticleList(list);

    // Auto clear overlay after animation finishes (approx 2.5s)
    const timer = setTimeout(() => {
      clearCast?.();
    }, 2500);

    return () => clearTimeout(timer);
  }, [activeCast, clearCast]);

  if (!activeCast) return null;

  const { role, skillName, skillSub, casterName, targetName, effectType, targetId } = activeCast;

  // Decide colors and visual attributes depending on skill cast type
  const getThemeConfig = () => {
    switch (effectType) {
      case "inspect":
        return {
          glow: "shadow-[0_0_80px_rgba(168,85,247,0.4)]",
          border: "border-purple-500/50",
          particleColor: "bg-purple-400",
          textColor: "text-purple-400",
          bannerBg: "bg-gradient-to-r from-purple-950/85 via-[#181030]/90 to-purple-950/85",
          accentColor: "#a855f7",
          titleIcon: Eye
        };
      case "heal":
        return {
          glow: "shadow-[0_0_80px_rgba(244,63,94,0.4)]",
          border: "border-rose-500/50",
          particleColor: "bg-rose-400",
          textColor: "text-rose-400",
          bannerBg: "bg-gradient-to-r from-rose-950/85 via-[#25101a]/90 to-rose-950/85",
          accentColor: "#f43f5e",
          titleIcon: Sparkles
        };
      case "poison":
        return {
          glow: "shadow-[0_0_80px_rgba(16,185,129,0.4)]",
          border: "border-emerald-500/50",
          particleColor: "bg-emerald-400",
          textColor: "text-emerald-400",
          bannerBg: "bg-gradient-to-r from-emerald-950/85 via-[#0e1c15]/90 to-emerald-950/85",
          accentColor: "#10b981",
          titleIcon: Skull
        };
      case "bite":
        return {
          glow: "shadow-[0_0_80px_rgba(239,68,68,0.5)]",
          border: "border-red-600/70",
          particleColor: "bg-red-500",
          textColor: "text-red-500",
          bannerBg: "bg-gradient-to-r from-red-950/85 via-[#200505]/95 to-red-950/85",
          accentColor: "#ef4444",
          titleIcon: Flame
        };
      case "shoot":
        return {
          glow: "shadow-[0_0_80px_rgba(234,179,8,0.4)]",
          border: "border-yellow-500/50",
          particleColor: "bg-yellow-400",
          textColor: "text-yellow-400",
          bannerBg: "bg-gradient-to-r from-yellow-950/85 via-[#231505]/90 to-yellow-950/85",
          accentColor: "#eab308",
          titleIcon: Crosshair
        };
      default:
        // Vote or generic
        return {
          glow: "shadow-[0_0_80px_rgba(59,130,246,0.3)]",
          border: "border-blue-500/50",
          particleColor: "bg-blue-400",
          textColor: "text-blue-400",
          bannerBg: "bg-gradient-to-r from-blue-950/85 via-[#09152a]/90 to-blue-950/85",
          accentColor: "#3b82f6",
          titleIcon: HelpCircle
        };
    }
  };

  const theme = getThemeConfig();
  const TitleIconComp = theme.titleIcon;

  // Extremely beautiful custom SVGs mirroring the requested illustration gothic designs
  const renderIllustrationCard = () => {
    switch (role) {
      case "预言家":
        return (
          <svg viewBox="0 0 450 600" className="w-full h-full max-h-[460px] bg-[#07050a] rounded-lg shadow-2xl" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Background elements - star orbits and constellation markers */}
            <circle cx="225" cy="225" r="180" stroke="#4a2082" strokeWidth="1.5" strokeDasharray="6 6" className="animate-spin" style={{ transformOrigin: "225px 225px", animationDuration: "35s" }} />
            <circle cx="225" cy="225" r="140" stroke="#311058" strokeWidth="2" strokeDasharray="14 4" className="animate-spin" style={{ transformOrigin: "225px 225px", animationDuration: "18s" }} />
            <path d="M 45 225 L 405 225 M 225 45 L 225 405" stroke="#4a2082" strokeWidth="0.5" opacity="0.4" />
            
            {/* Runes / cards layout */}
            <g opacity="0.3" stroke="#a855f7" strokeWidth="1">
              <rect x="30" y="50" width="40" height="60" rx="2" />
              <rect x="380" y="50" width="40" height="60" rx="2" />
              <rect x="380" y="340" width="40" height="60" rx="2" />
              <circle cx="50" cy="80" r="10" />
              <circle cx="400" cy="80" r="10" />
            </g>

            {/* Glowing violet background fog */}
            <defs>
              <radialGradient id="purpleGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.45" />
                <stop offset="100%" stopColor="#07050a" stopOpacity="0" />
              </radialGradient>
            </defs>
            <rect x="0" y="0" width="450" height="600" fill="url(#purpleGlow)" />

            {/* The Outer Frame with fine woodcut grid texture */}
            <rect x="15" y="15" width="420" height="570" rx="6" stroke="#a855f7" strokeWidth="4" />
            <rect x="22" y="22" width="406" height="556" rx="4" stroke="#ffffff" strokeWidth="1" strokeDasharray="4 4" opacity="0.3" />

            {/* Hooded Seer in center */}
            {/* Body robes */}
            <path d="M 90 540 C 90 420 150 250 225 250 C 300 250 360 420 360 540 Z" fill="#0c0714" stroke="#581c87" strokeWidth="3" />
            <path d="M 130 540 C 140 460 170 330 225 330 C 280 330 310 460 320 540 Z" fill="#040207" stroke="#2e104e" strokeWidth="1.5" />
            
            {/* Hood shroud */}
            <path d="M 225 100 C 150 100 135 180 135 240 C 135 300 155 310 165 310 Q 225 210 225 210 Q 225 210 285 310 C 295 310 315 300 315 240 C 315 180 300 100 225 100 Z" fill="#140c24" stroke="#c084fc" strokeWidth="3" />
            {/* Absolute black face shadow */}
            <path d="M 225 140 C 175 140 165 190 165 240 C 165 270 185 285 225 240 C 265 285 285 270 285 240 C 285 190 275 140 225 140 Z" fill="#000000" />
            
            {/* The Third Eye Symbol on Hood */}
            <path d="M 195 185 Q 225 165 255 185 Q 225 205 195 185 Z" fill="#030008" stroke="#a855f7" strokeWidth="2.5" />
            <circle cx="225" cy="185" r="6" fill="#c084fc" className="animate-pulse" />
            <path d="M 225 167 L 225 155 M 205 170 L 195 160 M 245 170 L 255 160 M 225 203 L 225 215" stroke="#a855f7" strokeWidth="1.5" />

            {/* Glowing mystic crystal ball on stone altar */}
            {/* Altar */}
            <path d="M 170 540 L 190 410 L 260 410 L 280 540 Z" fill="#1c1917" stroke="#44403c" strokeWidth="3" />
            <path d="M 150 540 H 300 V 570 H 150 Z" fill="#0c0a09" stroke="#292524" strokeWidth="2" />
            <circle cx="225" cy="410" r="48" fill="#581c87" fillOpacity="0.8" stroke="#c084fc" strokeWidth="4" />
            
            {/* Inside Crystal Ball: Moon and howling wolf graphic */}
            <ellipse cx="225" cy="410" rx="35" ry="35" fill="#311058" />
            {/* Little Moon Inside */}
            <circle cx="245" cy="395" r="12" fill="#c084fc" filter="drop-shadow(0 0 10px #c084fc)" />
            {/* Wolf Shadow */}
            <path d="M 215 440 C 215 420 225 410 230 405 L 235 410 L 238 402 L 243 415 L 248 425 H 215 Z" fill="#07050a" />

            {/* Crystal reflection line */}
            <path d="M 195 385 C 205 375 220 370 235 375" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" opacity="0.6" />
            
            {/* Spell card text at bottom */}
            <text x="225" y="555" fill="#c084fc" fontSize="24" fontWeight="900" fontFamily="sans-serif" textAnchor="middle" letterSpacing="6">预言家</text>
            <text x="225" y="575" fill="#e2e8f0" fontSize="10" fontWeight="bold" fontFamily="monospace" textAnchor="middle" letterSpacing="3">SEER ∙ ILLUMINATION</text>
          </svg>
        );

      case "女巫":
        return (
          <svg viewBox="0 0 450 600" className="w-full h-full max-h-[460px] bg-[#050806] rounded-lg shadow-2xl" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <radialGradient id="greenGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#10b981" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#050806" stopOpacity="0" />
              </radialGradient>
            </defs>
            <rect x="0" y="0" width="450" height="600" fill="url(#greenGlow)" />

            {/* Gothic frames */}
            <rect x="15" y="15" width="420" height="570" rx="6" stroke="#10b981" strokeWidth="4" />
            <rect x="22" y="22" width="406" height="556" rx="4" stroke="#ffffff" strokeWidth="1" strokeDasharray="3 3" opacity="0.2" />

            {/* Ravens and flasks in background */}
            <path d="M 30 180 C 40 170 60 175 70 190 C 60 200 45 195 30 180 Z" fill="#090d0b" stroke="#10b981" strokeWidth="1" />
            <path d="M 420 180 C 410 170 390 175 380 190 C 390 200 405 195 420 180 Z" fill="#090d0b" stroke="#10b981" strokeWidth="1" />
            
            {/* Distant alchemy bottles */}
            <rect x="40" y="320" width="25" height="40" rx="4" stroke="#047857" strokeWidth="1.5" fill="#022c22" />
            <line x1="52" y1="320" x2="52" y2="312" stroke="#047857" strokeWidth="2" />
            <rect x="385" y="320" width="25" height="40" rx="4" stroke="#047857" strokeWidth="1.5" fill="#022c22" />
            <line x1="397" y1="320" x2="397" y2="312" stroke="#047857" strokeWidth="2" />

            {/* Smirking Witch in pointed hat */}
            {/* Witch Robes */}
            <path d="M 80 540 C 90 410 150 240 225 240 C 300 240 360 410 360 540 Z" fill="#0d1f14" stroke="#065f46" strokeWidth="3.5" />
            <path d="M 120 540 C 135 440 170 320 225 320 C 280 320 315 440 330 540 Z" fill="#050a06" stroke="#042f1a" strokeWidth="2" />

            {/* Pointer Hat */}
            <path d="M 130 190 L 225 40 L 320 190 Z" fill="#090d0b" stroke="#10b981" strokeWidth="3" />
            <path d="M 90 190 Q 225 160 360 190 Q 225 220 90 190" fill="#111827" stroke="#10b981" strokeWidth="2" strokeLinejoin="round" />
            
            {/* Face and smirk shadow */}
            <path d="M 175 190 C 175 250 275 250 275 190 Z" fill="#1c0b2b" stroke="#10b981" strokeWidth="1" />
            <path d="M 200 220 Q 225 235 250 220" stroke="#f43f5e" strokeWidth="2.5" strokeLinecap="round" /> {/* Smirk lips */}
            
            {/* Green glowing Potion Flasks in hands (Antidote right, Poison left) */}
            {/* Left hands / Poison (Green) */}
            <g transform="translate(0, 0)">
              <circle cx="110" cy="360" r="30" fill="#064e3b" stroke="#10b981" strokeWidth="3.5" />
              <rect x="102" y="315" width="16" height="20" rx="2" fill="#042f1a" stroke="#10b981" strokeWidth="2" />
              {/* Green poison foam waves */}
              <path d="M 90 355 Q 110 335 130 355 Z" fill="#10b981" />
              <circle cx="100" cy="350" r="3" fill="#ffffff" />
              <circle cx="118" cy="345" r="2" fill="#ffffff" />
              <text x="110" y="394" fill="#059669" fontSize="9" fontWeight="900" fontFamily="sans-serif" textAnchor="middle">POISON</text>
            </g>

            {/* Right hands / Antidote (Rose/Purple) */}
            <g transform="translate(230, 0)">
              <circle cx="110" cy="360" r="30" fill="#4d0519" stroke="#f43f5e" strokeWidth="3.5" />
              <rect x="102" y="315" width="16" height="20" rx="2" fill="#310408" stroke="#f43f5e" strokeWidth="2" />
              {/* Rose glow foam */}
              <path d="M 90 355 Q 110 335 130 355 Z" fill="#f43f5e" />
              <circle cx="106" cy="348" r="3.5" fill="#ffffff" />
              <circle cx="114" cy="352" r="1.5" fill="#ffffff" />
              <text x="110" y="394" fill="#db2777" fontSize="9" fontWeight="900" fontFamily="sans-serif" textAnchor="middle">ANTIDOTE</text>
            </g>

            {/* Magic green & purple rising visual lines */}
            <path d="M 80 300 Q 60 240 100 200" stroke="#10b981" strokeWidth="2" opacity="0.5" strokeDasharray="5 5" className="animate-pulse" />
            <path d="M 370 300 Q 390 240 350 200" stroke="#f43f5e" strokeWidth="2" opacity="0.5" strokeDasharray="5 5" className="animate-pulse" />

            <text x="225" y="555" fill="#10b981" fontSize="24" fontWeight="900" fontFamily="sans-serif" textAnchor="middle" letterSpacing="6">女巫</text>
            <text x="225" y="575" fill="#e2e8f0" fontSize="10" fontWeight="bold" fontFamily="monospace" textAnchor="middle" letterSpacing="3">WITCH ∙ ELIXIR MIST</text>
          </svg>
        );

      case "猎人":
        return (
          <svg viewBox="0 0 450 600" className="w-full h-full max-h-[460px] bg-[#090705] rounded-lg shadow-2xl" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <radialGradient id="orangeGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#f97316" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#090705" stopOpacity="0" />
              </radialGradient>
            </defs>
            <rect x="0" y="0" width="450" height="600" fill="url(#orangeGlow)" />

            {/* Gothic frames */}
            <rect x="15" y="15" width="420" height="570" rx="6" stroke="#f97316" strokeWidth="4" />
            <rect x="22" y="22" width="406" height="556" rx="4" stroke="#ffffff" strokeWidth="1" strokeDasharray="3 3" opacity="0.2" />

            {/* Target Crosshairs in background */}
            <circle cx="70" cy="180" r="24" stroke="#ef4444" strokeWidth="1" strokeDasharray="4 2" />
            <line x1="70" y1="150" x2="70" y2="210" stroke="#ef4444" strokeWidth="1" />
            <line x1="40" y1="180" x2="100" y2="180" stroke="#ef4444" strokeWidth="1" />

            <circle cx="380" cy="180" r="24" stroke="#ef4444" strokeWidth="1" strokeDasharray="4 2" />
            <line x1="380" y1="150" x2="380" y2="210" stroke="#ef4444" strokeWidth="1" />
            <line x1="350" y1="180" x2="410" y2="180" stroke="#ef4444" strokeWidth="1" />

            {/* Forest elements of branches */}
            <path d="M 35 150 Q 80 90 20 20 M 15 110 Q 55 70 8 40" stroke="#451a03" strokeWidth="2.5" strokeLinecap="round" opacity="0.6" />
            <path d="M 415 150 Q 370 90 430 20 M 435 110 Q 395 70 442 40" stroke="#451a03" strokeWidth="2.5" strokeLinecap="round" opacity="0.6" />

            {/* Hunter under moon */}
            <circle cx="225" cy="180" r="60" fill="#fcfcfc" opacity="0.9" />
            <path d="M 215 140 C 215 143 218 145 225 145 C 232 145 235 143 235 140 Z" fill="#000000" />
            
            {/* Cowboy wide hat */}
            <path d="M 130 190 Q 225 148 320 190 L 305 198 H 145 Z" fill="#181411" stroke="#f97316" strokeWidth="3" />
            <path d="M 170 190 L 225 110 L 280 190 Z" fill="#1c140e" stroke="#3b2314" strokeWidth="1.5" />
            
            {/* Hunter Shadow body and gun */}
            <path d="M 90 540 C 100 420 145 250 225 250 C 305 250 350 420 360 540 Z" fill="#2d1508" stroke="#1c0f08" strokeWidth="3" />
            <path d="M 115 540 C 125 450 155 330 225 330 C 295 330 325 450 335 540 Z" fill="#0a0502" />

            {/* Glowing Orange Eyes beneath the hat shadow */}
            <ellipse cx="202" cy="225" rx="5" ry="3" fill="#f97316" />
            <circle cx="202" cy="225" r="1.5" fill="#ffffff" />
            <ellipse cx="248" cy="225" rx="5" ry="3" fill="#f97316" />
            <circle cx="248" cy="225" r="1.5" fill="#ffffff" />

            {/* Metallic Double-Barreled Shotgun Gun */}
            <g transform="translate(145, 340)">
              <rect x="0" y="10" width="160" height="15" fill="#3c3c3c" stroke="#f97316" strokeWidth="2.5" strokeLinejoin="round" />
              <line x1="0" y1="17.5" x2="160" y2="17.5" stroke="#1c1c1c" strokeWidth="1.5" />
              <rect x="15" y="25" width="45" height="18" rx="3" fill="#5c3a21" stroke="#3b2314" strokeWidth="2" /> {/* Stock grip */}
              <circle cx="140" cy="17.5" r="3" fill="#ef4444" /> {/* Gun site */}
            </g>

            {/* Falling bullets shells on bottom */}
            <rect x="50" y="520" width="8" height="18" rx="1" fill="#ca8a04" transform="rotate(25 50 520)" stroke="#713f12" strokeWidth="1" />
            <rect x="390" y="520" width="8" height="18" rx="1" fill="#ca8a04" transform="rotate(-40 390 520)" stroke="#713f12" strokeWidth="1" />

            <text x="225" y="555" fill="#f97316" fontSize="24" fontWeight="900" fontFamily="sans-serif" textAnchor="middle" letterSpacing="6">猎人</text>
            <text x="225" y="575" fill="#e2e8f0" fontSize="10" fontWeight="bold" fontFamily="monospace" textAnchor="middle" letterSpacing="3">HUNTER ∙ STEEL BOLT</text>
          </svg>
        );

      case "狼人":
        return (
          <svg viewBox="0 0 450 600" className="w-full h-full max-h-[460px] bg-[#0d0303] rounded-lg shadow-2xl" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <radialGradient id="redGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#ef4444" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#0d0303" stopOpacity="0" />
              </radialGradient>
            </defs>
            <rect x="0" y="0" width="450" height="600" fill="url(#redGlow)" />

            {/* Gothic frames */}
            <rect x="15" y="15" width="420" height="570" rx="6" stroke="#ef4444" strokeWidth="4" />
            <rect x="22" y="22" width="406" height="556" rx="4" stroke="#ffffff" strokeWidth="1" strokeDasharray="3 3" opacity="0.2" />

            {/* Large full moon background */}
            <circle cx="225" cy="180" r="95" fill="#f8fafc" />
            <circle cx="170" cy="130" r="14" fill="#e2e8f0" />
            <circle cx="280" cy="140" r="18" fill="#e2e8f0" />
            <circle cx="250" cy="220" r="10" fill="#e2e8f0" />

            {/* Wolf howling pack silhouettes */}
            <path d="M 40 280 L 70 250 H 90 L 80 280 L 110 260 L 120 280 H 40 Z" fill="#2d0606" stroke="#ef4444" strokeWidth="1" />
            <path d="M 410 280 L 380 250 H 360 L 370 280 L 340 260 L 330 280 H 410 Z" fill="#2d0606" stroke="#ef4444" strokeWidth="1" />

            {/* Thorns and Red splatters framing */}
            <path d="M 15 15 L 435 585 M 435 15 L 15 585" stroke="#7f1d1d" strokeWidth="1" opacity="0.2" />
            <path d="M 10 500 C 40 520 20 540 60 550" stroke="#ef4444" strokeWidth="3" strokeLinecap="round" />
            <path d="M 440 500 C 410 520 430 540 390 550" stroke="#ef4444" strokeWidth="3" strokeLinecap="round" />

            {/* Fierce Werewolf Silhouette */}
            {/* Shaggy Hairy wolf shoulders */}
            <path d="M 60 540 C 80 400 130 220 225 220 C 320 220 370 400 390 540 Z" fill="#1c0707" stroke="#7f1d1d" strokeWidth="4" />
            <path d="M 110 540 C 130 430 165 310 225 310 C 285 310 320 430 340 540 Z" fill="#000000" />
            
            {/* Shaggy head cowl hood */}
            <path d="M 225 150 C 170 150 155 210 155 250 C 155 290 175 320 225 320 C 275 320 295 290 295 250 C 295 210 280 150 225 150 Z" fill="#0a0202" stroke="#ef4444" strokeWidth="2" />
            
            {/* Glowing Red Eyes with slash lights */}
            <polygon points="185,225 205,215 215,228 195,235" fill="#f43f5e" filter="drop-shadow(0 0 8px #f43f5e)" />
            <polygon points="265,225 245,215 235,228 255,235" fill="#f43f5e" filter="drop-shadow(0 0 8px #f43f5e)" />

            {/* Werewolf Fangs jaws */}
            <path d="M 195 260 L 225 275 L 255 260 L 225 250 L 195 260 Z" fill="#180202" stroke="#ef4444" strokeWidth="1.5" />
            {/* Sharp white/red fangs */}
            <path d="M 205 256 L 210 264 L 215 255 L 220 264 L 225 255 L 230 264 L 235 255 L 240 264 L 245 256" stroke="#fcfcfc" strokeWidth="2" strokeLinecap="round" />

            {/* Large Red scratch wounds on visual */}
            <line x1="30" y1="50" x2="110" y2="130" stroke="#f43f5e" strokeWidth="5.5" strokeLinecap="round" />
            <line x1="45" y1="40" x2="125" y2="120" stroke="#f43f5e" strokeWidth="5.5" strokeLinecap="round" />
            <line x1="60" y1="30" x2="140" y2="110" stroke="#f43f5e" strokeWidth="5.5" strokeLinecap="round" />

            <text x="225" y="555" fill="#ef4444" fontSize="24" fontWeight="900" fontFamily="sans-serif" textAnchor="middle" letterSpacing="6">狼人</text>
            <text x="225" y="575" fill="#e2e8f0" fontSize="10" fontWeight="bold" fontFamily="monospace" textAnchor="middle" letterSpacing="3">WEREWOLF ∙ BLOODLUST</text>
          </svg>
        );

      case "村民":
      default:
        return (
          <svg viewBox="0 0 450 600" className="w-full h-full max-h-[460px] bg-[#040608] rounded-lg shadow-2xl" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <radialGradient id="yellowGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#eab308" stopOpacity="0.45" />
                <stop offset="100%" stopColor="#040608" stopOpacity="0" />
              </radialGradient>
            </defs>
            <rect x="0" y="0" width="450" height="600" fill="url(#yellowGlow)" />

            {/* Gothic frames */}
            <rect x="15" y="15" width="420" height="570" rx="6" stroke="#eab308" strokeWidth="4" />
            <rect x="22" y="22" width="406" height="556" rx="4" stroke="#ffffff" strokeWidth="1" strokeDasharray="3 3" opacity="0.2" />

            {/* Ruined huts, towers and crows in gray background */}
            <path d="M 40 380 L 110 290 L 180 380 Z M 35 380 Q 110 320 185 380" fill="#1e1b18" stroke="#713f12" strokeWidth="2.5" />
            <path d="M 410 380 L 340 290 L 270 380 Z M 415 380 Q 340 320 265 380" fill="#1e1b18" stroke="#713f12" strokeWidth="2.5" />
            
            {/* Church Bell design */}
            <rect x="195" y="45" width="60" height="90" rx="4" fill="#090502" stroke="#eab308" strokeWidth="2" />
            <circle cx="225" cy="110" r="18" fill="#ca8a04" stroke="#fef08a" strokeWidth="2.5" />
            <path d="M 225 125 L 225 150" stroke="#eab308" strokeWidth="4" strokeLinecap="round" />

            {/* Villager Farmer cladding in hood holding lamp */}
            {/* Body */}
            <path d="M 90 540 C 90 420 145 280 225 280 C 305 280 360 420 360 540 Z" fill="#1c1917" stroke="#ca8a04" strokeWidth="3" />
            <path d="M 125 540 C 135 450 165 345 225 345 C 285 345 315 450 325 540 Z" fill="#0c0a09" />
            
            {/* Head cowl */}
            <path d="M 225 200 C 175 200 160 250 160 290 C 160 320 180 330 225 330 C 270 330 290 320 290 290 C 290 250 275 200 225 200 Z" fill="#292524" stroke="#ca8a04" strokeWidth="1.5" />
            {/* Blank scared yellow eyes */}
            <circle cx="202" cy="272" r="5" fill="#ca8a04" />
            <circle cx="202" cy="272" r="2" fill="#ffffff" />
            <circle cx="248" cy="272" r="5" fill="#ca8a04" />
            <circle cx="248" cy="272" r="2" fill="#ffffff" />

            {/* Highly shining golden vintage lantern in hands */}
            <g transform="translate(182, 360)">
              <rect x="0" y="30" width="86" height="110" rx="6" fill="#1e1b18" stroke="#eab308" strokeWidth="5" />
              <rect x="18" y="45" width="50" height="60" rx="3" fill="#fef08a" filter="drop-shadow(0 0 16px #eab308)" /> {/* Shining glowing center */}
              <rect x="18" y="45" width="50" height="60" rx="3" fill="#ffffff" stroke="#eab308" strokeWidth="1" />
              <path d="M 12 10 Q 43 0 74 10 L 86 35 H 0 Z" fill="#1c0e01" stroke="#eab308" strokeWidth="3" /> {/* Lid */}
              <circle cx="43" cy="75" r="14" fill="#fef08a" />
              {/* handle loop */}
              <path d="M 20 10 Q 43 -20 66 10" stroke="#ca8a04" strokeWidth="4.5" fill="none" />
            </g>

            {/* Rising plasma flame visuals around */}
            <path d="M 80 450 Q 50 380 90 330" stroke="#eab308" strokeWidth="3" strokeLinecap="round" opacity="0.65" />
            <path d="M 370 450 Q 400 380 360 330" stroke="#eab308" strokeWidth="3" strokeLinecap="round" opacity="0.65" />

            <text x="225" y="555" fill="#eab308" fontSize="24" fontWeight="900" fontFamily="sans-serif" textAnchor="middle" letterSpacing="6">村民</text>
            <text x="225" y="575" fill="#e2e8f0" fontSize="10" fontWeight="bold" fontFamily="monospace" textAnchor="middle" letterSpacing="3">VILLAGER ∙ PURE LIGHT</text>
          </svg>
        );
    }
  };

  return (
    <AnimatePresence>
      <div 
        className="fixed inset-0 z-[100] flex items-center justify-center bg-zinc-950/90 select-none cursor-pointer"
        onClick={() => clearCast?.()}
        id="cast-skill-screen-overlay"
      >
        {/* Particle Canvas ambient layer */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          {particleList.map((p) => (
            <motion.div
              key={p.id}
              className={`absolute rounded-full opacity-60 ${theme.particleColor} pointer-events-none`}
              style={{
                width: p.size,
                height: p.size,
                left: `${p.x}%`,
                bottom: `${p.y - 45}%`
              }}
              animate={{
                y: [0, -320],
                opacity: [0.7, 1, 0],
                scale: [1, 1.4, 0.4]
              }}
              transition={{
                duration: p.speed,
                repeat: Infinity,
                ease: "linear"
              }}
            />
          ))}
        </div>

        {/* Ambient colored flashes */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: [0.3, 0.8, 0.3] }}
          transition={{ duration: 1.2, repeat: Infinity }}
          className="absolute inset-0 pointer-events-none opacity-40"
          style={{
            background: `radial-gradient(circle, ${theme.accentColor}44 0%, transparent 70%)`
          }}
        />

        {/* Diagonal slashing strikes specifically for Werewolf */}
        {role === "狼人" && (
          <div className="absolute inset-0 flex flex-col justify-center items-center pointer-events-none overflow-hidden z-25">
            <motion.div 
              initial={{ scaleX: 0, opacity: 0, x: -300, y: -200 }}
              animate={{ scaleX: 1, opacity: [0, 1, 1, 0], x: 300, y: 200 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="w-[150%] h-4 bg-red-600 rotate-[35deg] blur-sm shrink-0"
            />
            <motion.div 
              initial={{ scaleX: 0, opacity: 0, x: 300, y: -200 }}
              animate={{ scaleX: 1, opacity: [0, 1, 1, 0], x: -300, y: 200 }}
              transition={{ duration: 0.5, delay: 0.15, ease: "easeOut" }}
              className="w-[150%] h-4 bg-red-600 rotate-[-35deg] blur-sm shrink-0"
            />
          </div>
        )}

        {/* Gunshot muzzle flash burst specifically for Hunter */}
        {role === "猎人" && (
          <motion.div
            initial={{ scale: 0.3, opacity: 0 }}
            animate={{ scale: [1, 15], opacity: [0, 1, 0] }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="absolute inset-0 pointer-events-none z-30 bg-radial from-amber-500 via-orange-950 to-transparent flex items-center justify-center rounded-full"
            style={{ width: 120, height: 120, left: "calc(50% - 60px)", top: "calc(50% - 60px)" }}
          />
        )}

        {/* Center alignment stack content */}
        <div className="flex flex-col items-center justify-center max-w-[90vw] gap-6 text-center select-none z-10 pointer-events-auto">
          {/* Casting prompt headers */}
          <div className="flex flex-col items-center gap-1">
            <span className="font-mono text-xs text-zinc-500 uppercase tracking-[4px]">
              🛡️ CASTING ACTION IN PROGRESS
            </span>
            <div className="flex items-center gap-2 mt-1">
              <span className="font-sans font-black text-sm uppercase text-zinc-200 tracking-[1.5px]">
                {casterName} 
              </span>
              <span className="px-1.5 py-0.5 rounded text-[8px] font-sans font-black border border-zinc-700 text-zinc-400 bg-zinc-900">
                {role}
              </span>
            </div>
          </div>

          {/* Big popping graphic illustration model with spring mechanics */}
          <motion.div
            initial={{ scale: 0.4, rotateY: 90, opacity: 0, y: 50 }}
            animate={{ scale: 1, rotateY: 0, opacity: 1, y: 0 }}
            exit={{ scale: 0.4, opacity: 0 }}
            transition={{ type: "spring", stiffness: 180, damping: 16 }}
            className={`w-[300px] sm:w-[340px] aspect-[1/1.6] relative rounded p-2.5 bg-[#0a0505] border ${theme.border} ${theme.glow} flex flex-col items-center justify-between shadow-[0_0_50px_rgba(0,0,0,0.8)] overflow-hidden`}
            style={{ perspective: 1000 }}
          >
            {/* Antique background texture layering */}
            <div className="absolute inset-0 bg-woodcut-dark opacity-40 pointer-events-none mix-blend-overlay" />
            <div className="absolute inset-0 bg-gradient-to-t from-black via-black/20 to-black/60 pointer-events-none" />

            {/* Inner Gold Foil Frame */}
            <div className="w-full h-full border border-amber-500/20 absolute inset-0 m-3 z-10 pointer-events-none rounded-sm">
                <div className="absolute top-0 left-0 w-8 h-8 border-t border-l border-amber-600/60 -ml-1 -mt-1" />
                <div className="absolute top-0 right-0 w-8 h-8 border-t border-r border-amber-600/60 -mr-1 -mt-1" />
                <div className="absolute bottom-0 left-0 w-8 h-8 border-b border-l border-amber-600/60 -ml-1 -mb-1" />
                <div className="absolute bottom-0 right-0 w-8 h-8 border-b border-r border-amber-600/60 -mr-1 -mb-1" />
            </div>

            <div className="relative z-0 w-full h-[65%] shrink-0 rounded overflow-hidden border-b border-amber-900/30">
              <img 
                src={getRoleImage(role)}
                alt={role}
                className="w-full h-full object-cover object-center filter contrast-125 saturate-50"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[#0a0505] via-transparent to-transparent" />
            </div>

            <div className="relative z-20 flex-grow flex flex-col items-center justify-center p-4 w-full">
               <div className="flex items-center gap-2 mb-2 opacity-60">
                 <div className="w-1.5 h-1.5 bg-amber-500/60 rotate-45" />
                 <span className="font-serif text-[10px] uppercase tracking-[0.2em] text-amber-500/80">
                   {skillSub || "ARCANA"}
                 </span>
                 <div className="w-1.5 h-1.5 bg-amber-500/60 rotate-45" />
               </div>
               
               <h2 className="font-serif text-3xl font-medium text-transparent bg-clip-text bg-gradient-to-b from-amber-100 via-amber-300 to-amber-700 tracking-[0.15em] drop-shadow-md mb-1" style={{textShadow: "0 2px 10px rgba(245, 158, 11, 0.3)"}}>
                 {skillName}
               </h2>
               
               <div className="flex items-center gap-1 opacity-40 mt-1">
                 <TitleIconComp className={`w-3.5 h-3.5 ${theme.textColor}`} />
                 <span className="font-sans text-[11px] tracking-widest uppercase" style={{ color: theme.accentColor }}>{role}</span>
               </div>
            </div>
          </motion.div>

          {/* Target locking details */}
          {targetName && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25, duration: 0.4 }}
              className={`px-8 py-3 rounded border border-zinc-800/80 w-auto ${theme.bannerBg} flex flex-col gap-1 shadow-2xl relative overflow-hidden backdrop-blur-md`}
            >
              {/* Symmetrical framing lines */}
              <div className="absolute top-0 inset-x-0 h-[1.5px] bg-gradient-to-r from-transparent via-zinc-400/30 to-transparent" />
              <div className="absolute bottom-0 inset-x-0 h-[1.5px] bg-gradient-to-r from-transparent via-zinc-400/30 to-transparent" />

              <div className="flex items-center justify-center gap-2">
                <span className="text-zinc-500 font-sans text-[10px] uppercase">
                  目标锁定:
                </span>
                <span className="font-sans font-black text-sm text-[#fef08a] px-2 py-0.5 bg-black/60 border border-yellow-500/20 rounded shadow-inner">
                  {targetName} ({targetId}号)
                </span>
              </div>
            </motion.div>
          )}

          {/* Quick exit guide prompt */}
          <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-[1.5px] cursor-pointer hover:text-zinc-400 transition-colors mt-2">
            点击任意区域或等待法阵消散收回卡牌...
          </span>
        </div>
      </div>
    </AnimatePresence>
  );
}
