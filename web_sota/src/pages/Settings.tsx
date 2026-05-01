import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Settings2,
  Cpu,
  Cloud,
  Sun,
  Moon,
  Save,
  Check,
  Wifi,
  WifiOff,
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
}

export function Settings() {
  const [settings, setSettings] = useState<SettingsData>({
    theme: "dark",
    llm_provider: "local",
    local_endpoint: "http://127.0.0.1:11434",
    local_model: "llama3.2",
    cloud_provider: "openai",
    cloud_key: "",
    cloud_model: "gpt-4o",
  });
  const [ollamaOk, setOllamaOk] = useState<boolean | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api
      .getSettings()
      .then((s) => setSettings(s as SettingsData))
      .catch(console.error);
    fetch("/api/ollama/status")
      .then((r) => r.json())
      .then((d) => setOllamaOk(d.data.running))
      .catch(() => setOllamaOk(false));
  }, []);

  const handleSave = async () => {
    try {
      await api.updateSettings(settings as unknown as Record<string, unknown>);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Settings</h1>
        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover rounded-lg text-sm transition-colors"
          title="Save settings"
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
              onClick={() =>
                setSettings((s) => ({ ...s, theme: s.theme === "dark" ? "light" : "dark" }))
              }
              className={`relative w-12 h-6 rounded-full transition-colors ${
                settings.theme === "dark" ? "bg-accent" : "bg-zinc-600"
              }`}
              role="switch"
              aria-checked={settings.theme === "dark" ? "true" : "false"}
              aria-label="Toggle dark mode"
            >
              <div
                className={`absolute w-5 h-5 bg-white rounded-full top-0.5 transition-transform ${
                  settings.theme === "dark" ? "translate-x-6" : "translate-x-0.5"
                }`}
              />
            </button>
            <span className="text-sm text-zinc-300">Dark mode</span>
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
            Local LLM (Glom On)
          </h2>
          <div className="flex items-center gap-2 mb-4">
            {ollamaOk === true ? (
              <span className="flex items-center gap-1 text-xs text-green-400">
                <Wifi className="w-3 h-3" />
                Ollama detected on port 11434
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs text-zinc-500">
                <WifiOff className="w-3 h-3" />
                No local LLM detected
              </span>
            )}
          </div>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-zinc-500 mb-1 block">Endpoint</label>
              <input
                type="text"
                value={settings.local_endpoint}
                onChange={(e) => setSettings((s) => ({ ...s, local_endpoint: e.target.value }))}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50"
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
              High-performance GPU detected. Install Ollama or LM Studio to unlock AI features for free.
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
              </select>
            </div>
            <div>
              <label className="text-xs text-zinc-500 mb-1 block">API Key</label>
              <input
                type="password"
                value={settings.cloud_key}
                onChange={(e) => setSettings((s) => ({ ...s, cloud_key: e.target.value }))}
                placeholder="sk-..."
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50"
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
