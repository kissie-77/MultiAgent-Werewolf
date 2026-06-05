import { 
  HomePageData, 
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
  RunListPageData
} from "./types";

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
    const response = await fetch(`${API_BASE}${url}`);
    if (!response.ok) {
      throw new Error(`API error fetching ${url}: ${response.statusText}`);
    }
    return unwrap<T>(await response.json());
  }

  static async getHomePageData(): Promise<HomePageData> {
    return this.get<HomePageData>("/api/v1/pages/home");
  }

  static async getRolesPageData(): Promise<RolesPageData> {
    return this.get<RolesPageData>("/api/v1/pages/roles");
  }

  static async getRoleDetail(roleKey: string): Promise<RoleDetail> {
    return this.get<RoleDetail>(`/api/v1/pages/roles/${encodeURIComponent(roleKey)}`);
  }

  static async getModelsPageData(): Promise<ModelsPageData> {
    return this.get<ModelsPageData>("/api/v1/pages/models");
  }

  static async getModelDetail(modelId: string): Promise<ModelDetail> {
    return this.get<ModelDetail>(`/api/v1/pages/models/${encodeURIComponent(modelId)}`);
  }

  static async compareModels(ids: string[]): Promise<ModelComparisonData> {
    const params = new URLSearchParams();
    ids.forEach(id => params.append("ids", id));
    return this.get<ModelComparisonData>(`/api/v1/pages/models/compare?${params.toString()}`);
  }

  static async getReplayData(runId: string): Promise<ReplayPageData> {
    return this.get<ReplayPageData>(`/api/v1/pages/replay?run_id=${encodeURIComponent(runId)}`);
  }

  static async getShareReplayData(runId: string): Promise<ShareReplayPageData> {
    return this.get<ShareReplayPageData>(`/api/v1/pages/share-replay?run_id=${encodeURIComponent(runId)}`);
  }

  static async getAboutPageData(): Promise<AboutPageData> {
    return this.get<AboutPageData>("/api/v1/pages/about");
  }

  static async getFeaturesPageData(): Promise<FeaturesPageData> {
    return this.get<FeaturesPageData>("/api/v1/pages/features");
  }

  static async getHowToPlayPageData(): Promise<HowToPlayPageData> {
    return this.get<HowToPlayPageData>("/api/v1/pages/how-to-play");
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
}


