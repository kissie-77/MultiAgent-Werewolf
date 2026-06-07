export const getCustomApiKey = () => localStorage.getItem("deepseek_api_key") || "";
export const setCustomApiKey = (key: string) => localStorage.setItem("deepseek_api_key", key);

export const getOpenAIApiKey = () => localStorage.getItem("openai_api_key") || "";
export const setOpenAIApiKey = (key: string) => localStorage.setItem("openai_api_key", key);

export const getGeminiApiKey = () => localStorage.getItem("gemini_api_key") || "";
export const setGeminiApiKey = (key: string) => localStorage.setItem("gemini_api_key", key);

export const getClaudeApiKey = () => localStorage.getItem("claude_api_key") || "";
export const setClaudeApiKey = (key: string) => localStorage.setItem("claude_api_key", key);

export const getDoubaoApiKey = () => localStorage.getItem("doubao_api_key") || "";
export const setDoubaoApiKey = (key: string) => localStorage.setItem("doubao_api_key", key);
