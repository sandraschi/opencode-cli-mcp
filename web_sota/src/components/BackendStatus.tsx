import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Loader2 } from "lucide-react";
import { API_BASE } from "../lib/api";

type BackendState = "connecting" | "online" | "offline";

async function checkHealth(): Promise<boolean> {
  try {
    const r = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(4000) });
    return r.ok;
  } catch {
    return false;
  }
}

export function BackendStatus() {
  const [state, setState] = useState<BackendState>("connecting");
  const [restarting, setRestarting] = useState(false);

  const refresh = useCallback(async () => {
    const ok = await checkHealth();
    setState((prev) => (ok ? "online" : prev === "connecting" ? "connecting" : "offline"));
  }, []);

  useEffect(() => {
    refresh();
    const delays = [1000, 2000, 4000, 8000, 16000];
    let idx = 0;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      const ok = await checkHealth();
      if (ok) {
        setState("online");
        idx = 0;
      } else {
        setState((prev) => (prev === "online" || prev === "offline" ? "offline" : "connecting"));
        idx = Math.min(idx + 1, delays.length - 1);
      }
      timer = setTimeout(poll, delays[idx]);
    };
    timer = setTimeout(poll, delays[0]);
    let unlisten: (() => void) | undefined;
    (async () => {
      try {
        const { listen } = await import("@tauri-apps/api/event");
        unlisten = await listen<string>("backend-status", (event) => {
          if (event.payload === "ready") {
            setState("online");
          } else if (typeof event.payload === "string" && event.payload.startsWith("error:")) {
            setState("offline");
          }
        });
      } catch {
        // Not inside Tauri - HTTP polling handles it
      }
    })();
    return () => {
      clearTimeout(timer);
      if (unlisten) unlisten();
    };
  }, [refresh]);

  const restartBackend = useCallback(async () => {
    setRestarting(true);
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      await invoke("start_backend");
    } catch {
      setRestarting(false); // not in Tauri - HTTP poll will update
    }
  }, []);

  const dotClass =
    state === "online" ? "bg-green-500" : state === "offline" ? "bg-red-500" : "bg-amber-400 animate-pulse";

  return (
    <div className="flex items-center gap-2" data-testid="backend-dot">
      <span className={`w-2 h-2 rounded-full ${dotClass}`} title={`Backend ${state}`} />
      <span className="text-xs text-zinc-400 hidden md:inline">
        {state === "online" ? "Connected" : state === "offline" ? "Offline" : "Connecting..."}
      </span>
      {state === "offline" && (
        <button
          type="button"
          onClick={restartBackend}
          disabled={restarting}
          title="Restart backend"
          aria-label="Restart backend"
          className="p-1 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
        >
          {restarting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
        </button>
      )}
    </div>
  );
}
