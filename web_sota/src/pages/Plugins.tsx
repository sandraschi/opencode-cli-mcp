import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Puzzle, Plus, Trash2, RefreshCw, Loader2, FileCode2, FolderOpen, Check, Copy } from "lucide-react";
import { api, type PluginDirEntry, type PluginEntry } from "../services/api";

export function Plugins() {
  const [configPlugins, setConfigPlugins] = useState<PluginEntry[]>([]);
  const [dirPlugins, setDirPlugins] = useState<PluginDirEntry[]>([]);
  const [pluginDir, setPluginDir] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [newPlugin, setNewPlugin] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await api.getOConfig();
      setConfigPlugins(d.data.plugins);
      setDirPlugins(d.data.plugin_dir_plugins);
      setPluginDir(d.data.plugin_dir);
      setError("");
    } catch (e) {
      setError(`Failed to load plugins: ${e instanceof Error ? e.message : "unknown"}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const submitAdd = async () => {
    const plugin = newPlugin.trim();
    if (!plugin) {
      setError("Plugin spec required");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.addPlugin(plugin);
      setShowAdd(false);
      setNewPlugin("");
      await load();
    } catch (e) {
      setError(`Add failed: ${e instanceof Error ? e.message : "unknown"}`);
    } finally {
      setBusy(false);
    }
  };

  const removeConfigPlugin = async (index: number, name: string) => {
    if (!window.confirm(`Remove plugin '${name}' from config?`)) return;
    try {
      await api.removePlugin(index);
      await load();
    } catch (e) {
      setError(`Remove failed: ${e instanceof Error ? e.message : "unknown"}`);
    }
  };

  const copyPath = (path: string, key: string) => {
    navigator.clipboard.writeText(path).then(() => {
      setCopied(key);
      setTimeout(() => setCopied(""), 1500);
    });
  };

  const inputCls =
    "w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50 font-mono";

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Puzzle className="w-6 h-6 text-accent" />
            Plugins
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            opencode plugins — config entries and auto-discovered files in {pluginDir || "~/.config/opencode/plugins/"}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={load}
            className="p-2 text-zinc-400 hover:text-zinc-200 transition-colors"
            title="Refresh"
            aria-label="Refresh plugins"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
          <button
            type="button"
            onClick={() => setShowAdd((v) => !v)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm bg-accent hover:bg-accent-hover text-white transition-colors"
            data-testid="add-plugin"
          >
            <Plus className="w-4 h-4" />
            Add Plugin
          </button>
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
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4">Add Plugin</h2>
          <div className="space-y-3">
            <div>
              <label htmlFor="plugin-spec" className="text-xs text-zinc-500 mb-1 block">
                Plugin spec
              </label>
              <input
                id="plugin-spec"
                type="text"
                value={newPlugin}
                onChange={(e) => setNewPlugin(e.target.value)}
                placeholder="opencode-awesome-plugin@1.2.3  |  ./local-plugin.ts  |  C:\plugins\my-plugin.ts"
                className={inputCls}
                data-testid="plugin-spec"
              />
              <p className="text-xs text-zinc-600 mt-1">
                npm spec (latest), pinned version, or file path. Auto-discovered files in the plugins dir need no config
                entry.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={submitAdd}
                disabled={busy}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm bg-accent hover:bg-accent-hover text-white transition-colors disabled:opacity-50"
                data-testid="plugin-submit"
              >
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                Add
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowAdd(false);
                  setNewPlugin("");
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
      ) : (
        <div className="space-y-8">
          <section>
            <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-2">
              <FileCode2 className="w-4 h-4" />
              Auto-discovered ({dirPlugins.length}) — plugins dir
            </h2>
            {dirPlugins.length === 0 ? (
              <p className="text-sm text-zinc-600">No plugin files in the plugins dir.</p>
            ) : (
              <div className="space-y-2">
                {dirPlugins.map((p) => (
                  <div
                    key={p.name}
                    className="bg-surface-light border border-surface-border rounded-xl p-4"
                    data-testid={`dir-plugin-${p.name}`}
                  >
                    <div className="flex items-center gap-3">
                      <FolderOpen className="w-4 h-4 text-accent" />
                      <div className="flex-1 min-w-0">
                        <span className="font-mono text-sm font-semibold text-zinc-200">{p.name}</span>
                        <p className="text-xs text-zinc-500 font-mono truncate mt-0.5" title={p.path}>
                          {p.path}
                        </p>
                      </div>
                      <span className="text-xs text-zinc-600">{(p.size / 1024).toFixed(1)} KB</span>
                      <button
                        type="button"
                        onClick={() => copyPath(p.path, p.name)}
                        className="p-2 text-zinc-500 hover:text-zinc-300 transition-colors"
                        title="Copy path"
                        aria-label={`Copy path for ${p.name}`}
                      >
                        {copied === p.name ? (
                          <Check className="w-4 h-4 text-green-400" />
                        ) : (
                          <Copy className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section>
            <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Puzzle className="w-4 h-4" />
              Config entries ({configPlugins.length}) — plugin array
            </h2>
            {configPlugins.length === 0 ? (
              <p className="text-sm text-zinc-600">
                No explicit plugin entries in config. Add one with the button above, or drop a .ts/.js file into the
                plugins dir.
              </p>
            ) : (
              <div className="space-y-2">
                {configPlugins.map((p) => (
                  <div
                    key={`${p.index}-${p.name}`}
                    className="bg-surface-light border border-surface-border rounded-xl p-4"
                    data-testid={`config-plugin-${p.index}`}
                  >
                    <div className="flex items-center gap-3">
                      <Puzzle className="w-4 h-4 text-accent" />
                      <div className="flex-1 min-w-0">
                        <span className="font-mono text-sm font-semibold text-zinc-200">{p.name}</span>
                        {p.display !== p.name && (
                          <p className="text-xs text-zinc-500 font-mono truncate mt-0.5" title={p.display}>
                            {p.display}
                          </p>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => removeConfigPlugin(p.index, p.name)}
                        className="p-2 text-zinc-500 hover:text-red-400 transition-colors"
                        title="Remove from config"
                        aria-label={`Remove ${p.name}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}

      <p className="text-xs text-zinc-600 mt-6">
        Note: opencode loads plugins at startup. Restart opencode to apply changes.
      </p>
    </div>
  );
}
