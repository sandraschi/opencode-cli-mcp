import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ExternalLink, Pencil, RefreshCw, Trash2 } from "lucide-react";
import { api, type Session } from "../services/api";

export function Sessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [sessionDetail, setSessionDetail] = useState<Session | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

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

  const viewSession = async (id: string) => {
    setSelected(id);
    try {
      const res = await api.getSession(id);
      setSessionDetail(res.data.session);
    } catch {
      setSessionDetail(null);
    }
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
      }
      await load();
    } catch (e) {
      setNotice(`Delete failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusyId(null);
    }
  };

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
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="space-y-2">
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
                  <span className="font-mono text-sm truncate">{s.id}</span>
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
                {s.title && <div className="text-xs text-zinc-400 mt-1 truncate">{s.title}</div>}
              </motion.div>
            ))}
          </div>

          <div data-testid="session-detail" className="bg-surface-light border border-surface-border rounded-xl p-4">
            <h2 className="text-sm font-semibold mb-3 text-zinc-400 uppercase tracking-wider">Session Detail</h2>
            {sessionDetail ? (
              <pre className="text-xs font-mono text-zinc-300 whitespace-pre-wrap overflow-auto max-h-96">
                {JSON.stringify(sessionDetail, null, 2)}
              </pre>
            ) : (
              <div className="text-zinc-500 text-sm">Select a session to view details</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
