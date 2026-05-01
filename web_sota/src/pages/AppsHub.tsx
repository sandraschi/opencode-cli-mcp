import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  ExternalLink, Monitor, Wifi, WifiOff, RefreshCw, ShieldCheck,
  FlaskConical, AlertTriangle,
} from "lucide-react";
import { api, type FleetApp } from "../services/api";

export function AppsHub() {
  const [apps, setApps] = useState<FleetApp[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUntrusted, setShowUntrusted] = useState(false);

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

  const registeredAlive = apps.filter((a) => a.alive && a.known);
  const unregisteredAlive = apps.filter((a) => a.alive && !a.known);
  const dead = apps.filter((a) => !a.alive);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Apps Hub</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Fleet Discovery — MCP webapps on this machine
          </p>
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
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheck className="w-4 h-4 text-green-400" />
            <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
              Registered ({registeredAlive.length})
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {registeredAlive.map((app, i) => (
              <motion.a
                key={app.port}
                href={`http://127.0.0.1:${app.port}`}
                target="_blank"
                rel="noopener noreferrer"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
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
            {registeredAlive.length === 0 && (
              <div className="col-span-full text-zinc-500 text-sm">No registered fleet apps detected</div>
            )}
          </div>

          {unregisteredAlive.length > 0 && (
            <>
              <button
                onClick={() => setShowUntrusted(!showUntrusted)}
                className="flex items-center gap-2 mb-3 text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                <FlaskConical className="w-4 h-4" />
                <h2 className="text-sm font-semibold uppercase tracking-wider">
                  Experimental/Untrusted ({unregisteredAlive.length})
                </h2>
              </button>
              {showUntrusted && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
                  {unregisteredAlive.map((app, i) => (
                    <motion.div
                      key={app.port}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03 }}
                      className="flex items-center gap-3 bg-zinc-800/30 border border-yellow-500/20 rounded-xl p-4"
                    >
                      <div className="p-2 bg-yellow-500/10 rounded-lg">
                        <AlertTriangle className="w-5 h-5 text-yellow-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <span className="text-sm text-zinc-400 truncate block">{app.label}</span>
                        <div className="text-xs text-zinc-600">port {app.port} (not in registry)</div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </>
          )}

          <h2 className="text-sm font-semibold text-zinc-600 uppercase tracking-wider mb-3">
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
