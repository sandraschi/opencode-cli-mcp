import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Cpu,
  Cloud,
  Sun,
  Moon,
  Save,
  Check,
  Wifi,
  WifiOff,
  Server,
  RefreshCw,
} from "lucide-react";
import { api } from "../services/api";

interface SettingsData {
  theme: string;
  llm_provider: string;
  local_endpoint: string;
  local_model: string;
  cloud_provider: string;
  cloud_key: string;
  cloud_model: string;
  opencode_serve_url: string;
}

const DEFAULT_SETTINGS: SettingsData = {
  theme: "dark",
  llm_provider: "local",
  local_endpoint: "http://127.0.0.1:11434",
  local_model: "llama3.2",
  cloud_provider: "openai",
  cloud_key: "",
  cloud_model: "gpt-4o",
  opencode_serve_url: "http://127.0.0.1:4096",
};

function applyTheme(theme: string) {
  if (theme === "light") {
    document.documentElement.classList.remove("dark");
  } else {
    document.documentElement.classList.add("dark");
  }
}

export function Settings() {
  const [settings, setSettings] = useState<SettingsData>(DEFAULT_SETTINGS);
  const [originalSettings, setOriginalSettings] = useState<SettingsData>(DEFAULT_SETTINGS);
  const [ollamaOk, setOllamaOk] = useState<boolean | null>(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const hasChanges = JSON.stringify(settings) !== JSON.stringify(originalSettings);

  useEffect(() => {
    api
      .getSettings()
      .then((s) => {
        const merged = { ...DEFAULT_SETTINGS, ...s } as SettingsData;
        setSettings(merged);
        setOriginalSettings(merged);
        applyTheme(merged.theme);
      })
      .catch(console.error);
    api
      .getOllamaStatus()
      .then((d) => setOllamaOk(d.data.running))
      .catch(() => setOllamaOk(false));
  }, []);

  const handleSave = async () => {
    setError("");
    try {
      const res = await api.updateSettings(settings as unknown as Record<string, unknown>);
      if (res.success) {
        setOriginalSettings({ ...settings });
        applyTheme(settings.theme);
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      } else {
        setError("Save failed");
      }
    } catch (err) {
      setError(`Save failed: ${err instanceof Error ? err.message : "unknown"}`);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Settings</h1>
        <button
          onClick={handleSave}
          disabled={!hasChanges}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${
            hasChanges
              ? "bg-accent hover:bg-accent-hover text-white"
              : "bg-zinc-800 text-zinc-500 cursor-not-allowed"
          }`}
          title={hasChanges ? "Save settings" : "No changes to save"}
          aria-label="Save settings"
        >
          {saved ? (
            <>
              <Check className="w-4 h-4" />
              Saved
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              Save
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded-lg text-sm text-red-400">
          {error}
        </div>
      )}

      <div className="space-y-6">
        <motion.section
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-light border border-surface-border rounded-xl p-5"
        >
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Sun className="w-4 h-4" />
            Appearance
          </h2>
          <div className="flex items-center gap-3">
            <Moon className="w-5 h-5 text-zinc-400" />
            <button
              onClick={() => {
                const next = settings.theme === "dark" ? "light" : "dark";
                setSettings((s) => ({ ...s, theme: next }));
              }}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                settings.theme === "dark" ? "bg-accent" : "bg-zinc-600"
              }`}
              role="switch"
              aria-checked={settings.theme === "dark"}
              aria-label="Toggle dark mode"
            >
              <div
                className={`absolute w-5 h-5 bg-white rounded-full top-0.5 transition-transform ${
                  settings.theme === "dark" ? "translate-x-6" : "translate-x-0.5"
                }`}
              />
            </button>
            <span className="text-sm text-zinc-300">
              {settings.theme === "dark" ? "Dark mode" : "Light mode"}
            </span>
          </div>
        </motion.section>

        <motion.section
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="bg-surface-light border border-surface-border rounded-xl p-5"
        >
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Server className="w-4 h-4" />
            Opencode Serve
          </h2>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-zinc-500 mb-1 block">Server URL</label>
              <input
                type="text"
                value={settings.opencode_serve_url}
                onChange={(e) => setSettings((s) => ({ ...s, opencode_serve_url: e.target.value }))}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50 font-mono"
              />
            </div>
          </div>
        </motion.section>

        <motion.section
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="bg-surface-light border border-surface-border rounded-xl p-5"
        >
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Cpu className="w-4 h-4" />
            Local LLM
          </h2>
          <div className="flex items-center gap-2 mb-4">
            {ollamaOk === true ? (
              <span className="flex items-center gap-1 text-xs text-green-400">
                <Wifi className="w-3 h-3" />
                Ollama / LM Studio detected
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs text-zinc-500">
                <WifiOff className="w-3 h-3" />
                No local LLM detected
              </span>
            )}
            <button
              onClick={() => {
                setOllamaOk(null);
                api.getOllamaStatus()
                  .then((d) => setOllamaOk(d.data.running))
                  .catch(() => setOllamaOk(false));
              }}
              className="ml-auto text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
              title="Re-check local LLM status"
            >
              <RefreshCw className="w-3 h-3" />
            </button>
          </div>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-zinc-500 mb-1 block">Endpoint</label>
              <input
                type="text"
                value={settings.local_endpoint}
                onChange={(e) => setSettings((s) => ({ ...s, local_endpoint: e.target.value }))}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50 font-mono"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-500 mb-1 block">Default Model</label>
              <input
                type="text"
                value={settings.local_model}
                onChange={(e) => setSettings((s) => ({ ...s, local_model: e.target.value }))}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50"
              />
            </div>
          </div>
          {ollamaOk === false && (
            <p className="text-xs text-zinc-500 mt-3">
              Install <a href="https://ollama.com" className="text-accent hover:underline" target="_blank" rel="noopener noreferrer">Ollama</a> or <a href="https://lmstudio.ai" className="text-accent hover:underline" target="_blank" rel="noopener noreferrer">LM Studio</a> to run local models.
            </p>
          )}
        </motion.section>

        <motion.section
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-surface-light border border-surface-border rounded-xl p-5"
        >
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Cloud className="w-4 h-4" />
            Cloud Provider
          </h2>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-zinc-500 mb-1 block">Provider</label>
              <select
                value={settings.cloud_provider}
                onChange={(e) => setSettings((s) => ({ ...s, cloud_provider: e.target.value }))}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50"
              >
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="google">Google Gemini</option>
                <option value="openrouter">OpenRouter</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-zinc-500 mb-1 block">API Key</label>
              <input
                type="password"
                value={settings.cloud_key}
                onChange={(e) => setSettings((s) => ({ ...s, cloud_key: e.target.value }))}
                placeholder="sk-..."
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50 font-mono"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-500 mb-1 block">Model</label>
              <input
                type="text"
                value={settings.cloud_model}
                onChange={(e) => setSettings((s) => ({ ...s, cloud_model: e.target.value }))}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50"
              />
            </div>
          </div>
        </motion.section>
      </div>
    </div>
  );
}
