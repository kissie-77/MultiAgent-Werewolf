/** Optional settings token when WEREWOLF_SETTINGS_TOKEN is configured on the server. */
const SETTINGS_TOKEN = (import.meta.env.VITE_SETTINGS_TOKEN ?? "").trim();

function settingsHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (SETTINGS_TOKEN) {
    headers["X-Settings-Token"] = SETTINGS_TOKEN;
  }
  return headers;
}

export type ApiKeySlot = "deepseek" | "openai" | "gemini" | "claude" | "doubao";

export interface ApiKeySlotStatus {
  env_name: string;
  configured: boolean;
  masked: string | null;
}

export interface ApiKeysStatusResponse {
  keys: Record<ApiKeySlot, ApiKeySlotStatus>;
  env_file: string;
  writable: boolean;
}

export type UpdateApiKeysPayload = Partial<Record<ApiKeySlot, string>>;

export async function fetchApiKeysStatus(): Promise<ApiKeysStatusResponse> {
  const res = await fetch("/api/v1/settings/api-keys", { headers: settingsHeaders() });
  if (!res.ok) {
    throw new Error(`Failed to load API key status: ${res.status} ${res.statusText}`);
  }
  const json = await res.json();
  return (json.data ?? json) as ApiKeysStatusResponse;
}

export async function saveApiKeysToServer(payload: UpdateApiKeysPayload): Promise<ApiKeysStatusResponse> {
  const res = await fetch("/api/v1/settings/api-keys", {
    method: "POST",
    headers: settingsHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail ?? j.message ?? detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  const json = await res.json();
  return (json.data ?? json) as ApiKeysStatusResponse;
}

/** Legacy store.ts hooks; keys now live in server .env only. */
export const getCustomApiKey = () => "";
export const setCustomApiKey = (_key: string) => {};
export const getOpenAIApiKey = () => "";
export const setOpenAIApiKey = (_key: string) => {};
export const getGeminiApiKey = () => "";
export const setGeminiApiKey = (_key: string) => {};
export const getClaudeApiKey = () => "";
export const setClaudeApiKey = (_key: string) => {};
export const getDoubaoApiKey = () => "";
export const setDoubaoApiKey = (_key: string) => {};
