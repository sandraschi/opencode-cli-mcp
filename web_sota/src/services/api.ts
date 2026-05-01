const API_BASE = "/api";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export interface CapabilitiesResponse {
  status: string;
  server: { name: string; version: string };
  tool_surface: {
    total: number;
    portmanteau_count: number;
    atomic_count: number;
    atomic_tools: string[];
  };
  features: Record<string, boolean>;
}

export interface OpencodeStatus {
  health?: { status: string };
  sessions?: number;
  config?: Record<string, unknown>;
}

export interface Session {
  id: string;
  title?: string;
  created_at?: string;
  [key: string]: unknown;
}

export const api = {
  getCapabilities: () => fetchJson<CapabilitiesResponse>("/capabilities"),
  getHealth: () => fetchJson<{ status: string }>("/health"),
  getOpencodeStatus: () => fetchJson<{ success: boolean; data: OpencodeStatus }>("/opencode/status"),
  listSessions: () => fetchJson<{ success: boolean; data: { sessions: Session[] } }>("/opencode/sessions"),
  getSession: (id: string) => fetchJson<{ success: boolean; data: { session: Session } }>(`/opencode/sessions/${id}`),
};
