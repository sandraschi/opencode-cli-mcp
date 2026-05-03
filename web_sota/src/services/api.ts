const API_BASE = "/api";
const FETCH_TIMEOUT = 15000;

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT);
  try {
    const res = await fetch(`${API_BASE}${url}`, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      ...init,
    });
    if (!res.ok) {
      throw new Error(`API error: ${res.status} ${res.statusText}`);
    }
    return res.json();
  } finally {
    clearTimeout(timer);
  }
}

export interface CapabilitiesResponse {
  status: string;
  server: { name: string; version: string; fastmcp: string };
  tool_surface: {
    total: number;
    portmanteau_count: number;
    atomic_count: number;
    atomic_tools: string[];
    portmanteau_tools: string[];
  };
  features: Record<string, boolean>;
  runtime: { transport: string; surface_mode: string };
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

export interface FleetApp {
  port: number;
  name: string;
  alive: boolean;
  label?: string;
  known?: boolean;
}

export interface OllamaStatus {
  running: boolean;
  port?: number;
  provider?: string;
}

export interface SystemInfo {
  cpu: number;
  memory: { total: number; used: number; percent: number };
  platform: string;
  gpu?: string;
}

export interface ToolDetail {
  name: string;
  description: string;
  inputSchema?: Record<string, unknown>;
}

export const api = {
  getCapabilities: () => fetchJson<CapabilitiesResponse>("/capabilities"),
  getHealth: () => fetchJson<{ status: string }>("/health"),

  getOpencodeStatus: () =>
    fetchJson<{ success: boolean; data: OpencodeStatus }>("/opencode/status"),
  listSessions: () =>
    fetchJson<{ success: boolean; data: { sessions: Session[] } }>("/opencode/sessions"),
  getSession: (id: string) =>
    fetchJson<{ success: boolean; data: { session: Session } }>(`/opencode/sessions/${id}`),

  getFleet: () => fetchJson<{ success: boolean; data: { apps: FleetApp[] } }>("/fleet"),
  getOllamaStatus: () => fetchJson<{ success: boolean; data: OllamaStatus }>("/ollama/status"),
  getSystemInfo: () => fetchJson<{ success: boolean; data: SystemInfo }>("/system"),

  listToolDetails: () =>
    fetchJson<{ success: boolean; data: { tools: ToolDetail[] } }>("/tools"),

  getSettings: () => fetchJson<Record<string, unknown>>("/settings"),
  updateSettings: (s: Record<string, unknown>) =>
    fetchJson<{ success: boolean }>("/settings", {
      method: "PUT",
      body: JSON.stringify(s),
    }),
};
