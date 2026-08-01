import { useState } from "react";
import { motion } from "framer-motion";
import { Box, CheckCircle2, AlertCircle, Eye, Terminal, FileJson } from "lucide-react";

export function McpbInstall() {
  const [source, setSource] = useState("");
  const [nameOverride, setNameOverride] = useState("");
  const [dryRun, setDryRun] = useState(true);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const install = async () => {
    if (!source.trim()) return;
    setBusy(true);
    setResult(null);
    setError(null);
    try {
      const r = await fetch("/api/mcpb/install", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source: source.trim(),
          name_override: nameOverride.trim() || null,
          dry_run: dryRun,
        }),
      });
      const data = await r.json();
      if (data.success) setResult(data);
      else setError(data.error || "Install failed");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Box className="w-6 h-6 text-accent" />
          MCPB Install
        </h1>
        <p className="text-sm text-zinc-500 mt-1">
          Install an <code className="text-accent font-mono">.mcpb</code> bundle into your opencode configuration.
        </p>
      </div>

      <motion.section
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-light border border-surface-border rounded-xl p-5 space-y-4"
      >
        <div>
          <label htmlFor="mcpb-source" className="block text-xs text-zinc-500 mb-1">
            MCPB source path
          </label>
          <input
            id="mcpb-source"
            type="text"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder="./dist/arxiv-mcp-v1.0.0.mcpb"
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-accent/50"
          />
          <p className="text-xs text-zinc-600 mt-1">Path to an .mcpb file or an unpacked MCPB directory.</p>
        </div>

        <div>
          <label htmlFor="mcpb-name" className="block text-xs text-zinc-500 mb-1">
            Name override (optional)
          </label>
          <input
            id="mcpb-name"
            type="text"
            value={nameOverride}
            onChange={(e) => setNameOverride(e.target.value)}
            placeholder="arxiv"
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-accent/50"
          />
          <p className="text-xs text-zinc-600 mt-1">
            Override the server name in opencode config. Default: from manifest.
          </p>
        </div>

        <label className="flex items-center gap-2 text-sm text-zinc-400 cursor-pointer">
          <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} className="rounded" />
          Dry run (preview without modifying config)
        </label>

        <button
          type="button"
          onClick={install}
          disabled={busy || !source.trim()}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent/10 text-accent border border-accent/20 hover:bg-accent/15 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
        >
          {busy ? (
            <span className="animate-pulse">Processing...</span>
          ) : dryRun ? (
            <>
              <Eye className="w-4 h-4" />
              Preview
            </>
          ) : (
            <>
              <Terminal className="w-4 h-4" />
              Install
            </>
          )}
        </button>
      </motion.section>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-4 flex items-start gap-3"
        >
          <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-rose-200 font-semibold">Install failed</p>
            <p className="text-xs text-rose-300 mt-1">{error}</p>
          </div>
        </motion.div>
      )}

      {result && (
        <motion.section
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-light border border-surface-border rounded-xl p-5 space-y-3"
        >
          <div className="flex items-center gap-2 text-emerald-400">
            <CheckCircle2 className="w-5 h-5" />
            <span className="text-sm font-semibold">
              {result.dry_run
                ? "Preview ready"
                : result.created
                  ? "Config created"
                  : result.overwritten
                    ? "Server overwritten"
                    : "Server installed"}
            </span>
          </div>

          <div className="text-xs text-zinc-400 space-y-1">
            <p>
              <span className="text-zinc-500">Server:</span>{" "}
              <code className="text-zinc-300 font-mono">{String(result.server_name ?? "")}</code>
            </p>
            <p>
              <span className="text-zinc-500">Config:</span>{" "}
              <code className="text-zinc-300 font-mono">{String(result.config_path ?? "")}</code>
            </p>
            {Boolean(result.dry_run) && <p className="text-amber-400">Dry run -- nothing was written.</p>}
          </div>

          <div>
            <div className="flex items-center gap-1 text-xs text-zinc-500 mb-1">
              <FileJson className="w-3 h-3" />
              Entry that would be / was written
            </div>
            <pre className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 text-xs text-zinc-300 font-mono leading-relaxed overflow-x-auto">
              {JSON.stringify(result.entry, null, 2)}
            </pre>
          </div>

          {!result.dry_run && <p className="text-xs text-zinc-500">Restart opencode for the changes to take effect.</p>}
        </motion.section>
      )}
    </div>
  );
}
