export interface RecentRequest {
  id: string;
  ticker: string;
  submittedAt: string;
}

const KEY = "aegis_recent_requests";

export function loadRecent(): RecentRequest[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(window.localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

export function pushRecent(entry: RecentRequest): void {
  if (typeof window === "undefined") return;
  const existing = loadRecent().filter((r) => r.id !== entry.id);
  const next = [entry, ...existing].slice(0, 12);
  window.localStorage.setItem(KEY, JSON.stringify(next));
}
