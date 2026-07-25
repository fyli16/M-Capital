import type {
  CreateResearchRequest,
  MemorySearchResponse,
  PerformanceLeaderboard,
  RecommendationView,
  ResearchRequestAccepted,
  ResearchResultView,
} from "@/lib/types/contracts";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

const TOKEN_KEY = "aegis_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---- Auth -------------------------------------------------------------------

export async function login(email: string, password: string): Promise<string> {
  const form = new URLSearchParams({ username: email, password });
  const res = await fetch(`${API_URL}/api/v1/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
  if (!res.ok) throw new ApiError(res.status, "Invalid credentials");
  const body = (await res.json()) as { access_token: string };
  return body.access_token;
}

export async function register(
  email: string,
  password: string,
  role = "analyst"
): Promise<void> {
  await request("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, role }),
  });
}

// ---- Research ---------------------------------------------------------------

export function submitResearch(
  body: CreateResearchRequest
): Promise<ResearchRequestAccepted> {
  return request("/api/v1/research", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getResearch(id: string): Promise<ResearchResultView> {
  return request(`/api/v1/research/${id}`);
}

export function listRecommendations(params?: {
  ticker?: string;
  limit?: number;
}): Promise<RecommendationView[]> {
  const q = new URLSearchParams();
  if (params?.ticker) q.set("ticker", params.ticker);
  if (params?.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return request(`/api/v1/recommendations${qs ? `?${qs}` : ""}`);
}

export function getPerformance(): Promise<PerformanceLeaderboard> {
  return request("/api/v1/agent-performance");
}

export function searchMemory(
  query: string,
  ticker?: string
): Promise<MemorySearchResponse> {
  const q = new URLSearchParams({ query });
  if (ticker) q.set("ticker", ticker);
  return request(`/api/v1/memory/search?${q.toString()}`);
}

/** Open an SSE stream for live research progress. */
export function streamResearch(id: string): EventSource {
  const token = getToken();
  const url = new URL(`${API_URL}/api/v1/research/${id}/stream`);
  // EventSource can't set headers; pass the token as a query param the gateway
  // can also accept, or rely on the same-site cookie in a production setup.
  if (token) url.searchParams.set("access_token", token);
  return new EventSource(url.toString());
}
