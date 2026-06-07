import { 
  HomePageData, 
  BackendHomePageData,
  RolesPageData, 
  RoleDetail, 
  ModelsPageData, 
  ModelDetail, 
  ModelComparisonData, 
  ReplayPageData, 
  ShareReplayPageData,
  AboutPageData,
  FeaturesPageData,
  HowToPlayPageData,
  NightPhasePageData,
  StrategyPageData,
  RunListPageData,
  StartGameRequest,
  StartGameResponse,
  HumanInputRequest,
  HumanInputResponse,
  GameStatusResponse,
  BackendReplayPageData,
  BackendModelsPageData,
  BackendShareReplayData,
  BackendRolesPageData,
  BackendRoleDetailData,
  BackendHowToPlayPageData,
  BackendAboutPageData,
} from "./types";
import { mapReplayPage } from "../lib/replayMap";
import { mapModelsPage } from "../lib/modelsMap";
import { mapSharePage } from "../lib/shareMap";
import { mapHomePage } from "../lib/homeMap";
import { mapRoleDetail, mapRolesPage } from "../lib/rolesMap";
import { mapHowToPlayPage } from "../lib/howToPlayMap";
import { mapAboutPage } from "../lib/aboutMap";
import { fetchWithRetry } from "./retry";

const API_BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/+$/, "");

/**
 * Unwrap the backend's ApiResponse<T> envelope ({ success, data, message }).
 * Returns the inner `data`. If the value is not an envelope (e.g. a bare
 * payload), it is returned unchanged so tests/legacy paths keep working.
 */
export function unwrap<T>(json: unknown): T {
  if (
    json !== null &&
    typeof json === "object" &&
    "data" in (json as Record<string, unknown>) &&
    ("success" in (json as Record<string, unknown>) ||
      "message" in (json as Record<string, unknown>))
  ) {
    return (json as { data: T }).data;
  }
  return json as T;
}

export class ApiClient {
  private static async get<T>(url: string): Promise<T> {
    const response = await fetchWithRetry(`${API_BASE}${url}`);
    if (!response.ok) {
      throw new Error(`API error fetching ${url}: ${response.statusText}`);
    }
    return unwrap<T>(await response.json());
  }

  private static async post<T>(url: string, body: unknown): Promise<T> {
    const response = await fetchWithRetry(`${API_BASE}${url}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const j = await response.json();
        detail = (j && (j.detail || j.message)) || detail;
      } catch {
        // non-JSON error body; keep statusText
      }
      throw new Error(`API error POST ${url}: ${detail}`);
    }
    return unwrap<T>(await response.json());
  }

  static async startGame(req: StartGameRequest): Promise<StartGameResponse> {
    return this.post<StartGameResponse>("/api/v1/games/start", req);
  }

  static async sendInput(runId: string, body: HumanInputRequest): Promise<HumanInputResponse> {
    return this.post<HumanInputResponse>(
      `/api/v1/games/${encodeURIComponent(runId)}/input`,
      body
    );
  }

  static async getGameStatus(runId: string, source = "runs"): Promise<GameStatusResponse> {
    return this.get<GameStatusResponse>(
      `/api/v1/games/${encodeURIComponent(runId)}/status?source=${encodeURIComponent(source)}`
    );
  }

  static async getHomePageData(): Promise<HomePageData> {
    const raw = await this.get<BackendHomePageData>("/api/v1/pages/home");
    return mapHomePage(raw);
  }

  static async getRolesPageData(): Promise<RolesPageData> {
    const raw = await this.get<BackendRolesPageData>("/api/v1/pages/roles");
    return mapRolesPage(raw);
  }

  static async getRoleDetail(roleKey: string): Promise<RoleDetail> {
    const raw = await this.get<BackendRoleDetailData>(
      `/api/v1/pages/roles/${encodeURIComponent(roleKey)}`
    );
    return mapRoleDetail(raw);
  }

  static async getModelsPageData(): Promise<ModelsPageData> {
    // Backend returns ModelListPageData (usage_stats, fractional win_rate); the
    // mapper reshapes it into the page's ModelsPageData (models[], percent).
    const raw = await this.get<BackendModelsPageData>("/api/v1/pages/models");
    return mapModelsPage(raw);
  }

  static async getModelDetail(modelId: string): Promise<ModelDetail> {
    return this.get<ModelDetail>(`/api/v1/pages/models/${encodeURIComponent(modelId)}`);
  }

  static async compareModels(ids: string[]): Promise<ModelComparisonData> {
    const params = new URLSearchParams();
    ids.forEach(id => params.append("ids", id));
    return this.get<ModelComparisonData>(`/api/v1/pages/models/compare?${params.toString()}`);
  }

  static async getReplayData(runId: string, source = "runs"): Promise<ReplayPageData> {
    // Always request the enriched per-run replay under the god view: belief /
    // heatmap blocks are only populated for view=god, and the mapper filters the
    // god-injected belief/vote snapshot events back out of the timeline.
    const params = new URLSearchParams({ run_id: runId, source, view: "god" });
    const raw = await this.get<BackendReplayPageData>(
      `/api/v1/pages/replay?${params.toString()}`
    );
    return mapReplayPage(raw);
  }

  static async getShareReplayData(runId: string): Promise<ShareReplayPageData> {
    // Backend mvp_winner is snake_case with no citation and winner_camp is
    // lowercase; the mapper reshapes it into what SharePage renders.
    const raw = await this.get<BackendShareReplayData>(
      `/api/v1/pages/share-replay?run_id=${encodeURIComponent(runId)}`
    );
    return mapSharePage(raw);
  }

  static async getAboutPageData(): Promise<AboutPageData> {
    const raw = await this.get<BackendAboutPageData>("/api/v1/pages/about");
    return mapAboutPage(raw);
  }

  static async getFeaturesPageData(): Promise<FeaturesPageData> {
    return this.get<FeaturesPageData>("/api/v1/pages/features");
  }

  static async getHowToPlayPageData(): Promise<HowToPlayPageData> {
    const raw = await this.get<BackendHowToPlayPageData>("/api/v1/pages/how-to-play");
    return mapHowToPlayPage(raw);
  }

  static async getNightPhasePageData(): Promise<NightPhasePageData> {
    return this.get<NightPhasePageData>("/api/v1/pages/night-phase");
  }

  static async getStrategyPageData(): Promise<StrategyPageData> {
    return this.get<StrategyPageData>("/api/v1/pages/strategy");
  }

  static async getRunsPageData(page = 1, pageSize = 20): Promise<RunListPageData> {
    return this.get<RunListPageData>(
      `/api/v1/runs?page=${page}&page_size=${pageSize}`
    );
  }

  /** Runs that have on-disk events.jsonl (spectate / log replay). */
  static async getSpectatableRuns(page = 1, pageSize = 30): Promise<RunListPageData> {
    return this.get<RunListPageData>(
      `/api/v1/runs?page=${page}&page_size=${pageSize}&replay_only=true`
    );
  }

  /** Raw replay timeline from server-side events.jsonl (before UI mapping). */
  static async getReplayLogEvents(
    runId: string,
    source = "runs",
  ): Promise<import("./types").BackendReplayPageData> {
    const params = new URLSearchParams({ run_id: runId, source, view: "god" });
    return this.get<import("./types").BackendReplayPageData>(
      `/api/v1/pages/replay?${params.toString()}`
    );
  }
}


