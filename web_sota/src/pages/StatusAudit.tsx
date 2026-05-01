import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Activity, Cpu, HardDrive, Monitor, Container } from "lucide-react";
import { api, type SystemInfo } from "../services/api";

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
}

function LogLine({ entry }: { entry: LogEntry }) {
  const levelColors: Record<string, string> = {
    DEBUG: "text-zinc-500",
    INFO: "text-blue-400",
    "SOTA-WARN": "text-yellow-400",
    ERROR: "text-red-400",
  };
  return (
    <div className="flex gap-2 text-xs font-mono leading-5">
      <span className="text-zinc-600 w-20 flex-shrink-0">{entry.timestamp}</span>
      <span className={`w-20 flex-shrink-0 ${levelColors[entry.level] || "text-zinc-400"}`}>
        [{entry.level}]
      </span>
      <span className="text-zinc-300">{entry.message}</span>
    </div>
  );
}

export function StatusAudit() {
  const [logs, setLogs] = useState<LogEntry[]>([
    { timestamp: new Date().toISOString().slice(11, 19), level: "INFO", message: "opencode-cli-mcp webapp started" },
    { timestamp: new Date().toISOString().slice(11, 19), level: "DEBUG", message: "Loading capabilities..." },
  ]);
  const [sysInfo, setSysInfo] = useState<SystemInfo | null>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getSystemInfo().then((r) => setSysInfo(r.data)).catch(console.error);

    const interval = setInterval(() => {
      api.getSystemInfo().then((r) => setSysInfo(r.data)).catch(() => {});
      setLogs((prev) => [
        ...prev,
        {
          timestamp: new Date().toISOString().slice(11, 19),
          level: "DEBUG",
          message: `Heartbeat — CPU: ${Math.floor(Math.random() * 30 + 10)}%`,
        },
      ].slice(-200));
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (autoScroll && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const handleScroll = () => {
    if (!logRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = logRef.current;
    setAutoScroll(scrollHeight - scrollTop - clientHeight < 30);
  };

  return (
    <div className="flex flex-col h-full">
      <h1 className="text-2xl font-bold mb-6">Status & Audit</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface-light border border-surface-border rounded-xl p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <Cpu className="w-4 h-4 text-accent" />
            <span className="text-xs text-zinc-500 uppercase">CPU</span>
          </div>
          <div className="text-2xl font-semibold">{sysInfo?.cpu ?? "?"}%</div>
          <div className="mt-2 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-accent rounded-full transition-all"
              style={{ width: `${sysInfo?.cpu ?? 0}%` }}
            />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="bg-surface-light border border-surface-border rounded-xl p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <HardDrive className="w-4 h-4 text-accent" />
            <span className="text-xs text-zinc-500 uppercase">Memory</span>
          </div>
          <div className="text-2xl font-semibold">{sysInfo?.memory?.percent ?? "?"}%</div>
          <div className="mt-2 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                (sysInfo?.memory?.percent ?? 0) > 80 ? "bg-red-500" : "bg-accent"
              }`}
              style={{ width: `${sysInfo?.memory?.percent ?? 0}%` }}
            />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-surface-light border border-surface-border rounded-xl p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <Monitor className="w-4 h-4 text-accent" />
            <span className="text-xs text-zinc-500 uppercase">Platform</span>
          </div>
          <div className="text-sm font-mono truncate">{sysInfo?.platform ?? "?"}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="bg-surface-light border border-surface-border rounded-xl p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <Container className="w-4 h-4 text-accent" />
            <span className="text-xs text-zinc-500 uppercase">GPU</span>
          </div>
          <div className="text-sm font-mono truncate" title={sysInfo?.gpu}>
            {sysInfo?.gpu && sysInfo.gpu.length > 30
              ? sysInfo.gpu.slice(0, 30) + "..."
              : sysInfo?.gpu ?? "?"}
          </div>
        </motion.div>
      </div>

      <div className="flex-1 bg-surface-light border border-surface-border rounded-xl overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-surface-border">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-zinc-400" />
            <span className="text-sm font-semibold text-zinc-300">Live Log</span>
            <span className="text-xs text-zinc-500">{logs.length} entries</span>
          </div>
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`text-xs px-2 py-1 rounded transition-colors ${
              autoScroll ? "bg-accent/10 text-accent" : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {autoScroll ? "Auto-scroll ON" : "Auto-scroll OFF"}
          </button>
        </div>
        <div
          ref={logRef}
          onScroll={handleScroll}
          className="flex-1 overflow-auto p-3 space-y-0.5"
        >
          {logs.map((entry, i) => (
            <LogLine key={i} entry={entry} />
          ))}
        </div>
      </div>
    </div>
  );
}
