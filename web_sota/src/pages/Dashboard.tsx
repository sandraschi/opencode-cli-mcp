import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Server,
  Activity,
  ListTree,
  Cpu,
  AppWindow,
  HardDrive,
  Monitor,
  Terminal,
} from "lucide-react";
import { api, type FleetApp, type SystemInfo } from "../services/api";
import { useStore } from "../store";

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  delay = 0,
}: {
  icon: any;
  label: string;
  value: string | number;
  sub?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="bg-surface-light border border-surface-border rounded-xl p-4 flex items-start gap-3"
    >
      <div className="p-2 bg-accent/10 rounded-lg">
        <Icon className="w-5 h-5 text-accent" />
      </div>
      <div>
        <div className="text-xs text-zinc-500 uppercase tracking-wider">{label}</div>
        <div className="text-xl font-semibold mt-0.5">{value}</div>
        {sub && <div className="text-xs text-zinc-500 mt-0.5">{sub}</div>}
      </div>
    </motion.div>
  );
}

export function Dashboard() {
  const capabilities = useStore((s) => s.capabilities);
  const opencodeStatus = useStore((s) => s.opencodeStatus);
  const setCapabilities = useStore((s) => s.setCapabilities);
  const setOpencodeStatus = useStore((s) => s.setOpencodeStatus);
  const [fleetCount, setFleetCount] = useState(0);
  const [sysInfo, setSysInfo] = useState<SystemInfo | null>(null);

  useEffect(() => {
    api.getCapabilities().then(setCapabilities).catch(console.error);
    api.getOpencodeStatus().then((r) => setOpencodeStatus(r.data)).catch(console.error);
    api.getFleet().then((r) => setFleetCount(r.data.apps.filter((a: FleetApp) => a.alive).length)).catch(() => {});
    api.getSystemInfo().then((r) => setSysInfo(r.data)).catch(() => {});
  }, []);

  const serverOk =
    opencodeStatus?.health?.status === "ok" ||
    opencodeStatus?.health?.status === "running";

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Server}
          label="opencode Server"
          value={serverOk ? "Online" : "Offline"}
          sub={opencodeStatus?.health?.status || "unknown"}
          delay={0}
        />
        <StatCard
          icon={ListTree}
          label="Sessions"
          value={opencodeStatus?.sessions ?? "?"}
          delay={0.04}
        />
        <StatCard
          icon={Terminal}
          label="MCP Tools"
          value={capabilities?.tool_surface?.total ?? 0}
          sub={`${capabilities?.tool_surface?.atomic_count ?? 0} atomic`}
          delay={0.08}
        />
        <StatCard
          icon={AppWindow}
          label="Fleet Apps"
          value={fleetCount}
          sub="alive on this machine"
          delay={0.12}
        />
        <StatCard
          icon={Cpu}
          label="CPU"
          value={`${sysInfo?.cpu ?? "?"}%`}
          delay={0.16}
        />
        <StatCard
          icon={HardDrive}
          label="Memory"
          value={`${sysInfo?.memory?.percent ?? "?"}%`}
          delay={0.2}
        />
        <StatCard
          icon={Monitor}
          label="Platform"
          value={sysInfo?.platform ?? "?"}
          delay={0.24}
        />
        <StatCard
          icon={Activity}
          label="MCP Server"
          value={capabilities?.server?.version ?? "?"}
          sub="opencode-cli-mcp"
          delay={0.28}
        />
      </div>

      <div className="mt-8">
        <h2 className="text-lg font-semibold mb-3">Capabilities</h2>
        <div className="bg-surface-light border border-surface-border rounded-xl p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {capabilities?.features &&
              Object.entries(capabilities.features).map(([key, val]) => (
                <div key={key} className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${val ? "bg-green-500" : "bg-zinc-600"}`}
                  />
                  <span className="text-sm text-zinc-400 capitalize">
                    {key.replace(/_/g, " ")}
                  </span>
                </div>
              ))}
          </div>
        </div>
      </div>

      <div className="mt-8">
        <h2 className="text-lg font-semibold mb-3">Tool Surface</h2>
        <div className="flex flex-wrap gap-2">
          {capabilities?.tool_surface?.atomic_tools?.map((tool: string) => (
            <span
              key={tool}
              className="px-3 py-1 bg-zinc-800 text-zinc-300 rounded-full text-xs font-mono"
            >
              {tool}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
