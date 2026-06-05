export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message: string | null;
}

const API_V1 = "/api/v1";

export async function fetchPage<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_V1}${path}`, {
    headers: { Accept: "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  const body = (await res.json()) as ApiResponse<T>;
  if (!body.success) {
    throw new Error(body.message || `API ${path} returned success=false`);
  }
  return body.data;
}
