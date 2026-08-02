import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Server,
  Plus,
  Trash2,
  RefreshCw,
  Loader2,
  Terminal,
  Globe,
  Check,
  Copy,
  Search,
  ChevronDown,
  ChevronRight,
  CircleAlert,
} from "lucide-react";
import { api, type McpServerEntry, type McpServerStatus } from "../services/api";

interface AddForm {
  name: string;
  type: "local" | "remote";
  command: string;
  url: string;
  environment: string;
  enabled: boolean;
}

const EMPTY_FORM: AddForm = { name: "", type: "local", command: "", url: "", environment: "", enabled: true };

type ServerState = "connected" | "connecting" | "error" | "disabled" | "unknown";

const SECRET_KEY_RE = /(token|secret|password|passwd|api[-_]?key|_key|auth)/i;

function displayEnvValue(key: string, value: string): string {
  return SECRET_KEY_RE.test(key) ? "••••••••" : value;
}

function statusOf(s: McpServerEntry, status?: McpServerStatus): ServerState {
  if (!s.enabled) return "disabled";
  if (!status) return "unknown";
  if (status.status === "connected") return "connected";
  if (status.status === "connecting") return "connecting";
  if (status.status === "error" || status.status === "failed") return "error";
  return "unknown";
}

const DOT_CLASSES: Record<ServerState, string> = {
  connected: "bg-green-500",
  connecting: "bg-amber-400 animate-pulse",
  error: "bg-red-500",
  disabled: "bg-zinc-600",
  unknown: "bg-zinc-500",
};

const LABEL_CLASSES: Record<ServerState, string> = {
  connected: "text-green-400",
  connecting: "text-amber-400",
  error: "text-red-400",
  disabled: "text-zinc-500",
  unknown: "text-zinc-500",
};

export function McpServers() {
  const [servers, setServers] = useState<McpServerEntry[]>([]);
  const [statuses, setStatuses] = useState<Record<string, McpServerStatus>>({});
  const [statusNote, setStatusNote] = useState("");
  const [configPath, setConfigPath] = useState("");
  const [loading, setLoading] = useState(true);
  const [statusLoading, setStatusLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState<AddForm>(EMPTY_FORM);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState("");
  const [search, setSearch] = useState("");
  const [showEnv, setShowEnv] = useState<Record<string, boolean>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await api.getOConfig();
      setServers(d.data.mcp_servers);
      setConfigPath(d.data.path);
      setError("");
    } catch (e) {
      setError(`Failed to load config: ${e instanceof Error ? e.message : "unknown"}`);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadStatus = useCallback(async () => {
    setStatusLoading(true);
    setStatusNote("");
    try {
      const d = await api.getMcpStatus();
      setStatuses(d.data.servers);
    } catch (e) {
      setStatusNote(e instanceof Error ? e.message : "status unavailable");
      setStatuses({});
    } finally {
      setStatusLoading(false);
    }
  }, []);

  const refresh = useCallback(() => {
    load();
    loadStatus();
  }, [load, loadStatus]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const summary = useMemo(() => {
    const counts: Record<ServerState, number> = {
      connected: 0,
      connecting: 0,
      error: 0,
      disabled: 0,
      unknown: 0,
    };
    for (const s of servers) {
      counts[statusOf(s, statuses[s.name])] += 1;
    }
    return counts;
  }, [servers, statuses]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return servers;
    return servers.filter(
      (s) => s.name.toLowerCase().includes(q) || (s.summary || s.command || s.url || "").toLowerCase().includes(q),
    );
  }, [servers, search]);

  const toggleServer = async (s: McpServerEntry) => {
    try {
      await api.patchMcpServer(s.name, { enabled: !s.enabled });
      setServers((prev) => prev.map((x) => (x.name === s.name ? { ...x, enabled: !x.enabled } : x)));
    } catch (e) {
      setError(`Toggle failed: ${e instanceof Error ? e.message : "unknown"}`);
    }
  };

  const removeServer = async (name: string) => {
    if (!window.confirm(`Remove MCP server '${name}' from opencode config?`)) return;
    try {
      await api.removeMcpServer(name);
      setServers((prev) => prev.filter((x) => x.name !== name));
      setStatuses((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    } catch (e) {
      setError(`Remove failed: ${e instanceof Error ? e.message : "unknown"}`);
    }
  };

  const copyCommand = (s: McpServerEntry) => {
    const text = s.summary || s.command || s.url || "";
    navigator.clipboard.writeText(text).then(() => {
      setCopied(s.name);
      setTimeout(() => setCopied(""), 1500);
    });
  };

  const submitAdd = async () => {
    if (!form.name.trim()) {
      setError("Server name required");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const body: Record<string, unknown> = {
        name: form.name.trim(),
        type: form.type,
        enabled: form.enabled,
      };
      if (form.type === "local") {
        if (!form.command.trim()) {
          setError("Command required for local server");
          setBusy(false);
          return;
        }
        body.command = form.command.trim().split(/\s+/);
        if (form.environment.trim()) {
          const env: Record<string, string> = {};
          for (const line of form.environment.split("\n")) {
            const eq = line.indexOf("=");
            if (eq > 0) env[line.slice(0, eq).trim()] = line.slice(eq + 1).trim();
          }
          body.environment = env;
        }
      } else {
        if (!form.url.trim()) {
          setError("URL required for remote server");
          setBusy(false);
          return;
        }
        body.url = form.url.trim();
      }
      await api.addMcpServer(body);
      setShowAdd(false);
      setForm(EMPTY_FORM);
      await refresh();
    } catch (e) {
      setError(`Add failed: ${e instanceof Error ? e.message : "unknown"}`);
    } finally {
      setBusy(false);
    }
  };

  const inputCls =
    "w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50 font-mono";

  const summaryPills: Array<{ key: ServerState; label: string }> = [
    { key: "connected", label: "Connected" },
    { key: "connecting", label: "Connecting" },
    { key: "error", label: "Errors" },
    { key: "disabled", label: "Disabled" },
    { key: "unknown", label: "Unknown" },
  ];

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Server className="w-6 h-6 text-accent" />
            MCP Servers
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            {servers.length} server{servers.length === 1 ? "" : "s"} in opencode global config
            {configPath ? ` - ${configPath}` : ""}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={refresh}
            className="p-2 text-zinc-400 hover:text-zinc-200 transition-colors"
            title="Refresh servers and status"
            aria-label="Refresh MCP servers"
          >
            <RefreshCw className={`w-4 h-4 ${loading || statusLoading ? "animate-spin" : ""}`} />
          </button>
          <button
            type="button"
            onClick={() => setShowAdd((v) => !v)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm bg-accent hover:bg-accent-hover text-white transition-colors"
            data-testid="add-mcp-server"
          >
            <Plus className="w-4 h-4" />
            Add Server
          </button>
        </div>
      </div>

      <div
        className="flex flex-wrap items-center gap-2 mb-4 px-3 py-2 bg-surface-light border border-surface-border rounded-lg"
        data-testid="mcp-servers-summary"
      >
        {summaryPills.map((p) => (
          <span key={p.key} className="flex items-center gap-1.5 text-xs text-zinc-400">
            <span className={`w-2 h-2 rounded-full ${DOT_CLASSES[p.key]}`} />
            {p.label}: <span className="text-zinc-200 font-semibold">{summary[p.key]}</span>
          </span>
        ))}
        {statusLoading && <Loader2 className="w-3 h-3 animate-spin text-zinc-500 ml-1" />}
        {statusNote && (
          <span className="flex items-center gap-1 text-xs text-zinc-600 ml-1" title={statusNote}>
            <CircleAlert className="w-3 h-3" /> status unavailable
          </span>
        )}
        <div className="flex-1" />
        <div className="relative w-52">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search servers..."
            data-testid="mcp-servers-search"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md pl-8 pr-2 py-1.5 text-xs focus:outline-none focus:border-accent/50"
          />
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded-lg text-sm text-red-400">{error}</div>
      )}

      {showAdd && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 bg-surface-light border border-surface-border rounded-xl p-5"
        >
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4">Add MCP Server</h2>
          <div className="space-y-3">
            <div>
              <label htmlFor="mcps-name" className="text-xs text-zinc-500 mb-1 block">
                Name
              </label>
              <input
                id="mcps-name"
                type="text"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="resonite-mcp"
                className={inputCls}
                data-testid="mcps-name"
              />
            </div>
            <div>
              <label htmlFor="mcps-type" className="text-xs text-zinc-500 mb-1 block">
                Type
              </label>
              <select
                id="mcps-type"
                value={form.type}
                onChange={(e) => setForm((f) => ({ ...f, type: e.target.value as "local" | "remote" }))}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50"
              >
                <option value="local">Local (stdio command)</option>
                <option value="remote">Remote (HTTP URL)</option>
              </select>
            </div>
            {form.type === "local" ? (
              <>
                <div>
                  <label htmlFor="mcps-command" className="text-xs text-zinc-500 mb-1 block">
                    Command
                  </label>
                  <input
                    id="mcps-command"
                    type="text"
                    value={form.command}
                    onChange={(e) => setForm((f) => ({ ...f, command: e.target.value }))}
                    placeholder="D:\Dev\repos\resonite-mcp\.venv\Scripts\python.exe -m resonite_mcp.__main__"
                    className={inputCls}
                    data-testid="mcps-command"
                  />
                </div>
                <div>
                  <label htmlFor="mcps-env" className="text-xs text-zinc-500 mb-1 block">
                    Environment (KEY=VALUE per line, optional)
                  </label>
                  <textarea
                    id="mcps-env"
                    value={form.environment}
                    onChange={(e) => setForm((f) => ({ ...f, environment: e.target.value }))}
                    rows={2}
                    className={inputCls}
                  />
                </div>
              </>
            ) : (
              <div>
                <label htmlFor="mcps-url" className="text-xs text-zinc-500 mb-1 block">
                  URL
                </label>
                <input
                  id="mcps-url"
                  type="text"
                  value={form.url}
                  onChange={(e) => setForm((f) => ({ ...f, url: e.target.value }))}
                  placeholder="http://127.0.0.1:10979/mcp"
                  className={inputCls}
                  data-testid="mcps-url"
                />
              </div>
            )}
            <label className="flex items-center gap-2 text-sm text-zinc-300">
              <input
                type="checkbox"
                checked={form.enabled}
                onChange={(e) => setForm((f) => ({ ...f, enabled: e.target.checked }))}
                className="accent-accent"
              />
              Enabled
            </label>
            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={submitAdd}
                disabled={busy}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm bg-accent hover:bg-accent-hover text-white transition-colors disabled:opacity-50"
                data-testid="mcps-submit"
              >
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                Add
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowAdd(false);
                  setForm(EMPTY_FORM);
                }}
                className="px-4 py-2 rounded-lg text-sm bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </motion.div>
      )}

      {loading ? (
        <div className="flex justify-center py-12 text-zinc-500">
          <Loader2 className="w-6 h-6 animate-spin" />
        </div>
      ) : servers.length === 0 ? (
        <div className="text-center py-12 text-zinc-500">
          <Server className="w-8 h-8 mx-auto mb-3 opacity-40" />
          <p>No MCP servers in opencode config.</p>
          <p className="text-sm">Add one with the button above.</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-zinc-500">
          <Search className="w-8 h-8 mx-auto mb-3 opacity-40" />
          <p>No servers match "{search}"</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((s) => {
            const state = statusOf(s, statuses[s.name]);
            const envKeys = s.environment ? Object.keys(s.environment) : [];
            const showEnvFor = !!showEnv[s.name];
            return (
              <motion.div
                key={s.name}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className={`bg-surface-light border rounded-xl p-4 transition-opacity ${
                  s.enabled ? "border-surface-border" : "border-surface-border opacity-60"
                }`}
                data-testid={`mcp-server-${s.name}`}
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${DOT_CLASSES[state]}`}
                    data-testid={`mcp-server-status-${s.name}`}
                    title={`${state}`}
                  />
                  {s.type === "remote" ? (
                    <Globe className="w-4 h-4 text-accent flex-shrink-0" />
                  ) : (
                    <Terminal className="w-4 h-4 text-accent flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-semibold text-zinc-200">{s.name}</span>
                      <span className="text-[10px] uppercase tracking-wider text-zinc-500 border border-zinc-700 rounded px-1.5 py-0.5">
                        {s.type}
                      </span>
                      <span className={`text-[10px] uppercase tracking-wider ${LABEL_CLASSES[state]}`}>{state}</span>
                    </div>
                    <p
                      className="text-xs text-zinc-500 font-mono truncate mt-1 max-w-xl"
                      title={s.summary || s.command || s.url}
                    >
                      {s.summary || s.command || s.url}
                    </p>
                    {envKeys.length > 0 && (
                      <div className="mt-1.5">
                        <button
                          type="button"
                          onClick={() => setShowEnv((prev) => ({ ...prev, [s.name]: !prev[s.name] }))}
                          className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-zinc-500 hover:text-zinc-300 transition-colors"
                        >
                          {showEnvFor ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                          env · {envKeys.join(", ")}
                        </button>
                        {showEnvFor && (
                          <div className="mt-1.5 flex flex-wrap gap-1.5">
                            {envKeys.map((k) => (
                              <code
                                key={k}
                                className="text-[10px] font-mono text-zinc-400 bg-zinc-800/80 border border-zinc-700/60 rounded px-1.5 py-0.5"
                              >
                                {k}=
                                <span className="text-zinc-500">{displayEnvValue(k, s.environment?.[k] ?? "?")}</span>
                              </code>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => copyCommand(s)}
                    className="p-2 text-zinc-500 hover:text-zinc-300 transition-colors"
                    title="Copy command"
                    aria-label={`Copy command for ${s.name}`}
                  >
                    {copied === s.name ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => toggleServer(s)}
                    className="p-2 text-zinc-500 hover:text-zinc-300 transition-colors"
                    title={s.enabled ? "Disable" : "Enable"}
                    aria-label={`${s.enabled ? "Disable" : "Enable"} ${s.name}`}
                    data-testid={`mcp-server-toggle-${s.name}`}
                  >
                    <span
                      className={`block w-8 h-4 rounded-full transition-colors relative ${
                        s.enabled ? "bg-accent/70" : "bg-zinc-700"
                      }`}
                    >
                      <span
                        className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-all ${
                          s.enabled ? "left-4" : "left-0.5"
                        }`}
                      />
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => removeServer(s.name)}
                    className="p-2 text-zinc-500 hover:text-red-400 transition-colors"
                    title="Remove"
                    aria-label={`Remove ${s.name}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      <p className="text-xs text-zinc-600 mt-6">
        Note: opencode reads config at startup. Restart opencode to apply changes. Status reflects the connection state
        reported by opencode serve.
      </p>
    </div>
  );
}
