import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Cpu, Cloud, Save, Check, Wifi, WifiOff, Server, RefreshCw, Loader2 } from "lucide-react";
import { api, type LlmProvider } from "../services/api";
import { useStore } from "../store";

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

// Fleet standard (chat_skills_prefab_standard.md §1.3): provider + model
// selections persist in localStorage and are restored on load.
const LS_PROVIDER = "llm_provider";
const LS_MODEL = "llm_model";
const LS_ENDPOINT = "llm_endpoint";

// Fleet standard (WEBAPP_SOTA_STANDARDS.md §VI): permanently dark. No light toggle.

interface ProviderStatus {
  id: string;
  label: string;
  port: number;
  status: "probing" | "detected" | "not_found";
  models: string[];
}

export function Settings() {
  const [settings, setSettings] = useState<SettingsData>(DEFAULT_SETTINGS);
  const [originalSettings, setOriginalSettings] = useState<SettingsData>(DEFAULT_SETTINGS);
  const [providerStatus, setProviderStatus] = useState<ProviderStatus[]>([]);
  const [detectedModels, setDetectedModels] = useState<string[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [llmProviders, setLlmProviders] = useState<LlmProvider[]>([]);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const setStoreLlmProvider = useStore((s) => s.setLlmProvider);
  const setStoreLlmModel = useStore((s) => s.setLlmModel);

  const hasChanges = JSON.stringify(settings) !== JSON.stringify(originalSettings);

  const probeProviders = useCallback(async () => {
    const targets: Array<{ id: string; label: string; port: number }> = [
      { id: "ollama", label: "Ollama", port: 11434 },
      { id: "lmstudio", label: "LM Studio", port: 1234 },
      { id: "vllm", label: "vLLM", port: 8000 },
    ];
    setProviderStatus(targets.map((t) => ({ ...t, status: "probing", models: [] })));

    // Models per provider: /llm/providers covers Ollama + LM Studio with
    // model lists; probe ports for liveness of all three (incl. vLLM).
    let knownProviders: LlmProvider[] = [];
    try {
      const d = await api.getLlmProviders();
      if (d.success) knownProviders = d.data.providers;
    } catch {
      knownProviders = [];
    }
    const modelsByProvider = (id: string): string[] => knownProviders.find((p) => p.id === id)?.models ?? [];

    let runningProvider: string | null = null;
    try {
      const d = await api.getOllamaStatus();
      if (d.data.running) runningProvider = d.data.provider ?? null;
    } catch {
      runningProvider = null;
    }

    const results = await Promise.all(
      targets.map(async (t): Promise<ProviderStatus> => {
        const models = modelsByProvider(t.id);
        const detected = runningProvider === t.id || models.length > 0;
        return { ...t, status: detected ? "detected" : "not_found", models };
      }),
    );
    setProviderStatus(results);

    // Detection-driven provider select (WEBAPP_SOTA_STANDARDS §VI.2): the
    // dropdown lists detected providers, priority Ollama > LM Studio > vLLM.
    const detected = results.filter((r) => r.status === "detected");
    const detectedProviders: LlmProvider[] = detected.map((d) => ({
      id: d.id,
      label: d.label,
      base_url: `http://127.0.0.1:${d.port}/v1`,
      models: d.models,
      needs_key: false,
    }));
    setLlmProviders(detectedProviders);

    // Restore selection from localStorage if still detected; else first detected.
    const savedProvider = localStorage.getItem(LS_PROVIDER);
    const selected = detected.find((d) => d.id === savedProvider) ?? detected[0];
    const savedModel = localStorage.getItem(LS_MODEL);
    setSettings((s) => ({
      ...s,
      llm_provider: selected?.id ?? "local",
      local_endpoint:
        localStorage.getItem(LS_ENDPOINT) || (selected ? `http://127.0.0.1:${selected.port}/v1` : s.local_endpoint),
      local_model: selected?.models.includes(savedModel ?? "")
        ? (savedModel as string)
        : (selected?.models[0] ?? s.local_model),
    }));
    if (selected) setDetectedModels(selected.models);
    if (selected) {
      setStoreLlmProvider(selected.id);
      const resolvedModel = selected.models.includes(savedModel ?? "") ? (savedModel as string) : selected.models[0];
      if (resolvedModel) setStoreLlmModel(resolvedModel);
    }
  }, [setStoreLlmProvider, setStoreLlmModel]);

  const refreshModels = useCallback(
    async (providerId: string) => {
      setLoadingModels(true);
      try {
        const prov = llmProviders.find((p) => p.id === providerId);
        if (prov && prov.models.length > 0) {
          setDetectedModels(prov.models);
          setSettings((s) => {
            const nextModel = prov.models.includes(s.local_model) ? s.local_model : prov.models[0];
            setStoreLlmModel(nextModel);
            return { ...s, local_model: nextModel };
          });
        } else {
          // Provider has no model list yet — try the models endpoint directly.
          const d = await api.getLocalModels();
          if (d.success && d.data.models.length > 0) {
            setDetectedModels(d.data.models);
            setSettings((s) => {
              const nextModel = d.data.models.includes(s.local_model) ? s.local_model : d.data.models[0];
              setStoreLlmModel(nextModel);
              return { ...s, local_model: nextModel };
            });
          }
        }
      } catch {
        // provider down — keep current model
      } finally {
        setLoadingModels(false);
      }
    },
    [llmProviders, setStoreLlmModel],
  );

  useEffect(() => {
    api
      .getSettings()
      .then((s) => {
        const merged = { ...DEFAULT_SETTINGS, ...s } as SettingsData;
        setSettings(merged);
        setOriginalSettings(merged);
      })
      .catch(() => {});
    probeProviders();
  }, [probeProviders]);

  const handleProviderChange = (id: string) => {
    const prov = llmProviders.find((p) => p.id === id);
    setSettings((s) => ({
      ...s,
      llm_provider: id,
      local_endpoint: prov ? prov.base_url : s.local_endpoint,
    }));
    localStorage.setItem(LS_PROVIDER, id);
    if (prov) localStorage.setItem(LS_ENDPOINT, prov.base_url);
    setStoreLlmProvider(id);
    refreshModels(id);
  };

  const handleModelChange = (model: string) => {
    setSettings((s) => ({ ...s, local_model: model }));
    localStorage.setItem(LS_MODEL, model);
    setStoreLlmModel(model);
  };

  const handleSave = async () => {
    setError("");
    try {
      const res = await api.updateSettings(settings as unknown as Record<string, unknown>);
      if (res.success) {
        setOriginalSettings({ ...settings });
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      } else {
        setError("Save failed");
      }
    } catch (err) {
      setError(`Save failed: ${err instanceof Error ? err.message : "unknown"}`);
    }
  };

  const anyDetected = providerStatus.some((p) => p.status === "detected");

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Settings</h1>
        <button
          type="button"
          onClick={handleSave}
          disabled={!hasChanges}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${
            hasChanges ? "bg-accent hover:bg-accent-hover text-white" : "bg-zinc-800 text-zinc-500 cursor-not-allowed"
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
        <div className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded-lg text-sm text-red-400">{error}</div>
      )}

      <div className="space-y-6">
        <motion.section
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-light border border-surface-border rounded-xl p-5"
        >
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Server className="w-4 h-4" />
            Opencode Serve
          </h2>
          <div className="space-y-3">
            <div>
              <label htmlFor="oc-serve-url" className="text-xs text-zinc-500 mb-1 block">
                Server URL
              </label>
              <input
                id="oc-serve-url"
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

          <div className="mb-4">
            {providerStatus.map((p) => (
              <div key={p.id} className="flex items-center gap-2 py-1 text-xs">
                {p.status === "detected" ? (
                  <Wifi className="w-3 h-3 text-green-400" />
                ) : p.status === "probing" ? (
                  <Loader2 className="w-3 h-3 text-zinc-500 animate-spin" />
                ) : (
                  <WifiOff className="w-3 h-3 text-zinc-600" />
                )}
                <span className={p.status === "detected" ? "text-green-400" : "text-zinc-500"}>
                  {p.label} on :{p.port}
                </span>
                <span className="text-zinc-600">
                  {p.status === "detected"
                    ? `(${p.models.length || "?"} models)`
                    : p.status === "probing"
                      ? "probing..."
                      : "not found"}
                </span>
              </div>
            ))}
            <button
              type="button"
              onClick={probeProviders}
              className="mt-2 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
              title="Re-check local LLM status"
            >
              <RefreshCw className="w-3 h-3" />
            </button>
          </div>

          <div className="space-y-3">
            <div>
              <label htmlFor="llm-provider" className="text-xs text-zinc-500 mb-1 block">
                Provider
              </label>
              <select
                id="llm-provider"
                data-testid="llm-provider-select"
                value={settings.llm_provider}
                onChange={(e) => handleProviderChange(e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50"
              >
                {llmProviders.length > 0 ? (
                  llmProviders.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                    </option>
                  ))
                ) : (
                  <option value="local">No local LLM detected</option>
                )}
              </select>
            </div>
            <div>
              <label htmlFor="llm-endpoint" className="text-xs text-zinc-500 mb-1 block">
                Endpoint
              </label>
              <input
                id="llm-endpoint"
                type="text"
                value={settings.local_endpoint}
                onChange={(e) => setSettings((s) => ({ ...s, local_endpoint: e.target.value }))}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50 font-mono"
              />
            </div>
            <div>
              <label htmlFor="llm-model" className="text-xs text-zinc-500 mb-1 block">
                Model
              </label>
              {detectedModels.length > 0 ? (
                <select
                  id="llm-model"
                  data-testid="llm-model-select"
                  value={settings.local_model}
                  onChange={(e) => handleModelChange(e.target.value)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50"
                >
                  {detectedModels.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  id="llm-model"
                  data-testid="llm-model-select"
                  type="text"
                  value={settings.local_model}
                  onChange={(e) => handleModelChange(e.target.value)}
                  placeholder={loadingModels ? "Loading models..." : "Enter model name or start Ollama/LM Studio"}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50"
                />
              )}
            </div>
          </div>
          {!anyDetected && (
            <p className="text-xs text-zinc-500 mt-3">
              Install{" "}
              <a
                href="https://ollama.com"
                className="text-accent hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                Ollama
              </a>
              ,{" "}
              <a
                href="https://lmstudio.ai"
                className="text-accent hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                LM Studio
              </a>{" "}
              or vLLM to run local models.
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
              <label htmlFor="cloud-provider" className="text-xs text-zinc-500 mb-1 block">
                Provider
              </label>
              <select
                id="cloud-provider"
                value={settings.cloud_provider}
                onChange={(e) => setSettings((s) => ({ ...s, cloud_provider: e.target.value }))}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50"
              >
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="google">Google Gemini</option>
                <option value="openrouter">OpenRouter</option>
                <option value="deepseek">DeepSeek</option>
              </select>
            </div>
            <div>
              <label htmlFor="cloud-key" className="text-xs text-zinc-500 mb-1 block">
                API Key
              </label>
              <input
                id="cloud-key"
                type="password"
                value={settings.cloud_key}
                onChange={(e) => setSettings((s) => ({ ...s, cloud_key: e.target.value }))}
                placeholder="sk-..."
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent/50 font-mono"
              />
            </div>
            <div>
              <label htmlFor="cloud-model" className="text-xs text-zinc-500 mb-1 block">
                Model
              </label>
              <input
                id="cloud-model"
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
