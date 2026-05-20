import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { RefreshCw, ExternalLink, Circle } from "lucide-react";

interface Run {
  job_id: string;
  prompt: string;
  project: string | null;
  status: string;
  created_at: number;
  completed_at: number | null;
  exit_code: number | null;
  stdout: string;
  stderr: string;
  error: string | null;
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    completed: "bg-green-500/10 text-green-400 border-green-500/30",
    failed: "bg-red-500/10 text-red-400 border-red-500/30",
    running: "bg-blue-500/10 text-blue-400 border-blue-500/30",
    queued: "bg-zinc-500/10 text-zinc-400 border-zinc-500/30",
    cancelled: "bg-yellow-500/10 text-yellow-400 border-yellow-500/30",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${colors[status] || colors.queued}`}>
      {status}
    </span>
  );
}

function fmtTime(ts: number) {
  const d = new Date(ts * 1000);
  return d.toLocaleString();
}

function fmtTimeAgo(ts: number) {
  const seconds = Math.floor(Date.now() / 1000 - ts);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function Projects() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [runDetail, setRunDetail] = useState<Run | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/runs");
      const json = await res.json();
      setRuns(json.data?.runs ?? []);
    } catch {
      setRuns([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const viewRun = async (jobId: string) => {
    setSelected(jobId);
    try {
      const res = await fetch(`/api/runs/${jobId}`);
      const json = await res.json();
      setRunDetail(json.data?.run ?? null);
    } catch {
      setRunDetail(null);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Projects</h1>
        <button
          onClick={load}
          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
          title="Refresh runs"
          aria-label="Refresh runs"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-zinc-500">
          <Circle className="w-4 h-4 animate-pulse" />
          Loading projects...
        </div>
      ) : runs.length === 0 ? (
        <div className="text-zinc-500 py-12 text-center border border-dashed border-surface-border rounded-xl">
          <p className="text-lg mb-1">No agent runs yet</p>
          <p className="text-sm text-zinc-600">Run an opencode agent first to see projects here.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          <div className="lg:col-span-3 space-y-2">
            {runs.map((run) => (
              <motion.div
                key={run.job_id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  selected === run.job_id
                    ? "border-accent bg-accent/5"
                    : "border-surface-border bg-surface-light hover:border-zinc-600"
                }`}
                onClick={() => viewRun(run.job_id)}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-zinc-500">{run.job_id}</span>
                    <StatusBadge status={run.status} />
                    {run.exit_code !== null && run.exit_code !== 0 && (
                      <span className="text-xs text-red-400">exit {run.exit_code}</span>
                    )}
                  </div>
                  <ExternalLink className="w-3.5 h-3.5 text-zinc-500 flex-shrink-0" />
                </div>
                <div className="text-sm text-zinc-300 truncate">{run.prompt}</div>
                <div className="flex items-center gap-3 mt-1.5 text-xs text-zinc-500">
                  <span>{run.project || "(no project)"}</span>
                  <span>{fmtTimeAgo(run.created_at)}</span>
                  {run.completed_at && (
                    <span>{Math.round(run.completed_at - run.created_at)}s duration</span>
                  )}
                </div>
              </motion.div>
            ))}
          </div>

          <div className="lg:col-span-2 bg-surface-light border border-surface-border rounded-xl p-4">
            <h2 className="text-sm font-semibold mb-3 text-zinc-400 uppercase tracking-wider">Run Details</h2>
            {runDetail ? (
              <div className="space-y-3 text-sm">
                <div>
                  <span className="text-zinc-500 text-xs uppercase">Prompt</span>
                  <p className="text-zinc-200 mt-0.5">{runDetail.prompt}</p>
                </div>
                <div className="flex gap-4">
                  <div>
                    <span className="text-zinc-500 text-xs uppercase">Status</span>
                    <div className="mt-0.5"><StatusBadge status={runDetail.status} /></div>
                  </div>
                  <div>
                    <span className="text-zinc-500 text-xs uppercase">Project</span>
                    <p className="text-zinc-200 mt-0.5">{runDetail.project || "—"}</p>
                  </div>
                  <div>
                    <span className="text-zinc-500 text-xs uppercase">Exit Code</span>
                    <p className="text-zinc-200 mt-0.5">{runDetail.exit_code ?? "—"}</p>
                  </div>
                </div>
                <div>
                  <span className="text-zinc-500 text-xs uppercase">Created</span>
                  <p className="text-zinc-200 mt-0.5">{fmtTime(runDetail.created_at)}</p>
                </div>
                {runDetail.completed_at && (
                  <div>
                    <span className="text-zinc-500 text-xs uppercase">Completed</span>
                    <p className="text-zinc-200 mt-0.5">{fmtTime(runDetail.completed_at)}</p>
                  </div>
                )}
                {runDetail.error && (
                  <div>
                    <span className="text-zinc-500 text-xs uppercase">Error</span>
                    <p className="text-red-400 mt-0.5">{runDetail.error}</p>
                  </div>
                )}
                {(runDetail.stdout || runDetail.stderr) && (
                  <div>
                    <span className="text-zinc-500 text-xs uppercase">Output</span>
                    <pre className="mt-1 text-xs font-mono bg-black/30 rounded-lg p-3 max-h-48 overflow-auto text-zinc-300 whitespace-pre-wrap">
                      {runDetail.stderr || runDetail.stdout || "(empty)"}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-zinc-500 text-sm">Select a run to view details</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
