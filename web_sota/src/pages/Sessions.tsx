import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Download,
  ExternalLink,
  FileText,
  ListTree,
  MessageSquareText,
  Pencil,
  RefreshCw,
  Search,
  Trash2,
} from "lucide-react";
import { api, type Session, type SessionMessage } from "../services/api";

type DetailTab = "overview" | "transcript" | "diff";

interface DiffShape {
  created?: string[];
  modified?: string[];
  deleted?: string[];
  [key: string]: unknown;
}

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
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
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

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.listSessions();
      setSessions(res.data.sessions);
    } catch {
      // backend down - keep last list; empty state covers first load
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

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

  const renameSession = async (s: Session) => {
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

  const deleteSession = async (s: Session) => {
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

  return (
    <div data-testid="sessions-page">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Sessions</h1>
        <button
          type="button"
          data-testid="sessions-refresh"
          onClick={load}
          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
          title="Refresh sessions"
          aria-label="Refresh sessions"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
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
        <div className="text-zinc-500">No active sessions. Run an agent first.</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          <div className="space-y-2 lg:col-span-2">
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
              </motion.div>
            ))}
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
