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

export interface LocalModels {
  provider: string | null;
  port: number | null;
  models: string[];
}

export interface LlmProvider {
  id: string;
  label: string;
  base_url: string;
  models: string[];
  needs_key: boolean;
}

export interface LlmProvidersResponse {
  success: boolean;
  data: {
    providers: LlmProvider[];
  };
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

export interface DocEntry {
  id: string;
  label: string;
  file: string;
}

export interface DocContent {
  id: string;
  label: string;
  content: string;
}

export interface OpenCodeToolDef {
  name: string;
  label: string;
  category: string;
  description: string;
  source: string;
}

export interface McpServerEntry {
  name: string;
  type: string;
  enabled: boolean;
  command?: string;
  url?: string;
  environment?: Record<string, string>;
  summary?: string;
}

export interface PluginEntry {
  index: number;
  name: string;
  display: string;
  source: string;
}

export interface PluginDirEntry {
  name: string;
  path: string;
  size: number;
  source: string;
}

export interface OConfigResponse {
  success: boolean;
  data: {
    path: string;
    mcp_servers: McpServerEntry[];
    mcp_count: number;
    plugins: PluginEntry[];
    plugin_count: number;
    plugin_dir_plugins: PluginDirEntry[];
    plugin_dir: string;
    plugin_dir_count: number;
  };
}

export function pluginDisplay(p: unknown): string {
  if (typeof p === "string") return p;
  if (Array.isArray(p) && p.length > 0) return String(p[0]);
  try {
    return JSON.stringify(p);
  } catch {
    return String(p);
  }
}

export const api = {
  getCapabilities: () => fetchJson<CapabilitiesResponse>("/capabilities"),
  getHealth: () => fetchJson<{ status: string }>("/health"),

  getOpencodeStatus: () => fetchJson<{ success: boolean; data: OpencodeStatus }>("/opencode/status"),
  listSessions: () => fetchJson<{ success: boolean; data: { sessions: Session[] } }>("/opencode/sessions"),
  getSession: (id: string) => fetchJson<{ success: boolean; data: { session: Session } }>(`/opencode/sessions/${id}`),

  getFleet: () => fetchJson<{ success: boolean; data: { apps: FleetApp[] } }>("/fleet"),
  getOllamaStatus: () => fetchJson<{ success: boolean; data: OllamaStatus }>("/ollama/status"),
  getLlmProviders: () => fetchJson<LlmProvidersResponse>("/llm/providers"),
  getLocalModels: () => fetchJson<{ success: boolean; data: LocalModels }>("/ollama/models"),
  getSystemInfo: () => fetchJson<{ success: boolean; data: SystemInfo }>("/system"),

  listToolDetails: () => fetchJson<{ success: boolean; data: { tools: ToolDetail[] } }>("/tools"),

  getSettings: () => fetchJson<Record<string, unknown>>("/settings"),
  updateSettings: (s: Record<string, unknown>) =>
    fetchJson<{ success: boolean }>("/settings", {
      method: "PUT",
      body: JSON.stringify(s),
    }),

  listDocs: () => fetchJson<{ success: boolean; data: { docs: DocEntry[] } }>("/docs"),
  getDoc: (id: string) => fetchJson<{ success: boolean; data: DocContent }>(`/docs/${id}`),

  listOpenCodeTools: () =>
    fetchJson<{ success: boolean; data: { tools: OpenCodeToolDef[]; install_path: string } }>("/opencode-tools"),

  getOConfig: () => fetchJson<OConfigResponse>("/occonfig"),
  addMcpServer: (body: Record<string, unknown>) =>
    fetchJson<{ success: boolean; message: string }>("/occonfig/mcp", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  removeMcpServer: (name: string) =>
    fetchJson<{ success: boolean; message: string }>(`/occonfig/mcp/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),
  patchMcpServer: (name: string, body: Record<string, unknown>) =>
    fetchJson<{ success: boolean; message: string }>(`/occonfig/mcp/${encodeURIComponent(name)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  addPlugin: (plugin: unknown) =>
    fetchJson<{ success: boolean; message: string }>("/occonfig/plugin", {
      method: "POST",
      body: JSON.stringify({ plugin }),
    }),
  removePlugin: (index: number) =>
    fetchJson<{ success: boolean; message: string }>(`/occonfig/plugin/${index}`, {
      method: "DELETE",
    }),
};
