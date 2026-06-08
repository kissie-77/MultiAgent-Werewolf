import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useGameStore } from "../store";
import { ApiClient } from "../api/client";
import { nearestStandardConfigId } from "../lib/boardConfig";
import { type BoardSetupMode } from "../components/BoardSetupPanel";
import {
  findPreset,
  roleDisplayName,
  standardLineupForCount,
  validateCustomLineup,
} from "../lib/roleCatalog";
import type { BoardPresetOption, PlayableRoleOption, AvailableModelOption } from "../api/types";
import { mapRunRow, type RunRow } from "../utils/runRows";

export function useGameSetup() {
  const setSetupCount = useGameStore((s) => s.setSetupCount);
  const setInsightEnabled = useGameStore((s) => s.setInsightEnabled);
  const navigate = useNavigate();

  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [setupStep, setSetupStep] = useState<"landing" | "settings">("landing");
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [gameMode, setGameMode] = useState<"llmOnly" | "humanVsAI">("humanVsAI");
  const [boardMode, setBoardMode] = useState<BoardSetupMode>("standard");
  const [boardPresets, setBoardPresets] = useState<BoardPresetOption[]>([]);
  const [playableRoles, setPlayableRoles] = useState<PlayableRoleOption[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState("preset-lovers-9");
  const [customLineup, setCustomLineup] = useState<string[]>(() => standardLineupForCount(6));
  const [presetsLoading, setPresetsLoading] = useState(false);
  const [playerCount, setPlayerCount] = useState(6);
  const [userRole, setUserRole] = useState("预言家");
  const [humanSeat, setHumanSeat] = useState(1);
  const [hasSheriff, setHasSheriff] = useState(true);
  const [enableDeepGame, setEnableDeepGame] = useState(true);
  const [customizeModels, setCustomizeModels] = useState(false);
  const [availableModels, setAvailableModels] = useState<AvailableModelOption[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [seatProviders, setSeatProviders] = useState<string[]>([]);
  const [spectatableRuns, setSpectatableRuns] = useState<RunRow[]>([]);
  const [spectateRunId, setSpectateRunId] = useState("");
  const [spectateRunsLoading, setSpectateRunsLoading] = useState(false);
  const [spectateRunsError, setSpectateRunsError] = useState<string | null>(null);

  const defaultProviderId =
    availableModels.find((m) => m.provider_id === "doubao")?.provider_id
    ?? availableModels[0]?.provider_id
    ?? "doubao";

  const activeLineup = (() => {
    if (boardMode === "custom") return customLineup;
    if (boardMode === "curated") {
      return findPreset(boardPresets, selectedPresetId)?.role_names ?? standardLineupForCount(6);
    }
    return standardLineupForCount(playerCount);
  })();

  const effectivePlayerCount = activeLineup.length;

  const lineupRoleOptions = (() => {
    const seen = new Set<string>();
    const opts: { key: string; label: string }[] = [];
    for (const key of activeLineup) {
      if (seen.has(key)) continue;
      seen.add(key);
      opts.push({ key, label: roleDisplayName(key, playableRoles) });
    }
    return opts;
  })();

  // Sync setup count to store
  useEffect(() => {
    setSetupCount(effectivePlayerCount);
  }, [effectivePlayerCount, setSetupCount]);

  // Clamp human seat within range
  useEffect(() => {
    setHumanSeat((seat) => Math.min(Math.max(1, seat), effectivePlayerCount));
  }, [effectivePlayerCount]);

  // Reset user role when lineup changes
  useEffect(() => {
    if (!lineupRoleOptions.length) return;
    setUserRole((prev) => {
      if (lineupRoleOptions.some((o) => o.label === prev)) return prev;
      return lineupRoleOptions[0].label;
    });
  }, [lineupRoleOptions]);

  // Cleanup setup count on unmount
  useEffect(() => {
    return () => setSetupCount(null);
  }, [setSetupCount]);

  // Fetch board presets when entering settings
  useEffect(() => {
    if (setupStep !== "settings") return;
    let cancelled = false;
    setPresetsLoading(true);
    ApiClient.getBoardPresets()
      .then((data) => {
        if (cancelled) return;
        setBoardPresets(data.presets);
        setPlayableRoles(data.roles);
        const curated = data.presets.find((p) => p.kind === "curated");
        if (curated) {
          setSelectedPresetId((prev) =>
            data.presets.some((p) => p.preset_id === prev && p.kind === "curated") ? prev : curated.preset_id
          );
        }
      })
      .catch(() => {
        if (!cancelled) { setBoardPresets([]); setPlayableRoles([]); }
      })
      .finally(() => !cancelled && setPresetsLoading(false));
    return () => { cancelled = true; };
  }, [setupStep]);

  // Fetch available models when entering settings
  useEffect(() => {
    if (setupStep !== "settings") return;
    let cancelled = false;
    setModelsLoading(true);
    ApiClient.getAvailableModels()
      .then((data) => {
        if (cancelled) return;
        setAvailableModels(data.models);
      })
      .catch(() => {
        if (!cancelled) setAvailableModels([]);
      })
      .finally(() => !cancelled && setModelsLoading(false));
    return () => { cancelled = true; };
  }, [setupStep]);

  // Sync seat providers array length
  useEffect(() => {
    setSeatProviders((prev) => {
      const next = Array.from({ length: effectivePlayerCount }, (_, i) => prev[i] ?? defaultProviderId);
      return next.length === effectivePlayerCount ? next : next.slice(0, effectivePlayerCount);
    });
  }, [effectivePlayerCount, defaultProviderId]);

  // Fetch spectatable runs for llmOnly mode
  useEffect(() => {
    if (setupStep !== "settings" || gameMode !== "llmOnly") return;
    let cancelled = false;
    setSpectateRunsLoading(true);
    ApiClient.getSpectatableRuns(1, 40)
      .then((data) => {
        if (cancelled) return;
        const rows = data.runs.items.map(mapRunRow).filter((r) => r.hasReplay);
        setSpectatableRuns(rows);
        setSpectateRunId((prev) => prev || rows[0]?.runId || "");
        setSpectateRunsError(null);
      })
      .catch((err) => {
        if (!cancelled) setSpectateRunsError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => !cancelled && setSpectateRunsLoading(false));
    return () => { cancelled = true; };
  }, [setupStep, gameMode]);

  // ---- event handlers ----

  const resolveStartBoard = () => {
    if (boardMode === "curated") {
      const preset = findPreset(boardPresets, selectedPresetId);
      if (!preset) throw new Error("请选择一套推荐板子");
      return {
        config_id: preset.preset_id,
        player_count: preset.player_count,
        role_names: preset.kind === "curated" ? undefined : preset.role_names,
      };
    }
    if (boardMode === "custom") {
      const err = validateCustomLineup(customLineup, playableRoles);
      if (err) throw new Error(err);
      return {
        config_id: nearestStandardConfigId(customLineup.length),
        player_count: customLineup.length,
        role_names: customLineup,
      };
    }
    return {
      config_id: nearestStandardConfigId(playerCount),
      player_count: playerCount,
      role_names: undefined as string[] | undefined,
    };
  };

  const startMatch = async () => {
    if (starting) return;
    setStartError(null);
    setStarting(true);
    setSetupCount(null);
    setInsightEnabled(gameMode === "llmOnly" && enableDeepGame);
    try {
      const board = resolveStartBoard();
      const rosterPayload = customizeModels
        ? {
            players: Array.from({ length: board.player_count }, (_, index) => {
              const seat = index + 1;
              if (gameMode === "humanVsAI" && seat === humanSeat) return {};
              return { provider: seatProviders[index] ?? defaultProviderId };
            }),
          }
        : { defaults: { provider: defaultProviderId } };

      const res = await ApiClient.startGame({
        config_id: board.config_id,
        player_count: board.player_count,
        ...(board.role_names ? { role_names: board.role_names } : {}),
        badge_flow: hasSheriff,
        track_vote_intentions: enableDeepGame,
        ...rosterPayload,
        ...(gameMode === "humanVsAI" ? { human: { seat: humanSeat, role: userRole } } : {}),
      });

      if (gameMode === "humanVsAI" && res.player_token) {
        const sep = res.game_page_path.includes("?") ? "&" : "?";
        navigate(
          `${res.game_page_path}${sep}view=seat&seat=${humanSeat}&token=${encodeURIComponent(res.player_token)}`
        );
      } else {
        navigate(res.game_page_path);
      }
    } catch (e) {
      setStartError(e instanceof Error ? e.message : String(e));
      setStarting(false);
    }
  };

  const handlePlayerCountChange = (val: number) => {
    const nextVal = Math.max(6, Math.min(20, val));
    setPlayerCount(nextVal);
    if (boardMode === "standard") {
      setCustomLineup(standardLineupForCount(nextVal));
    }
  };

  const handleSelectPreset = (id: string) => {
    setSelectedPresetId(id);
    const preset = findPreset(boardPresets, id);
    if (preset) setPlayerCount(preset.player_count);
  };

  const handleBoardModeChange = (mode: BoardSetupMode) => {
    setBoardMode(mode);
    if (mode === "standard") {
      setCustomLineup(standardLineupForCount(playerCount));
    }
    if (mode === "custom") {
      setCustomLineup((prev) =>
        prev.length >= 6 ? prev : standardLineupForCount(playerCount),
      );
    }
    if (mode === "curated") {
      const preset = findPreset(boardPresets, selectedPresetId);
      if (preset) setPlayerCount(preset.player_count);
    }
  };

  return {
    // state
    starting,
    startError,
    setupStep,
    showSettingsModal,
    gameMode,
    boardMode,
    boardPresets,
    playableRoles,
    selectedPresetId,
    customLineup,
    presetsLoading,
    playerCount,
    userRole,
    humanSeat,
    hasSheriff,
    enableDeepGame,
    customizeModels,
    availableModels,
    modelsLoading,
    seatProviders,
    spectatableRuns,
    spectateRunId,
    spectateRunsLoading,
    spectateRunsError,
    // computed
    defaultProviderId,
    activeLineup,
    effectivePlayerCount,
    lineupRoleOptions,
    // setters
    setSetupStep,
    setShowSettingsModal,
    setGameMode,
    setBoardMode,
    setPlayerCount,
    setUserRole,
    setHumanSeat,
    setHasSheriff,
    setEnableDeepGame,
    setCustomizeModels,
    setCustomLineup,
    setSeatProviders,
    setAvailableModels,
    // callbacks
    startMatch,
    handlePlayerCountChange,
    handleSelectPreset,
    handleBoardModeChange,
  };
}
