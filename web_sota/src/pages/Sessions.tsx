import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Download,
  ExternalLink,
  FileText,
  LayoutGrid,
  List,
  ListTree,
  MessageSquareText,
  Pencil,
  RefreshCw,
  Search,
  Star,
  Trash2,
} from "lucide-react";
import { api, type DepotSession, type Session, type SessionMessage } from "../services/api";

type DetailTab = "overview" | "transcript" | "diff";

interface DiffShape {
  created?: string[];
  modified?: string[];
  deleted?: string[];
  [key: string]: unknown;
}

const PAGE_SIZE = 25;

interface SessionFilters {
  status: "all" | "active" | "archived";
  search: string;
  project: string;
  sort: "updated" | "created" | "title" | "cost" | "tokens" | "starred";
  timeframe: number | null;
  dateFrom: string;
  dateTo: string;
  starred: "all" | "only" | "none";
  tag: string;
}

type SessionView = "list" | "grid";

function msgText(msg: SessionMessage): string {
  const parts = msg.parts ?? [];
  return parts
    .filter((p) => p.type === "text" && p.text && p.text.trim())
    .map((p) => String(p.text))
    .join("\n");
}

function msgRole(msg: SessionMessage): string {
  return msg.info?.role ?? msg.role ?? "unknown";
}

function modelLabel(model: unknown): string {
  if (typeof model === "string") return model;
  if (model && typeof model === "object") {
    const m = model as { modelID?: unknown; providerID?: unknown };
    return String(m.modelID ?? JSON.stringify(model));
  }
  return "";
}

function msgTs(msg: SessionMessage): number | null {
  const t = msg.info?.time?.created ?? msg.createdAt;
  return typeof t === "number" && t > 0 ? t : null;
}

function fmtTs(ms: number): string {
  return new Date(ms).toLocaleString();
}

function fmtField(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function exportTranscript(title: string, sessionId: string, messages: SessionMessage[]) {
  const lines: string[] = [`# ${title || sessionId}`, "", `Session: ${sessionId}`, "", "---", ""];
  for (const m of messages) {
    const text = msgText(m);
    if (!text.trim()) continue;
    lines.push(`## ${msgRole(m)}`);
    const ts = msgTs(m);
    if (ts) lines.push(`*${fmtTs(ts)}*`);
    lines.push("", text, "", "---", "");
  }
  const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${(title || sessionId).replace(/[^\w\- ]+/g, "").trim() || "session"}-transcript.md`;
  a.click();
  URL.revokeObjectURL(url);
}

export function Sessions() {
  // List rows come from the offline depot (/depot/sessions): full history,
  // filters, sort, pagination. The old live-serve list only showed the serve
  // instance's project-scoped slice (e.g. 4 stale sessions). Detail actions
  // (transcript/diff/rename/delete) still go through live serve when up.
  const [sessions, setSessions] = useState<DepotSession[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<SessionFilters>({
    status: "all",
    search: "",
    project: "",
    sort: "updated",
    timeframe: null,
    dateFrom: "",
    dateTo: "",
    starred: "all",
    tag: "",
  });
  const [tagOptions, setTagOptions] = useState<Array<{ tag: string; count: number }>>([]);
  const [tagDraft, setTagDraft] = useState("");
  const [view, setView] = useState<SessionView>("list");
  const [selected, setSelected] = useState<string | null>(null);
  const [sessionDetail, setSessionDetail] = useState<Session | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [detailTab, setDetailTab] = useState<DetailTab>("overview");
  const [messages, setMessages] = useState<SessionMessage[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [transcriptQuery, setTranscriptQuery] = useState("");
  const [showMetaParts, setShowMetaParts] = useState(false);
  const [diff, setDiff] = useState<DiffShape | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);

  const load = useCallback(
    async (nextOffset = 0) => {
      setLoading(true);
      try {
        const params = new URLSearchParams({
          limit: String(PAGE_SIZE),
          offset: String(nextOffset),
          sort: filters.sort,
        });
        if (filters.status !== "all") params.set("status", filters.status);
        if (filters.search.trim()) params.set("search", filters.search.trim());
        if (filters.project.trim()) params.set("project", filters.project.trim());
        if (filters.dateFrom || filters.dateTo) {
          if (filters.dateFrom) params.set("date_from", filters.dateFrom);
          if (filters.dateTo) params.set("date_to", filters.dateTo);
        } else if (filters.timeframe) {
          params.set("timeframe_days", String(filters.timeframe));
        }
        if (filters.starred === "only") params.set("starred", "true");
        if (filters.starred === "none") params.set("starred", "false");
        if (filters.tag) params.set("tag", filters.tag);
        const res = await api.depotList(params.toString());
        setSessions(res.data.sessions);
        setTotal(res.data.total);
        setOffset(nextOffset);
      } catch {
        // backend down - keep last list; empty state covers first load
      } finally {
        setLoading(false);
      }
    },
    [
      filters.status,
      filters.search,
      filters.project,
      filters.sort,
      filters.timeframe,
      filters.dateFrom,
      filters.dateTo,
      filters.starred,
      filters.tag,
    ],
  );

  const loadTags = useCallback(async () => {
    try {
      const res = await api.depotTags();
      setTagOptions(res.data.tags);
    } catch {
      setTagOptions([]);
    }
  }, []);

  useEffect(() => {
    load(0);
  }, [load]);

  useEffect(() => {
    loadTags();
  }, [loadTags]);

  const refreshRowMeta = async (id: string) => {
    await load(offset);
    void loadTags();
    if (selected === id) void viewSession(id);
  };

  const toggleStar = async (s: DepotSession) => {
    try {
      await api.starSession(s.id, !s.starred);
      await refreshRowMeta(s.id);
    } catch (e) {
      setNotice(`Star failed: ${e instanceof Error ? e.message : "unknown"}`);
    }
  };

  const addTag = async (s: DepotSession) => {
    const value = tagDraft.trim();
    if (!value) return;
    try {
      await api.addSessionTags(s.id, [value]);
      setTagDraft("");
      await refreshRowMeta(s.id);
    } catch (e) {
      setNotice(`Tag failed: ${e instanceof Error ? e.message : "unknown"}`);
    }
  };

  const removeTag = async (s: DepotSession, tag: string) => {
    try {
      await api.removeSessionTag(s.id, tag);
      await refreshRowMeta(s.id);
    } catch (e) {
      setNotice(`Untag failed: ${e instanceof Error ? e.message : "unknown"}`);
    }
  };

  const exportSession = async (s: DepotSession, format: "md" | "html" | "docx") => {
    try {
      const res = await api.exportSession(s.id, format);
      setNotice(`Exported ${format.toUpperCase()} -> ${res.data.path}`);
    } catch (e) {
      setNotice(`Export failed: ${e instanceof Error ? e.message : "unknown"}`);
    }
  };

  const sendToMemops = async (s: DepotSession) => {
    try {
      const res = await api.sendSessionToMemops(s.id, s.tags ?? []);
      setNotice(`memops: ${res.data.path} - ${res.data.next_step}`);
    } catch (e) {
      setNotice(`memops failed: ${e instanceof Error ? e.message : "unknown"}`);
    }
  };

  const loadMessages = useCallback(async (id: string) => {
    setMessagesLoading(true);
    try {
      const res = await api.getSessionMessages(id, 300);
      setMessages(res.data.messages ?? []);
    } catch {
      setMessages([]);
    } finally {
      setMessagesLoading(false);
    }
  }, []);

  const loadDiff = useCallback(async (id: string) => {
    setDiffLoading(true);
    try {
      const res = await api.getSessionDiff(id);
      setDiff(res.data.diff ?? {});
    } catch {
      setDiff(null);
    } finally {
      setDiffLoading(false);
    }
  }, []);

  const viewSession = async (id: string) => {
    setSelected(id);
    setDetailTab("overview");
    setTranscriptQuery("");
    setMessages([]);
    setDiff(null);
    try {
      const res = await api.getSession(id);
      setSessionDetail(res.data.session);
    } catch {
      setSessionDetail(null);
    }
  };

  const openTab = (tab: DetailTab) => {
    setDetailTab(tab);
    if (tab === "transcript" && messages.length === 0 && selected) loadMessages(selected);
    if (tab === "diff" && diff === null && selected) loadDiff(selected);
  };

  const renameSession = async (s: { id: string; title?: string | null }) => {
    const title = window.prompt(`Rename session ${s.id}`, s.title ?? "");
    if (title === null || !title.trim()) return;
    setBusyId(s.id);
    setNotice(null);
    try {
      await api.renameSession(s.id, title.trim());
      setNotice(`Renamed ${s.id} -> ${title.trim()}`);
      await load();
      if (selected === s.id) await viewSession(s.id);
    } catch (e) {
      setNotice(`Rename failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusyId(null);
    }
  };

  const deleteSession = async (s: { id: string; title?: string | null }) => {
    if (
      !window.confirm(
        `Permanently delete session '${s.title || s.id}'? All messages and file diffs cascade. No recovery.`,
      )
    ) {
      return;
    }
    setBusyId(s.id);
    setNotice(null);
    try {
      await api.deleteSession(s.id);
      setNotice(`Deleted ${s.id}`);
      if (selected === s.id) {
        setSelected(null);
        setSessionDetail(null);
        setMessages([]);
      }
      await load();
    } catch (e) {
      setNotice(`Delete failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusyId(null);
    }
  };

  const filteredMessages = useMemo(() => {
    const q = transcriptQuery.trim().toLowerCase();
    if (!q) return messages;
    return messages.filter((m) => {
      if (msgText(m).toLowerCase().includes(q)) return true;
      return String(msgRole(m)).toLowerCase().includes(q);
    });
  }, [messages, transcriptQuery]);

  const overviewEntries = useMemo(() => {
    if (!sessionDetail) return [];
    const keys = [
      "id",
      "title",
      "agent",
      "model",
      "version",
      "directory",
      "project_id",
      "time_created",
      "time_updated",
      "time_archived",
      "time_compacting",
      "cost",
      "tokens_input",
      "tokens_output",
      "tokens_reasoning",
      "tokens_cache_read",
      "tokens_cache_write",
      "share_url",
      "permission",
    ];
    return keys
      .filter((k) => sessionDetail[k] !== undefined && sessionDetail[k] !== null)
      .map((k) => {
        let v = sessionDetail[k] as unknown;
        if (
          (k === "time_created" || k === "time_updated" || k === "time_archived" || k === "time_compacting") &&
          typeof v === "number"
        ) {
          v = fmtTs(v);
        }
        if (typeof v === "object") v = JSON.stringify(v);
        return { key: k, value: String(v) };
      });
  }, [sessionDetail]);

  const diffEntries = useMemo(() => {
    if (!diff) return [];
    const out: Array<{ kind: string; files: string[] }> = [];
    for (const kind of ["created", "modified", "deleted"]) {
      const files = (diff[kind] ?? []) as string[];
      if (files.length) out.push({ kind, files });
    }
    return out;
  }, [diff]);

  const tabButton = (tab: DetailTab, label: string, icon: React.ReactNode) => (
    <button
      type="button"
      data-testid={`session-tab-${tab}`}
      onClick={() => openTab(tab)}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-colors ${
        detailTab === tab ? "bg-accent/20 text-accent" : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50"
      }`}
    >
      {icon}
      {label}
    </button>
  );

  const selectedRow = useMemo(
    () => sessions.find((s) => s.id === (sessionDetail?.id ?? selected)) ?? null,
    [sessions, sessionDetail, selected],
  );

  return (
    <div data-testid="sessions-page">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">Sessions</h1>
          <p className="text-sm text-zinc-500 mt-1" data-testid="sessions-count">
            {total} sessions · offline depot
          </p>
        </div>
        <div className="flex items-center gap-2">
          <fieldset className="flex items-center rounded-lg overflow-hidden border border-zinc-700">
            <legend className="sr-only">View</legend>
            <button
              type="button"
              data-testid="sessions-view-list"
              onClick={() => setView("list")}
              className={`p-2 transition-colors ${view === "list" ? "bg-zinc-700 text-zinc-100" : "text-zinc-500 hover:text-zinc-300"}`}
              title="List view"
              aria-label="List view"
              aria-pressed={view === "list"}
            >
              <List className="w-4 h-4" />
            </button>
            <button
              type="button"
              data-testid="sessions-view-grid"
              onClick={() => setView("grid")}
              className={`p-2 transition-colors ${view === "grid" ? "bg-zinc-700 text-zinc-100" : "text-zinc-500 hover:text-zinc-300"}`}
              title="Grid view"
              aria-label="Grid view"
              aria-pressed={view === "grid"}
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
          </fieldset>
          <button
            type="button"
            data-testid="sessions-refresh"
            onClick={() => load(offset)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
            title="Refresh sessions"
            aria-label="Refresh sessions"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-4 px-3 py-2 bg-surface-light border border-surface-border rounded-lg">
        <select
          value={filters.status}
          onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value as SessionFilters["status"] }))}
          className="bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs focus:outline-none focus:border-accent/50"
          data-testid="sessions-status-filter"
          aria-label="Filter by archive status"
        >
          <option value="all">All sessions</option>
          <option value="active">Active</option>
          <option value="archived">Archived</option>
        </select>
        <select
          value={filters.sort}
          onChange={(e) => setFilters((f) => ({ ...f, sort: e.target.value as SessionFilters["sort"] }))}
          className="bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs focus:outline-none focus:border-accent/50"
          data-testid="sessions-sort"
          aria-label="Sort sessions"
        >
          <option value="updated">Recently updated</option>
          <option value="created">Recently created</option>
          <option value="title">Title A-Z</option>
          <option value="cost">Highest cost</option>
          <option value="tokens">Most tokens</option>
          <option value="starred">Favourites first</option>
        </select>
        <select
          value={filters.dateFrom || filters.dateTo ? "custom" : (filters.timeframe ?? 0)}
          onChange={(e) =>
            setFilters((f) =>
              e.target.value === "custom"
                ? { ...f }
                : { ...f, timeframe: e.target.value === "0" ? null : Number(e.target.value), dateFrom: "", dateTo: "" },
            )
          }
          className="bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs focus:outline-none focus:border-accent/50"
          data-testid="sessions-timeframe"
          aria-label="Time range"
        >
          <option value="0">All time</option>
          <option value="1">Last 24 hours</option>
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="90">Last 90 days</option>
          <option value="custom">Custom range</option>
        </select>
        <input
          type="date"
          value={filters.dateFrom}
          onChange={(e) => setFilters((f) => ({ ...f, dateFrom: e.target.value, timeframe: null }))}
          className="bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-accent/50"
          data-testid="sessions-date-from"
          aria-label="From date"
          title="From date (overrides preset)"
        />
        <input
          type="date"
          value={filters.dateTo}
          onChange={(e) => setFilters((f) => ({ ...f, dateTo: e.target.value, timeframe: null }))}
          className="bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-accent/50"
          data-testid="sessions-date-to"
          aria-label="To date"
          title="To date (overrides preset)"
        />
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
          <input
            type="text"
            value={filters.search}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
            placeholder="Title contains..."
            data-testid="sessions-search"
            aria-label="Search titles"
            className="bg-zinc-800 border border-zinc-700 rounded-md pl-8 pr-3 py-1.5 text-xs focus:outline-none focus:border-accent/50"
          />
        </div>
        <input
          type="text"
          value={filters.project}
          onChange={(e) => setFilters((f) => ({ ...f, project: e.target.value }))}
          placeholder="Project / directory..."
          data-testid="sessions-project"
          aria-label="Filter by project"
          className="bg-zinc-800 border border-zinc-700 rounded-md px-3 py-1.5 text-xs focus:outline-none focus:border-accent/50"
        />
        <button
          type="button"
          onClick={() => setFilters((f) => ({ ...f, starred: f.starred === "only" ? "all" : "only" }))}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs border transition-colors ${
            filters.starred === "only"
              ? "border-amber-500/60 bg-amber-500/15 text-amber-300"
              : "border-zinc-700 text-zinc-400 hover:text-zinc-200"
          }`}
          data-testid="sessions-starred-filter"
          aria-pressed={filters.starred === "only"}
          title="Show favourites only"
        >
          <Star className={`w-3.5 h-3.5 ${filters.starred === "only" ? "fill-amber-400 text-amber-400" : ""}`} />
          Favourites
        </button>
        <select
          value={filters.tag}
          onChange={(e) => setFilters((f) => ({ ...f, tag: e.target.value }))}
          className="bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs focus:outline-none focus:border-accent/50"
          data-testid="sessions-tag-filter"
          aria-label="Filter by tag"
        >
          <option value="">All tags</option>
          {tagOptions.map((t) => (
            <option key={t.tag} value={t.tag}>
              {t.tag} ({t.count})
            </option>
          ))}
        </select>
      </div>

      {notice && (
        <div
          className="mb-4 px-3 py-2 text-sm rounded-lg border border-surface-border bg-surface-light text-zinc-300"
          data-testid="sessions-notice"
        >
          {notice}
        </div>
      )}

      {loading ? (
        <div className="text-zinc-500">Loading sessions...</div>
      ) : sessions.length === 0 ? (
        <div className="text-zinc-500" data-testid="sessions-empty">
          No sessions match these filters. Try widening the time range or clearing the search.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          <div
            className={
              view === "grid"
                ? "lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-2 content-start"
                : "space-y-2 lg:col-span-2"
            }
          >
            {sessions.map((s) => (
              <motion.div
                key={s.id}
                data-testid={`session-${s.id}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  selected === s.id
                    ? "border-accent bg-accent/5"
                    : "border-surface-border bg-surface-light hover:border-zinc-600"
                }`}
                onClick={() => viewSession(s.id)}
              >
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`text-sm truncate ${s.title ? "font-semibold text-zinc-100" : "font-mono text-zinc-300"}`}
                  >
                    {s.title || s.id}
                  </span>
                  <span className="flex items-center gap-1 shrink-0">
                    <button
                      type="button"
                      data-testid={`session-star-${s.id}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        void toggleStar(s);
                      }}
                      className={`p-1.5 rounded-md transition-colors hover:bg-zinc-800 ${
                        s.starred ? "text-amber-400" : "text-zinc-500 hover:text-amber-400"
                      }`}
                      title={s.starred ? "Remove from favourites" : "Add to favourites"}
                      aria-label={`${s.starred ? "Unstar" : "Star"} session ${s.id}`}
                      aria-pressed={Boolean(s.starred)}
                    >
                      <Star className={`w-3.5 h-3.5 ${s.starred ? "fill-amber-400" : ""}`} />
                    </button>
                    <button
                      type="button"
                      data-testid={`session-rename-${s.id}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        renameSession(s);
                      }}
                      disabled={busyId === s.id}
                      className="p-1.5 rounded-md text-zinc-500 hover:text-amber-400 hover:bg-zinc-800 transition-colors"
                      title="Rename session"
                      aria-label={`Rename session ${s.id}`}
                    >
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      data-testid={`session-delete-${s.id}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteSession(s);
                      }}
                      disabled={busyId === s.id}
                      className="p-1.5 rounded-md text-zinc-500 hover:text-red-400 hover:bg-zinc-800 transition-colors"
                      title="Delete session (permanent)"
                      aria-label={`Delete session ${s.id}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                    <ExternalLink className="w-3.5 h-3.5 text-zinc-500" />
                  </span>
                </div>
                {s.title && <div className="text-xs text-zinc-600 font-mono mt-0.5 truncate">{s.id}</div>}
                {Boolean(s.tags?.length) && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {(s.tags ?? []).map((t) => (
                      <span
                        key={t}
                        className="text-[10px] px-1.5 py-0.5 rounded bg-sky-900/50 text-sky-300 border border-sky-800/60"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                )}
                <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                  {s.archived && (
                    <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-900/60 text-amber-300">
                      archived
                    </span>
                  )}
                  {s.agent && <span className="text-[10px] text-zinc-500">agent: {s.agent}</span>}
                  {s.time_updated_display && (
                    <span className="text-[10px] text-zinc-600">{s.time_updated_display}</span>
                  )}
                </div>
                {s.directory && view === "list" && (
                  <div className="text-[11px] text-zinc-600 font-mono mt-0.5 truncate" title={s.directory}>
                    {s.directory}
                  </div>
                )}
              </motion.div>
            ))}
            <div className="flex items-center justify-between pt-2" data-testid="sessions-pagination">
              <button
                type="button"
                data-testid="sessions-prev"
                disabled={offset === 0}
                onClick={() => load(Math.max(0, offset - PAGE_SIZE))}
                className="px-3 py-1.5 text-xs bg-zinc-800 hover:bg-zinc-700 rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Prev
              </button>
              <span className="text-xs text-zinc-500">
                {total === 0 ? "0" : `${offset + 1}–${offset + sessions.length}`} of {total}
              </span>
              <button
                type="button"
                data-testid="sessions-next"
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => load(offset + PAGE_SIZE)}
                className="px-3 py-1.5 text-xs bg-zinc-800 hover:bg-zinc-700 rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>

          <div
            data-testid="session-detail"
            className="lg:col-span-3 bg-surface-light border border-surface-border rounded-xl p-4 min-h-[24rem]"
          >
            {!sessionDetail ? (
              <div className="text-zinc-500 text-sm">Select a session to view it</div>
            ) : (
              <>
                <div className="flex items-center justify-between gap-3 mb-3">
                  <div className="min-w-0">
                    <h2 className="font-semibold text-sm truncate">{sessionDetail.title || sessionDetail.id}</h2>
                    <span className="font-mono text-xs text-zinc-600">{sessionDetail.id}</span>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {tabButton("overview", "Overview", <ListTree className="w-3.5 h-3.5" />)}
                    {tabButton("transcript", "Transcript", <MessageSquareText className="w-3.5 h-3.5" />)}
                    {tabButton("diff", "Diff", <FileText className="w-3.5 h-3.5" />)}
                    {messages.length > 0 && (
                      <button
                        type="button"
                        data-testid="session-export"
                        onClick={() => exportTranscript(sessionDetail.title ?? "", sessionDetail.id, messages)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition-colors"
                        title="Export transcript as markdown"
                      >
                        <Download className="w-3.5 h-3.5" />
                        Export
                      </button>
                    )}
                  </div>
                </div>

                {selectedRow && (
                  <div
                    className="mb-3 pb-3 border-b border-surface-border/60 flex flex-wrap items-center gap-2"
                    data-testid="session-curation"
                  >
                    <button
                      type="button"
                      onClick={() => void toggleStar(selectedRow)}
                      data-testid="session-detail-star"
                      className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs border transition-colors ${
                        selectedRow.starred
                          ? "border-amber-500/60 bg-amber-500/15 text-amber-300"
                          : "border-zinc-700 text-zinc-400 hover:text-zinc-200"
                      }`}
                      aria-pressed={Boolean(selectedRow.starred)}
                    >
                      <Star className={`w-3.5 h-3.5 ${selectedRow.starred ? "fill-amber-400" : ""}`} />
                      {selectedRow.starred ? "Favourite" : "Star"}
                    </button>
                    {(selectedRow.tags ?? []).map((t) => (
                      <span
                        key={t}
                        className="flex items-center gap-1 text-[11px] px-1.5 py-1 rounded bg-sky-900/50 text-sky-300 border border-sky-800/60"
                      >
                        {t}
                        <button
                          type="button"
                          onClick={() => void removeTag(selectedRow, t)}
                          className="hover:text-red-300"
                          aria-label={`Remove tag ${t}`}
                          title={`Remove tag ${t}`}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                    <input
                      type="text"
                      value={tagDraft}
                      onChange={(e) => setTagDraft(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          void addTag(selectedRow);
                        }
                      }}
                      placeholder="add tag + Enter"
                      data-testid="session-tag-input"
                      aria-label="Add a tag"
                      className="w-40 bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs focus:outline-none focus:border-accent/50"
                    />
                    <span className="flex-1" />
                    {(["md", "html", "docx"] as const).map((fmt) => (
                      <button
                        key={fmt}
                        type="button"
                        onClick={() => void exportSession(selectedRow, fmt)}
                        data-testid={`session-export-${fmt}`}
                        className="px-2 py-1.5 rounded-md text-[11px] uppercase bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition-colors"
                        title={`Save as ${fmt.toUpperCase()}`}
                      >
                        {fmt}
                      </button>
                    ))}
                    <button
                      type="button"
                      onClick={() => void sendToMemops(selectedRow)}
                      data-testid="session-memops"
                      className="px-2 py-1.5 rounded-md text-[11px] bg-emerald-900/50 hover:bg-emerald-800/60 text-emerald-300 border border-emerald-800/60 transition-colors"
                      title="Write a frontmatter note into the advanced-memory inbox"
                    >
                      → memops
                    </button>
                  </div>
                )}

                {detailTab === "overview" && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5">
                    {overviewEntries.map((e) => (
                      <div key={e.key} className="flex justify-between gap-3 py-1 border-b border-surface-border/60">
                        <span className="text-xs text-zinc-500 shrink-0">{fmtField(e.key)}</span>
                        <span className="text-xs text-zinc-300 font-mono text-right break-all">{e.value}</span>
                      </div>
                    ))}
                  </div>
                )}

                {detailTab === "transcript" && (
                  <div className="flex flex-col h-[28rem]">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="relative flex-1">
                        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
                        <input
                          type="text"
                          value={transcriptQuery}
                          onChange={(e) => setTranscriptQuery(e.target.value)}
                          placeholder={`Search ${messages.length} messages...`}
                          data-testid="session-transcript-search"
                          className="w-full bg-zinc-800 border border-zinc-700 rounded-md pl-8 pr-3 py-1.5 text-xs focus:outline-none focus:border-accent/50"
                        />
                      </div>
                      <label className="flex items-center gap-1.5 text-xs text-zinc-500 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={showMetaParts}
                          onChange={(e) => setShowMetaParts(e.target.checked)}
                          className="accent-amber-500"
                          data-testid="session-show-meta"
                        />
                        reasoning/tools
                      </label>
                    </div>
                    <div className="flex-1 overflow-y-auto space-y-2 pr-1" data-testid="session-transcript">
                      {messagesLoading && messages.length === 0 ? (
                        <div className="text-zinc-500 text-sm py-8 text-center">Loading transcript...</div>
                      ) : filteredMessages.length === 0 ? (
                        <div className="text-zinc-500 text-sm py-8 text-center">
                          {transcriptQuery ? "No messages match the search." : "No text messages in this session."}
                        </div>
                      ) : (
                        filteredMessages.map((m, i) => {
                          const text = msgText(m);
                          const metaText = showMetaParts
                            ? (m.parts ?? [])
                                .filter((p) => p.type !== "text" && p.text)
                                .map((p) => `[${p.type}] ${String(p.text)}`)
                                .join("\n")
                            : "";
                          if (!text && !metaText) return null;
                          const role = msgRole(m);
                          const ts = msgTs(m);
                          const messageKey = String(m.info?.id ?? m.info?.time?.created ?? `${msgRole(m)}-${i}`);
                          return (
                            <motion.div
                              key={messageKey}
                              initial={{ opacity: 0 }}
                              animate={{ opacity: 1 }}
                              data-testid={`session-message-${i}`}
                              className={`rounded-lg border p-3 ${
                                role === "user"
                                  ? "border-surface-border bg-zinc-800/40"
                                  : "border-surface-border bg-surface-light"
                              }`}
                            >
                              <div className="flex items-center gap-2 mb-1">
                                <span
                                  className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                                    role === "user" ? "bg-amber-900/60 text-amber-300" : "bg-zinc-800 text-zinc-300"
                                  }`}
                                >
                                  {role}
                                </span>
                                {m.info?.agent && (
                                  <span className="text-[10px] text-zinc-600">agent: {String(m.info.agent)}</span>
                                )}
                                {modelLabel(m.info?.model) && (
                                  <span className="text-[10px] text-zinc-600">model: {modelLabel(m.info?.model)}</span>
                                )}
                                <span className="flex-1" />
                                {ts && <span className="text-[10px] text-zinc-600">{fmtTs(ts)}</span>}
                              </div>
                              {text && (
                                <p className="text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed">{text}</p>
                              )}
                              {metaText && (
                                <pre className="mt-2 text-[10px] text-zinc-500 whitespace-pre-wrap font-mono border-t border-surface-border pt-2">
                                  {metaText}
                                </pre>
                              )}
                            </motion.div>
                          );
                        })
                      )}
                    </div>
                  </div>
                )}

                {detailTab === "diff" && (
                  <div className="space-y-3" data-testid="session-diff">
                    {diffLoading && diff === null ? (
                      <div className="text-zinc-500 text-sm py-8 text-center">Loading diff...</div>
                    ) : diffEntries.length === 0 ? (
                      <div className="text-zinc-500 text-sm py-8 text-center">
                        No file changes recorded for this session.
                      </div>
                    ) : (
                      diffEntries.map((d) => (
                        <div key={d.kind}>
                          <div
                            className={`text-[10px] font-bold uppercase tracking-wider mb-1 ${
                              d.kind === "created"
                                ? "text-emerald-400"
                                : d.kind === "deleted"
                                  ? "text-red-400"
                                  : "text-amber-400"
                            }`}
                          >
                            {d.kind} ({d.files.length})
                          </div>
                          <div className="space-y-0.5">
                            {d.files.map((f) => (
                              <div key={f} className="font-mono text-xs text-zinc-400 truncate">
                                {f}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
