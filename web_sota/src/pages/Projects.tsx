import { useCallback, useEffect, useState } from "react";
import { API_BASE } from "../lib/api";
import { motion } from "framer-motion";
import { RefreshCw, ExternalLink, Circle, Rocket, X, Square, Loader2 } from "lucide-react";
import { api } from "../services/api";

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
  const [showForm, setShowForm] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [project, setProject] = useState("");
  const [wait, setWait] = useState(false);
  const [launching, setLaunching] = useState(false);
  const [launchError, setLaunchError] = useState("");
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/runs`);
      const json = await res.json();
      setRuns(json.data?.runs ?? []);
    } catch {
      setRuns([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Live-poll while any run is running/queued so statuses stay current.
  useEffect(() => {
    const active = runs.some((r) => r.status === "running" || r.status === "queued");
    if (!active) return;
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, [runs, load]);

  const viewRun = async (jobId: string) => {
    setSelected(jobId);
    try {
      const res = await fetch(`${API_BASE}/api/runs/${jobId}`);
      const json = await res.json();
      setRunDetail(json.data?.run ?? null);
    } catch {
      setRunDetail(null);
    }
  };

  const launch = async () => {
    const p = prompt.trim();
    if (!p) return;
    setLaunching(true);
    setLaunchError("");
    try {
      const d = await api.startRun({
        prompt: p,
        project: project.trim() || undefined,
        wait: false,
      });
      setPrompt("");
      setProject("");
      setShowForm(false);
      await load();
      if (d.data?.job_id) {
        setSelected(d.data.job_id);
        viewRun(d.data.job_id);
      }
    } catch (e) {
      setLaunchError(`Launch failed: ${e instanceof Error ? e.message : "unknown"}`);
    } finally {
      setLaunching(false);
    }
  };

  const cancelRun = async (jobId: string) => {
    setCancellingId(jobId);
    try {
      await api.cancelRun(jobId);
      await load();
    } catch {
      // status will refresh on the next poll
    } finally {
      setCancellingId(null);
    }
  };

  const inputCls =
    "w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50";

  return (
    <div data-testid="projects-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Rocket className="w-6 h-6 text-accent" />
            Projects
          </h1>
          <p className="text-sm text-zinc-500 mt-1">Agent runs launched through this server ({runs.length})</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            data-testid="projects-refresh"
            onClick={load}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
            title="Refresh runs"
            aria-label="Refresh runs"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            type="button"
            data-testid="projects-new-run"
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-2 px-4 py-1.5 text-sm bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors"
          >
            {showForm ? <X className="w-4 h-4" /> : <Rocket className="w-4 h-4" />}
            {showForm ? "Close" : "New run"}
          </button>
        </div>
      </div>

      {(showForm || runs.length === 0) && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 bg-surface-light border border-surface-border rounded-xl p-5"
          data-testid="launch-run-form"
        >
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">
            {runs.length === 0 ? "Populate this page — launch your first agent run" : "Launch an agent run"}
          </h2>
          <div className="space-y-3">
            <div>
              <label htmlFor="launch-prompt" className="text-xs text-zinc-500 mb-1 block">
                Prompt
              </label>
              <textarea
                id="launch-prompt"
                data-testid="launch-prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={3}
                placeholder="e.g. Fix the failing tests in src/ and report what changed"
                className={inputCls}
              />
            </div>
            <div>
              <label htmlFor="launch-project" className="text-xs text-zinc-500 mb-1 block">
                Project directory (optional — defaults to opencode's working dir)
              </label>
              <input
                id="launch-project"
                data-testid="launch-project"
                type="text"
                value={project}
                onChange={(e) => setProject(e.target.value)}
                placeholder="D:\Dev\repos\example-repo"
                className={inputCls}
              />
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-zinc-300">
                <input
                  type="checkbox"
                  checked={wait}
                  onChange={(e) => setWait(e.target.checked)}
                  className="accent-accent"
                  data-testid="launch-wait"
                />
                Wait for completion (blocks the request)
              </label>
              <span className="text-xs text-zinc-600">Fire-and-forget is recommended — poll status instead.</span>
            </div>
            {launchError && <div className="text-sm text-red-400">{launchError}</div>}
            <button
              type="button"
              data-testid="launch-run"
              onClick={launch}
              disabled={!prompt.trim() || launching}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm bg-accent hover:bg-accent-hover text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {launching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Rocket className="w-4 h-4" />}
              {launching ? "Launching..." : "Launch agent run"}
            </button>
          </div>
        </motion.div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-zinc-500">
          <Circle className="w-4 h-4 animate-pulse" />
          Loading projects...
        </div>
      ) : runs.length === 0 ? (
        !showForm && (
          <div className="text-zinc-500 py-12 text-center border border-dashed border-surface-border rounded-xl">
            <p className="text-lg mb-1">No agent runs yet</p>
            <p className="text-sm text-zinc-600">Launch a run above to populate this page.</p>
          </div>
        )
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
                data-testid={`project-run-${run.job_id}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-zinc-500">{run.job_id}</span>
                    <StatusBadge status={run.status} />
                    {run.exit_code !== null && run.exit_code !== 0 && (
                      <span className="text-xs text-red-400">exit {run.exit_code}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    {(run.status === "running" || run.status === "queued") && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          cancelRun(run.job_id);
                        }}
                        disabled={cancellingId === run.job_id}
                        className="p-1.5 text-zinc-500 hover:text-red-400 transition-colors disabled:opacity-40"
                        title="Cancel run"
                        aria-label={`Cancel ${run.job_id}`}
                        data-testid={`cancel-run-${run.job_id}`}
                      >
                        {cancellingId === run.job_id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Square className="w-3.5 h-3.5" />
                        )}
                      </button>
                    )}
                    <ExternalLink className="w-3.5 h-3.5 text-zinc-500 flex-shrink-0" />
                  </div>
                </div>
                <div className="text-sm text-zinc-300 truncate">{run.prompt}</div>
                <div className="flex items-center gap-3 mt-1.5 text-xs text-zinc-500">
                  <span>{run.project || "(no project)"}</span>
                  <span>{fmtTimeAgo(run.created_at)}</span>
                  {run.completed_at && <span>{Math.round(run.completed_at - run.created_at)}s duration</span>}
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
                    <div className="mt-0.5">
                      <StatusBadge status={runDetail.status} />
                    </div>
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
