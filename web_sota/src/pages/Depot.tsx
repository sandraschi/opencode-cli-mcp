import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Archive,
  ArchiveRestore,
  Database,
  RefreshCw,
  Loader2,
  Search,
  FileText,
  Pencil,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Layers,
  Coins,
  Eye,
} from "lucide-react";
import { api, type DepotSession, type DepotStats } from "../services/api";

const PAGE_SIZE = 25;

interface Filters {
  status: "all" | "active" | "archived";
  search: string;
  searchMode: "title" | "transcript";
}

export function Depot() {
  const [sessions, setSessions] = useState<DepotSession[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [stats, setStats] = useState<DepotStats | null>(null);
  const [filters, setFilters] = useState<Filters>({ status: "all", search: "", searchMode: "title" });
  const [transcriptResults, setTranscriptResults] = useState<
    Array<{ session_id: string; title: string; snippet: string; timestamp: string; archived: boolean }>
  >([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DepotSession | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const load = useCallback(
    async (nextOffset = 0) => {
      setLoading(true);
      setError("");
      try {
        const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(nextOffset), sort: "updated" });
        if (filters.status !== "all") params.set("status", filters.status);
        if (filters.search.trim() && filters.searchMode === "title") params.set("search", filters.search.trim());
        const d = await api.depotList(params.toString());
        setSessions(d.data.sessions);
        setTotal(d.data.total);
        setOffset(nextOffset);
      } catch (e) {
        setError(`Failed to load depot: ${e instanceof Error ? e.message : "unknown"}`);
      } finally {
        setLoading(false);
      }
    },
    [filters.status, filters.search, filters.searchMode],
  );

  const loadStats = useCallback(async () => {
    try {
      const d = await api.depotStats();
      setStats(d.data);
    } catch {
      setStats(null);
    }
  }, []);

  useEffect(() => {
    load();
    loadStats();
  }, [load, loadStats]);

  const runTranscriptSearch = useCallback(async (q: string) => {
    setSearching(true);
    setError("");
    try {
      const d = await api.depotSearch(q);
      setTranscriptResults(d.data.results);
      setTotal(d.data.count);
      setOffset(0);
    } catch (e) {
      setError(`Search failed: ${e instanceof Error ? e.message : "unknown"}`);
      setTranscriptResults([]);
    } finally {
      setSearching(false);
    }
  }, []);

  useEffect(() => {
    if (filters.searchMode === "transcript" && filters.search.trim().length >= 3) {
      const t = setTimeout(() => runTranscriptSearch(filters.search.trim()), 400);
      return () => clearTimeout(t);
    }
    setTranscriptResults([]);
  }, [filters.search, filters.searchMode, runTranscriptSearch]);

  const viewSession = async (id: string) => {
    setSelectedId(id);
    setDetail(null);
    try {
      const d = await api.depotGet(id);
      setDetail(d.data.session);
    } catch {
      setDetail(null);
    }
  };

  const doAction = async (id: string, fn: () => Promise<unknown>) => {
    setBusyId(id);
    setError("");
    try {
      await fn();
      await load(offset);
      await loadStats();
    } catch (e) {
      setError(e instanceof Error ? e.message : "action failed");
    } finally {
      setBusyId(null);
    }
  };

  const startRename = (s: DepotSession) => {
    setRenamingId(s.id);
    setRenameValue(s.title ?? "");
  };

  const submitRename = async () => {
    if (!renamingId || !renameValue.trim()) {
      setRenamingId(null);
      return;
    }
    await doAction(renamingId, () => api.depotRename(renamingId, renameValue.trim()));
    setRenamingId(null);
  };

  const confirmDelete = (s: DepotSession) => {
    if (!window.confirm(`Permanently delete session '${s.title || s.id}'? Messages and files cascade. No recovery.`)) {
      return;
    }
    doAction(s.id, () => api.depotDelete(s.id));
  };

  const fmtTokens = (n?: number | null) => {
    if (!n) return "—";
    return n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1_000 ? `${(n / 1_000).toFixed(0)}k` : String(n);
  };

  const inTranscriptMode = filters.searchMode === "transcript" && filters.search.trim().length >= 3;
  const hasNext = offset + PAGE_SIZE < total;
  const hasPrev = offset > 0;

  const topCostLabel = useMemo(() => {
    if (!stats || stats.top_cost.length === 0) return null;
    const t = stats.top_cost[0];
    return { title: t.title || t.id, cost: t.cost };
  }, [stats]);

  return (
    <div data-testid="depot-page" className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Database className="w-6 h-6 text-accent" />
            Session Depot
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            {total} sessions in the opencode depot (offline SQLite) · archive, search, rename, delete
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            load(offset);
            loadStats();
          }}
          className="p-2 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="Refresh"
          aria-label="Refresh depot"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4" data-testid="depot-stats">
          <div className="bg-surface-light border border-surface-border rounded-xl p-3" data-testid="depot-stat-total">
            <div className="text-xs text-zinc-500 uppercase tracking-wider">Total</div>
            <div className="text-xl font-semibold">{stats.totals.total}</div>
          </div>
          <div className="bg-surface-light border border-surface-border rounded-xl p-3" data-testid="depot-stat-active">
            <div className="text-xs text-zinc-500 uppercase tracking-wider">Active</div>
            <div className="text-xl font-semibold text-green-400">{stats.totals.active}</div>
          </div>
          <div
            className="bg-surface-light border border-surface-border rounded-xl p-3"
            data-testid="depot-stat-archived"
          >
            <div className="text-xs text-zinc-500 uppercase tracking-wider">Archived</div>
            <div className="text-xl font-semibold text-amber-400">{stats.totals.archived}</div>
          </div>
          <div className="bg-surface-light border border-surface-border rounded-xl p-3" data-testid="depot-stat-tokens">
            <div className="text-xs text-zinc-500 uppercase tracking-wider flex items-center gap-1">
              <Layers className="w-3 h-3" /> Tokens
            </div>
            <div className="text-xl font-semibold">
              {fmtTokens(stats.totals.tokens_input + stats.totals.tokens_output)}
            </div>
          </div>
          <div className="bg-surface-light border border-surface-border rounded-xl p-3" data-testid="depot-stat-cost">
            <div className="text-xs text-zinc-500 uppercase tracking-wider flex items-center gap-1">
              <Coins className="w-3 h-3" /> Cost
            </div>
            <div className="text-xl font-semibold">${stats.totals.total_cost.toFixed(2)}</div>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2 mb-4 px-3 py-2 bg-surface-light border border-surface-border rounded-lg">
        <select
          value={filters.status}
          onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value as Filters["status"] }))}
          className="bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs focus:outline-none focus:border-accent/50"
          data-testid="depot-status-filter"
          aria-label="Filter by archive status"
        >
          <option value="all">All sessions</option>
          <option value="active">Active</option>
          <option value="archived">Archived</option>
        </select>
        <div className="flex items-center gap-1 bg-zinc-800 border border-zinc-700 rounded-md px-1 py-0.5">
          <button
            type="button"
            onClick={() => setFilters((f) => ({ ...f, searchMode: "title" }))}
            className={`px-2 py-1 rounded text-[10px] uppercase tracking-wider transition-colors ${
              filters.searchMode === "title" ? "bg-accent/20 text-accent" : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            Title
          </button>
          <button
            type="button"
            onClick={() => setFilters((f) => ({ ...f, searchMode: "transcript" }))}
            className={`px-2 py-1 rounded text-[10px] uppercase tracking-wider transition-colors ${
              filters.searchMode === "transcript" ? "bg-accent/20 text-accent" : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            Transcript
          </button>
        </div>
        <div className="relative flex-1 min-w-52">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
          <input
            type="text"
            value={filters.search}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
            placeholder={
              filters.searchMode === "transcript"
                ? "Search session transcripts (3+ chars)..."
                : "Filter by session title..."
            }
            data-testid="depot-search"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md pl-8 pr-2 py-1.5 text-xs focus:outline-none focus:border-accent/50"
          />
        </div>
        {searching && <Loader2 className="w-3.5 h-3.5 animate-spin text-zinc-500" />}
        <span className="text-xs text-zinc-500">
          {inTranscriptMode ? `${transcriptResults.length} transcript matches` : `${total} shown`}
        </span>
      </div>

      {topCostLabel && (
        <div className="text-xs text-zinc-600 mb-3">
          Most expensive session: <span className="text-zinc-400">{topCostLabel.title}</span> — $
          {topCostLabel.cost.toFixed(2)}
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded-lg text-sm text-red-400">{error}</div>
      )}

      {loading ? (
        <div className="flex justify-center py-12 text-zinc-500">
          <Loader2 className="w-6 h-6 animate-spin" />
        </div>
      ) : inTranscriptMode ? (
        <div className="space-y-2">
          {transcriptResults.length === 0 ? (
            <div className="text-center py-12 text-zinc-500">
              <Search className="w-8 h-8 mx-auto mb-3 opacity-40" />
              <p>No transcript matches.</p>
            </div>
          ) : (
            transcriptResults.map((r) => (
              <motion.div
                key={`${r.session_id}-${r.timestamp}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="bg-surface-light border border-surface-border rounded-xl p-4"
                data-testid={`depot-transcript-${r.session_id}`}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <FileText className="w-3.5 h-3.5 text-accent" />
                  <span className="font-mono text-xs text-zinc-200">{r.title || r.session_id}</span>
                  {r.archived && (
                    <span className="text-[10px] uppercase tracking-wider text-amber-400 bg-amber-900/30 rounded px-1.5 py-0.5">
                      archived
                    </span>
                  )}
                  <span className="flex-1" />
                  <span className="text-xs text-zinc-600">{r.timestamp}</span>
                </div>
                <p className="text-xs text-zinc-400 whitespace-pre-wrap">{r.snippet}</p>
                <button
                  type="button"
                  onClick={() => viewSession(r.session_id)}
                  className="mt-2 text-xs text-accent hover:underline"
                >
                  Open session
                </button>
              </motion.div>
            ))
          )}
        </div>
      ) : sessions.length === 0 ? (
        <div className="text-center py-12 text-zinc-500">
          <Database className="w-8 h-8 mx-auto mb-3 opacity-40" />
          <p>No sessions match the current filter.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {sessions.map((s) => (
            <motion.div
              key={s.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className={`bg-surface-light border rounded-xl p-4 ${selectedId === s.id ? "border-accent/50" : "border-surface-border"}`}
              data-testid={`depot-session-${s.id}`}
            >
              <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  {renamingId === s.id ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") submitRename();
                          if (e.key === "Escape") setRenamingId(null);
                        }}
                        ref={(el) => {
                          if (el) el.focus();
                        }}
                        data-testid={`depot-rename-input-${s.id}`}
                        className="flex-1 bg-zinc-800 border border-accent/50 rounded-md px-2 py-1 text-sm focus:outline-none"
                      />
                      <button
                        type="button"
                        onClick={submitRename}
                        className="text-xs px-2 py-1 rounded bg-accent/20 text-accent hover:bg-accent/30"
                      >
                        Save
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-semibold text-zinc-200">{s.title || "(untitled)"}</span>
                      {s.archived && (
                        <span className="text-[10px] uppercase tracking-wider text-amber-400 bg-amber-900/30 rounded px-1.5 py-0.5">
                          archived
                        </span>
                      )}
                    </div>
                  )}
                  <p className="text-xs text-zinc-500 font-mono mt-0.5">{s.id}</p>
                  <p className="text-xs text-zinc-600 mt-0.5 truncate">{s.directory || s.project_id}</p>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 text-xs text-zinc-500">
                    {s.agent && <span>agent: {s.agent}</span>}
                    <span>updated: {s.time_updated_display || "—"}</span>
                    <span>tokens: {fmtTokens((s.tokens_input ?? 0) + (s.tokens_output ?? 0))}</span>
                    <span>cost: ${(s.cost ?? 0).toFixed(2)}</span>
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <button
                    type="button"
                    onClick={() => viewSession(s.id)}
                    className="p-1.5 text-zinc-500 hover:text-zinc-300 transition-colors"
                    title="View details"
                    aria-label={`View ${s.id}`}
                    data-testid={`depot-view-${s.id}`}
                  >
                    {busyId === s.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => startRename(s)}
                    className="p-1.5 text-zinc-500 hover:text-zinc-300 transition-colors"
                    title="Rename"
                    aria-label={`Rename ${s.id}`}
                    data-testid={`depot-rename-${s.id}`}
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                  {s.archived ? (
                    <button
                      type="button"
                      onClick={() => doAction(s.id, () => api.depotUnarchive(s.id))}
                      className="p-1.5 text-zinc-500 hover:text-green-400 transition-colors"
                      title="Unarchive"
                      aria-label={`Unarchive ${s.id}`}
                      data-testid={`depot-unarchive-${s.id}`}
                    >
                      <ArchiveRestore className="w-4 h-4" />
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => doAction(s.id, () => api.depotArchive(s.id))}
                      className="p-1.5 text-zinc-500 hover:text-amber-400 transition-colors"
                      title="Archive"
                      aria-label={`Archive ${s.id}`}
                      data-testid={`depot-archive-${s.id}`}
                    >
                      <Archive className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => confirmDelete(s)}
                    className="p-1.5 text-zinc-500 hover:text-red-400 transition-colors"
                    title="Delete permanently"
                    aria-label={`Delete ${s.id}`}
                    data-testid={`depot-delete-${s.id}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              {selectedId === s.id && detail && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="mt-3 pt-3 border-t border-surface-border"
                >
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-zinc-400">
                    <div>
                      <span className="text-zinc-600 block">Created</span>
                      {detail.time_created_display || "—"}
                    </div>
                    <div>
                      <span className="text-zinc-600 block">Archived</span>
                      {detail.time_archived_display || "—"}
                    </div>
                    <div>
                      <span className="text-zinc-600 block">Messages</span>
                      {detail.message_count ?? "—"}
                    </div>
                    <div>
                      <span className="text-zinc-600 block">Parts</span>
                      {detail.part_count ?? "—"}
                    </div>
                    <div>
                      <span className="text-zinc-600 block">Model</span>
                      {detail.model ? String(detail.model).slice(0, 60) : "—"}
                    </div>
                    <div>
                      <span className="text-zinc-600 block">Agent</span>
                      {detail.agent || "—"}
                    </div>
                    <div>
                      <span className="text-zinc-600 block">Project</span>
                      {detail.project_id || "—"}
                    </div>
                    <div>
                      <span className="text-zinc-600 block">Slug</span>
                      {detail.slug || "—"}
                    </div>
                  </div>
                </motion.div>
              )}
            </motion.div>
          ))}

          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              disabled={!hasPrev}
              onClick={() => load(Math.max(0, offset - PAGE_SIZE))}
              className="flex items-center gap-1 px-3 py-1.5 text-xs bg-zinc-800 hover:bg-zinc-700 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              data-testid="depot-prev"
            >
              <ChevronLeft className="w-3.5 h-3.5" /> Prev
            </button>
            <span className="text-xs text-zinc-500">
              {total === 0 ? "0" : `${offset + 1}-${Math.min(offset + PAGE_SIZE, total)}`} of {total}
            </span>
            <button
              type="button"
              disabled={!hasNext}
              onClick={() => load(offset + PAGE_SIZE)}
              className="flex items-center gap-1 px-3 py-1.5 text-xs bg-zinc-800 hover:bg-zinc-700 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              data-testid="depot-next"
            >
              Next <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
