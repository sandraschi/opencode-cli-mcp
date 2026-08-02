import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE } from "../lib/api";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, User, Bot, Cpu, Cloud, Loader2, Wifi, WifiOff, Download, Eraser } from "lucide-react";
import { api } from "../services/api";
import { useStore } from "../store";

const LS_HISTORY = "opencode-cli-chat-history";
const LS_PERSONALITY = "opencode-cli-chat-personality";
const MAX_HISTORY = 100;

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

interface SettingsData {
  llm_provider?: string;
  local_endpoint?: string;
  local_model?: string;
  cloud_provider?: string;
  cloud_key?: string;
  cloud_model?: string;
}

const PERSONAS = [
  {
    id: "reductionist",
    label: "Reductionist",
    desc: "Industrial, technically exhaustive",
    system:
      "You are a reductionist AI assistant. Be concise, direct, and technically precise. Prefer brevity and accuracy.",
  },
  {
    id: "debugger",
    label: "Debugger",
    desc: "Trace-focused, edge cases",
    system:
      "You are a debugger AI. Focus on finding edge cases, tracing problems, and identifying root causes. Be methodical.",
  },
  {
    id: "explainer",
    label: "Explainer",
    desc: "Architectural patterns & concepts",
    system:
      "You are an explainer AI. Focus on architectural patterns, high-level concepts, and making complex topics accessible.",
  },
  {
    id: "custom",
    label: "Custom",
    desc: "User-defined",
    system: "You are a helpful AI assistant.",
  },
];

const HEADERS: Record<string, string> = {
  ollama: "Ollama",
  lmstudio: "LM Studio",
  vllm: "vLLM",
  openai: "OpenAI",
  anthropic: "Anthropic",
  google: "Google Gemini",
  openrouter: "OpenRouter",
};

const EXAMPLE_PROMPTS = [
  "What is the current project structure?",
  "Find all TODO comments",
  "Explain this codebase architecture",
  "Debug the latest error",
  "Suggest refactoring for this module",
  "Write a test for this function",
  "Check git log for recent changes",
  "Optimize this query",
  "Review the API design",
];

function loadHistory(): Message[] {
  try {
    const s = localStorage.getItem(LS_HISTORY);
    if (s) return JSON.parse(s);
  } catch {
    return [];
  }
  return [];
}

export function Chat() {
  const [messages, setMessages] = useState<Message[]>(() => {
    const saved = loadHistory();
    if (saved.length > 0) return saved;
    return [];
  });
  const [input, setInput] = useState("");
  const [persona, setPersona] = useState(() => localStorage.getItem(LS_PERSONALITY) || PERSONAS[0].id);
  const [provider, setProvider] = useState<"local" | "cloud">("local");
  const [streaming, setStreaming] = useState(false);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const [backendProvider, setBackendProvider] = useState<string | null>(null);
  const [settings, setSettings] = useState<SettingsData>({});
  const [refined, setRefined] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  // Shared selection from the Zustand store (Settings owns detection; this
  // keeps the header label consistent with Settings without re-fetching).
  const storeProvider = useStore((s) => s.llmProvider);
  const storeModel = useStore((s) => s.llmModel);

  useEffect(() => {
    try {
      localStorage.setItem(LS_HISTORY, JSON.stringify(messages.slice(-MAX_HISTORY)));
    } catch {
      /* ignore */
    }
  }, [messages]);

  useEffect(() => {
    localStorage.setItem(LS_PERSONALITY, persona);
  }, [persona]);

  const refreshStatus = useCallback(() => {
    api
      .getOllamaStatus()
      .then((d) => setBackendOk(d.data.running))
      .catch(() => setBackendOk(false));
    api
      .getSettings()
      .then((s) => setSettings(s as SettingsData))
      .catch(() => {});
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const currentPersona = PERSONAS.find((p) => p.id === persona);

  const providerLabel = () => {
    if (backendProvider) return HEADERS[backendProvider] || backendProvider;
    if (backendOk && provider === "local") {
      if (storeProvider) return HEADERS[storeProvider] || storeProvider;
      if (settings.local_endpoint?.includes("1234")) return "LM Studio";
      return "Ollama";
    }
    if (provider === "cloud") return HEADERS[settings.cloud_provider || "openai"];
    return "Local";
  };

  const handleRefine = async () => {
    if (!input.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: `Rewrite this prompt to be more clear and specific. Return ONLY the rewritten prompt, no explanation:\n\n${input}`,
          system:
            "You are a prompt refiner. Rewrite the user's input to be clearer and more specific. Return only the rewritten text.",
        }),
      });
      const data = await res.json();
      setRefined(data.response?.trim() || null);
    } catch {
      setRefined(null);
    }
  };

  const sendMessage = async () => {
    let finalInput = input;
    if (refined) {
      finalInput = refined;
      setRefined(null);
    }
    if (!finalInput.trim()) return;

    const userMsg: Message = { role: "user", content: finalInput, timestamp: Date.now() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStreaming(true);

    const assistantMsg: Message = { role: "assistant", content: "", timestamp: Date.now() };
    setMessages((prev) => [...prev, assistantMsg]);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: finalInput,
          system: currentPersona?.system || "",
          // Settings selection is authoritative: the provider/model picked
          // in Settings (shared Zustand store) drives this request.
          provider,
          model: storeProvider ? storeModel || undefined : undefined,
          endpoint: settings.local_endpoint || undefined,
        }),
      });
      const data = await res.json();
      if (data.provider) setBackendProvider(data.provider);
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content: data.response || data.error || "(no response)",
        };
        return updated;
      });
    } catch {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content: "Error: Could not reach LLM provider. Check Settings.",
        };
        return updated;
      });
    } finally {
      setStreaming(false);
    }
  };

  const handleClear = useCallback(() => {
    setMessages([]);
    try {
      localStorage.removeItem(LS_HISTORY);
    } catch {
      /* ignore */
    }
  }, []);

  const handleExport = useCallback(() => {
    const text = messages.map((m) => `[${m.role.toUpperCase()}] ${m.content}`).join("\n\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `opencode-cli-chat-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }, [messages]);

  return (
    <div data-testid="chat-page" className="flex flex-col h-full max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Chat</h1>
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-mono bg-zinc-800 px-2 py-0.5 rounded">
            skill:opencode-cli
          </span>
          <select
            data-testid="personality-select"
            value={persona}
            onChange={(e) => setPersona(e.target.value)}
            className="bg-zinc-800 text-xs text-zinc-300 border border-zinc-700 rounded px-2 py-1"
          >
            {PERSONAS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
          <div className="flex gap-1">
            <button
              type="button"
              data-testid="chat-export"
              onClick={handleExport}
              disabled={messages.length === 0}
              className="p-1.5 rounded text-zinc-500 hover:text-zinc-300 disabled:opacity-30"
              title="Export"
            >
              <Download className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              data-testid="chat-clear"
              onClick={handleClear}
              disabled={messages.length === 0}
              className="p-1.5 rounded text-zinc-500 hover:text-zinc-300 disabled:opacity-30"
              title="Clear"
            >
              <Eraser className="w-3.5 h-3.5" />
            </button>
          </div>
          {backendOk === true && (
            <span className="flex items-center gap-1 text-xs text-green-400 bg-green-500/10 px-2 py-1 rounded-full">
              <Wifi className="w-3 h-3" />
              {providerLabel()}
              {storeProvider && storeModel && provider === "local" && !backendProvider ? ` · ${storeModel}` : ""}
            </span>
          )}
          {backendOk === false && (
            <span className="flex items-center gap-1 text-xs text-zinc-500 bg-zinc-800 px-2 py-1 rounded-full">
              <WifiOff className="w-3 h-3" />
              No LLM detected
            </span>
          )}
          {backendOk === null && (
            <span className="flex items-center gap-1 text-xs text-zinc-500 bg-zinc-800 px-2 py-1 rounded-full">
              <Loader2 className="w-3 h-3 animate-spin" />
              Checking...
            </span>
          )}
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        {PERSONAS.map((p) => (
          <button
            type="button"
            key={p.id}
            onClick={() => setPersona(p.id)}
            className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${persona === p.id ? "border-accent bg-accent/10 text-accent" : "border-surface-border text-zinc-400 hover:text-zinc-200"}`}
            title={p.desc}
          >
            {p.label}
          </button>
        ))}
        <div className="flex-1" />
        <button
          type="button"
          onClick={() => setProvider(provider === "local" ? "cloud" : "local")}
          className={`flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg border transition-colors ${provider === "local" ? "border-green-500/30 text-green-400" : "border-blue-500/30 text-blue-400"}`}
        >
          {provider === "local" ? (
            <>
              <Cpu className="w-3 h-3" /> Local
            </>
          ) : (
            <>
              <Cloud className="w-3 h-3" /> Cloud
            </>
          )}
        </button>
      </div>

      <div data-testid="example-prompts" className="flex flex-wrap gap-1.5 mb-3">
        {EXAMPLE_PROMPTS.map((p) => (
          <button
            type="button"
            key={p}
            onClick={() => setInput(p)}
            className="flex items-center gap-1 px-2 py-1 rounded-full text-[10px] border border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:border-accent/40 transition-colors bg-zinc-900/50"
          >
            <Sparkles className="w-2.5 h-2.5" />
            {p}
          </button>
        ))}
      </div>

      <div data-testid="chat-messages" className="flex-1 overflow-auto space-y-3 mb-4 px-1">
        {messages.length === 0 && (
          <div className="text-center text-zinc-600 mt-16">
            <Bot className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">Send a message to start chatting</p>
            <p className="text-xs mt-1">Configure your LLM in Settings first</p>
          </div>
        )}
        <AnimatePresence>
          {messages.map((msg) => (
            <motion.div
              key={msg.timestamp}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "assistant" && (
                <div className="p-1.5 bg-accent/10 rounded-lg h-fit mt-1">
                  <Bot className="w-4 h-4 text-accent" />
                </div>
              )}
              <div
                className={`max-w-[70%] rounded-xl px-4 py-2.5 text-sm ${msg.role === "user" ? "bg-accent text-white" : "bg-surface-light border border-surface-border"}`}
              >
                {msg.content || <span className="text-zinc-500 italic">Streaming...</span>}
              </div>
              {msg.role === "user" && (
                <div className="p-1.5 bg-zinc-700 rounded-lg h-fit mt-1">
                  <User className="w-4 h-4 text-zinc-300" />
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>

      <div className="flex-shrink-0">
        <AnimatePresence>
          {refined && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              className="mb-2 p-3 bg-zinc-800/50 border border-zinc-700 rounded-lg"
            >
              <div className="flex items-center gap-1 text-xs text-zinc-400 mb-1">
                <Sparkles className="w-3 h-3" />
                Refined prompt
              </div>
              <p className="text-sm text-zinc-300">{refined}</p>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleRefine}
            disabled={!input.trim()}
            className="p-2.5 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors disabled:opacity-30"
            title="Refine prompt"
            aria-label="Refine prompt"
          >
            <Sparkles className="w-4 h-4 text-zinc-400" />
          </button>
          <div className="flex-1 relative">
            <textarea
              data-testid="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder={backendOk ? "Ask something..." : "No LLM detected. Configure in Settings..."}
              rows={1}
              className="w-full bg-surface-light border border-surface-border rounded-lg px-4 py-2.5 text-sm resize-none focus:outline-none focus:border-accent/50 transition-colors"
              style={{ maxHeight: "120px" }}
            />
          </div>
          <button
            type="button"
            data-testid="chat-send"
            onClick={sendMessage}
            disabled={!input.trim() || streaming}
            className="p-2.5 bg-accent hover:bg-accent-hover rounded-lg transition-colors disabled:opacity-30"
            title="Send message"
            aria-label="Send message"
          >
            {streaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
