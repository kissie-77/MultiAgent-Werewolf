import { ProviderPreset } from "../types";

// 项目自有 provider 预设（base_url 与 configs/*.yaml 对齐，可按需增减）
export const PROVIDER_PRESETS: ProviderPreset[] = [
  { id: "deepseek", label: "DeepSeek", base_url: "https://api.deepseek.com/v1",
    models: ["deepseek-chat", "deepseek-reasoner"] },
  { id: "doubao", label: "豆包 Doubao", base_url: "https://ark.cn-beijing.volces.com/api/v3",
    models: ["doubao-pro-32k", "doubao-lite-32k"] },
  { id: "siliconflow", label: "SiliconFlow", base_url: "https://api.siliconflow.cn/v1",
    models: ["Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3"] },
  { id: "openai", label: "OpenAI 兼容", base_url: "https://api.openai.com/v1",
    models: ["gpt-4o-mini", "gpt-4o"] },
];

const KEY_PREFIX = "werewolf.apikey.";

export function getApiKey(provider: string): string {
  try {
    return localStorage.getItem(KEY_PREFIX + provider) || "";
  } catch {
    return "";
  }
}

export function setApiKey(provider: string, key: string): void {
  try {
    if (key) localStorage.setItem(KEY_PREFIX + provider, key);
    else localStorage.removeItem(KEY_PREFIX + provider);
  } catch {
    /* ignore quota/private-mode errors */
  }
}

export function providerById(id: string): ProviderPreset | undefined {
  return PROVIDER_PRESETS.find((p) => p.id === id);
}
