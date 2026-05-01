import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ExternalLink, Monitor, Wifi, WifiOff, RefreshCw } from "lucide-react";
import { api, type FleetApp } from "../services/api";

export function AppsHub() {
  const [apps, setApps] = useState<FleetApp[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.getFleet();
      setApps(res.data.apps);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const alive = apps.filter((a) => a.alive);
  const dead = apps.filter((a) => !a.alive);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Apps Hub</h1>
          <p className="text-sm text-zinc-500 mt-1">Fleet Discovery — other active MCP webapps on this machine</p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
          title="Refresh fleet scan"
          aria-label="Refresh fleet scan"
        >
          <RefreshCw className="w-4 h-4" />
          Scan
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-zinc-800/50 animate-pulse rounded-xl h-24" />
          ))}
        </div>
      ) : (
        <>
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">
            Online ({alive.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {alive.map((app) => (
              <motion.a
                key={app.port}
                href={`http://127.0.0.1:${app.port}`}
                target="_blank"
                rel="noopener noreferrer"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-3 bg-surface-light border border-green-500/20 rounded-xl p-4 hover:border-green-500/40 transition-colors group"
              >
                <div className="p-2 bg-green-500/10 rounded-lg">
                  <Wifi className="w-5 h-5 text-green-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Monitor className="w-3.5 h-3.5 text-zinc-500 flex-shrink-0" />
                    <span className="font-medium truncate">{app.label}</span>
                  </div>
                  <div className="text-xs text-zinc-500 mt-0.5">port {app.port}</div>
                </div>
                <ExternalLink className="w-4 h-4 text-zinc-500 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
              </motion.a>
            ))}
            {alive.length === 0 && (
              <div className="col-span-full text-zinc-500 text-sm">No other fleet apps detected</div>
            )}
          </div>

          <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-3">
            Offline ({dead.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {dead.slice(0, 12).map((app) => (
              <div
                key={app.port}
                className="flex items-center gap-3 bg-zinc-800/30 border border-zinc-800 rounded-xl p-4 opacity-50"
              >
                <div className="p-2 bg-zinc-800 rounded-lg">
                  <WifiOff className="w-5 h-5 text-zinc-600" />
                </div>
                <div>
                  <span className="text-sm text-zinc-500">{app.label}</span>
                  <div className="text-xs text-zinc-600">port {app.port}</div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
