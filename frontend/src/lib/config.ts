/** Optional settings token when WEREWOLF_SETTINGS_TOKEN is configured on the server. */
const SETTINGS_TOKEN = (import.meta.env.VITE_SETTINGS_TOKEN ?? "").trim();

function settingsHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (SETTINGS_TOKEN) {
    headers["X-Settings-Token"] = SETTINGS_TOKEN;
  }
  return headers;
}

export interface EnvFieldStatus {
  env_name: string;
  configured: boolean;
  masked: string | null;
}

export interface ProviderFieldSchema {
  env_name: string;
  label: string;
  required: boolean;
  secret: boolean;
  example: string;
  description: string;
}

export interface ProviderSchema {
  provider_id: string;
  display_name: string;
  fields: ProviderFieldSchema[];
}

export interface ProvidersListResponse {
  providers: ProviderSchema[];
  default_provider_id: string;
}

export interface ApiKeysStatusResponse {
  keys: Record<string, EnvFieldStatus>;
  env_fields: Record<string, EnvFieldStatus>;
  env_file: string;
  writable: boolean;
}

export async function fetchProviders(): Promise<ProvidersListResponse> {
  const res = await fetch("/api/v1/settings/providers", { headers: settingsHeaders() });
  if (!res.ok) {
    throw new Error(`Failed to load providers: ${res.status} ${res.statusText}`);
  }
  const json = await res.json();
  return (json.data ?? json) as ProvidersListResponse;
}

export async function fetchApiKeysStatus(): Promise<ApiKeysStatusResponse> {
  const res = await fetch("/api/v1/settings/api-keys", { headers: settingsHeaders() });
  if (!res.ok) {
    throw new Error(`Failed to load API key status: ${res.status} ${res.statusText}`);
  }
  const json = await res.json();
  return (json.data ?? json) as ApiKeysStatusResponse;
}

export async function saveProviderFieldsToServer(
  fields: Record<string, string>,
): Promise<ApiKeysStatusResponse> {
  const res = await fetch("/api/v1/settings/api-keys", {
    method: "POST",
    headers: settingsHeaders(),
    body: JSON.stringify({ fields }),
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
  await res.json();
  return fetchApiKeysStatus();
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
