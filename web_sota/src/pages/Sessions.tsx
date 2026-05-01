import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ExternalLink, RefreshCw } from "lucide-react";
import { api, type Session } from "../services/api";

export function Sessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [sessionDetail, setSessionDetail] = useState<Session | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.listSessions();
      setSessions(res.data.sessions);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const viewSession = async (id: string) => {
    setSelected(id);
    try {
      const res = await api.getSession(id);
      setSessionDetail(res.data.session);
    } catch {
      setSessionDetail(null);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Sessions</h1>
        <button
          onClick={load}
          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
          title="Refresh sessions"
          aria-label="Refresh sessions"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

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
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  selected === s.id
                    ? "border-accent bg-accent/5"
                    : "border-surface-border bg-surface-light hover:border-zinc-600"
                }`}
                onClick={() => viewSession(s.id)}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm">{s.id}</span>
                  <ExternalLink className="w-3.5 h-3.5 text-zinc-500" />
                </div>
                {s.title && <div className="text-xs text-zinc-400 mt-1">{s.title}</div>}
              </motion.div>
            ))}
          </div>

          <div className="bg-surface-light border border-surface-border rounded-xl p-4">
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
