export async function fetchWithRetry(
  input: RequestInfo | URL,
  init?: RequestInit,
  options: { retries?: number; backoffMs?: number } = {},
): Promise<Response> {
  const retries = options.retries ?? 2;
  const backoffMs = options.backoffMs ?? 300;
  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      const res = await fetch(input, init);
      if (res.ok || res.status < 500 || attempt === retries) {
        return res;
      }
      lastError = new Error(`HTTP ${res.status}`);
    } catch (err) {
      lastError = err;
      if (attempt === retries) {
        throw err;
      }
    }
    await new Promise((resolve) => setTimeout(resolve, backoffMs * (attempt + 1)));
  }
  throw lastError;
}
