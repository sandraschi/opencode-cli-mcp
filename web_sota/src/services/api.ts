const API_BASE = "/api";
const FETCH_TIMEOUT = 15000;

async function fetchJson<T>(url: string, init?: RequestInit, timeoutMs: number = FETCH_TIMEOUT): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
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

export interface McpServerStatus {
  status: string;
  [key: string]: unknown;
}

export interface DepotSession {
  id: string;
  project_id?: string | null;
  slug?: string | null;
  directory?: string | null;
  title?: string | null;
  agent?: string | null;
  model?: string | null;
  cost?: number | null;
  cost_est?: number | null;
  tokens_input?: number | null;
  tokens_output?: number | null;
  archived: boolean;
  time_created_display?: string | null;
  time_updated_display?: string | null;
  time_archived_display?: string | null;
  message_count?: number;
  part_count?: number;
  [key: string]: unknown;
}

export interface DepotListResponse {
  success: boolean;
  message: string;
  data: {
    sessions: DepotSession[];
    total: number;
    limit: number;
    offset: number;
    next_offset: number | null;
  };
}

export interface DepotStats {
  totals: {
    total: number;
    archived: number;
    active: number;
    total_cost: number;
    estimated_cost: number;
    estimated_cost_known_sessions: number;
    tokens_input: number;
    tokens_output: number;
    tokens_reasoning: number;
    tokens_cache_read: number;
  };
  by_agent: Array<{ agent: string; count: number; cost: number; cost_est: number }>;
  by_project: Array<{ project_id: string; count: number; cost: number; cost_est: number }>;
  top_cost: Array<{ id: string; title: string; cost: number; cost_est: number }>;
}

export interface DepotSearchResult {
  session_id: string;
  title: string;
  archived: boolean;
  directory: string;
  agent: string;
  timestamp: string;
  snippet: string;
}

export interface RagStatus {
  available: boolean;
  enabled: boolean;
  reason?: string;
  backend?: string;
  model?: string;
  db_path?: string;
  indexed_chunks: number;
  last_watermark_ms?: number;
  running?: boolean;
  indexed_sessions?: number;
  total_sessions?: number;
  pending_sessions?: number | null;
  install_hint?: string;
  error?: string;
}

export interface RagSearchResult {
  session_id: string;
  title: string;
  agent: string;
  directory: string;
  snippet: string;
  rank: number;
  distance: number;
  engine: string;
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
  renameSession: (id: string, title: string) =>
    fetchJson<{ success: boolean; message: string }>(`/opencode/sessions/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  deleteSession: (id: string) =>
    fetchJson<{ success: boolean; message: string }>(`/opencode/sessions/${id}?confirm=true`, {
      method: "DELETE",
    }),

  backupsStatus: () => fetchJson<{ success: boolean; data: BackupStatus }>("/backups/status"),
  backupsList: () => fetchJson<{ success: boolean; data: { backups: BackupEntry[] } }>("/backups/list"),
  backupsCreate: (kind: string) =>
    fetchJson<{ success: boolean; message: string }>(`/backups/create?kind=${kind}`, {
      method: "POST",
    }),
  backupsPrune: () =>
    fetchJson<{ success: boolean; message: string; data: { removed: string[] } }>("/backups/prune", {
      method: "POST",
    }),
  backupsRestore: (name: string, force = false) =>
    fetchJson<{ success: boolean; message: string }>("/backups/restore", {
      method: "POST",
      body: JSON.stringify({ name, confirm: true, force }),
    }),
  backupsDelete: (name: string) =>
    fetchJson<{ success: boolean; message: string }>(`/backups/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),

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
  getMcpStatus: () =>
    fetchJson<{ success: boolean; data: { servers: Record<string, McpServerStatus> } }>(
      "/mcp/status",
      undefined,
      50000,
    ),
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

  depotList: (params: string) => fetchJson<DepotListResponse>(`/depot/sessions?${params}`),
  depotGet: (id: string) =>
    fetchJson<{ success: boolean; message: string; data: { session: DepotSession } }>(`/depot/sessions/${id}`),
  depotSearch: (q: string, limit = 20) =>
    fetchJson<{ success: boolean; message: string; data: { results: DepotSearchResult[]; count: number } }>(
      `/depot/search?q=${encodeURIComponent(q)}&limit=${limit}`,
      undefined,
      60000,
    ),
  depotStats: () => fetchJson<{ success: boolean; message: string; data: DepotStats }>("/depot/stats"),
  depotArchive: (id: string) =>
    fetchJson<{ success: boolean; message: string }>(`/depot/sessions/${encodeURIComponent(id)}/archive`, {
      method: "POST",
    }),
  depotUnarchive: (id: string) =>
    fetchJson<{ success: boolean; message: string }>(`/depot/sessions/${encodeURIComponent(id)}/unarchive`, {
      method: "POST",
    }),
  depotRename: (id: string, title: string) =>
    fetchJson<{ success: boolean; message: string }>(`/depot/sessions/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  depotDelete: (id: string) =>
    fetchJson<{ success: boolean; message: string }>(`/depot/sessions/${encodeURIComponent(id)}?confirm=true`, {
      method: "DELETE",
    }),

  startRun: (body: { prompt: string; project?: string; format?: string; wait?: boolean; timeout?: number }) =>
    fetchJson<{ success: boolean; message: string; data: { job_id: string; status: string } }>("/runs", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  cancelRun: (jobId: string) =>
    fetchJson<{ success: boolean; message: string }>(`/runs/${encodeURIComponent(jobId)}/cancel`, {
      method: "POST",
    }),

  depotRagStatus: () => fetchJson<{ success: boolean; message: string; data: RagStatus }>("/depot/rag/status"),
  depotRagIndex: (limitSessions?: number) =>
    fetchJson<{ success: boolean; message: string; data: RagStatus }>(
      `/depot/rag/index${limitSessions ? `?limit_sessions=${limitSessions}` : ""}`,
      { method: "POST" },
    ),
  depotRagSearch: (q: string, limit = 20) =>
    fetchJson<{ success: boolean; message: string; data: { results: RagSearchResult[]; count: number } }>(
      `/depot/rag/search?q=${encodeURIComponent(q)}&limit=${limit}`,
      undefined,
      60000,
    ),
};

export interface BackupStatus {
  db_path: string;
  db_exists: boolean;
  db_size: number;
  config_dir: string;
  config_exists: boolean;
  backup_dir: string;
  free_bytes: number;
  min_free_bytes: number;
  retention: number;
  autobackup_interval_hours: number;
  counts: { db: number; config: number };
  last_backup?: BackupEntry | null;
  last_autobackup?: { timestamp?: string | null; results: Array<{ kind: string; ok: boolean; error?: string }> } | null;
}

export interface BackupEntry {
  kind: "db" | "config";
  name: string;
  path: string;
  size: number;
  created?: string | null;
}
