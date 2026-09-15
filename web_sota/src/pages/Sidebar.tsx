import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { PanelLeft, MousePointerClick, Keyboard, Settings2, Wrench, CheckCircle2, AlertCircle } from "lucide-react";
import { API_BASE } from "../lib/api";

const KEYBINDS = [
  ["Ctrl+Alt+O", "Show / hide the sidebar panel"],
  ["AppsKey", "Tab menu (close, reopen, new, switch) while opencode is focused"],
  ["Enter", "Jump to the focused session (sidebar focused)"],
  ["Right-click a row", "Rename, archive, delete, star, rate, comment, copy id"],
  ["Hover a row", "Chat-tail preview tooltip"],
];

const MENU_ROWS = [
  ["Jump to session", "Opens the desktop command palette filtered to that title"],
  ["New session here", "opencode://new-session deep link in the row's directory"],
  ["Rename / Archive", "Via the depot path (backed up, reversible)"],
  ["Delete", "Confirm dialog, depot cascade, backup rotation covers it"],
  ["Star / Rate / Comment", "Local sidecar.ini, shown in the Mark column"],
];

export function Sidebar() {
  const [backend, setBackend] = useState<"probing" | "up" | "down">("probing");

  useEffect(() => {
    let live = true;
    fetch(`${API_BASE}/api/v1/health`, { signal: AbortSignal.timeout(4000) })
      .then((r) => live && setBackend(r.ok ? "up" : "down"))
      .catch(() => live && setBackend("down"));
    return () => {
      live = false;
    };
  }, []);

  return (
    <div className="max-w-2xl mx-auto space-y-6" data-testid="sidebar-page">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <PanelLeft className="w-6 h-6 text-accent" />
          Desktop Sidebar
        </h1>
        <p className="text-sm text-zinc-500 mt-1">
          AHK companion that replaces the desktop top-tab chaos with a docked session list. Code:{" "}
          <code className="text-accent font-mono">sidebar/</code> (outside the .mcpb).
        </p>
      </div>

      <motion.section
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-light border border-surface-border rounded-xl p-5 space-y-3"
        data-testid="sidebar-status"
      >
        <div className="flex items-center gap-2 text-sm">
          {backend === "up" ? (
            <CheckCircle2 className="w-4 h-4 text-green-400" data-testid="sidebar-backend-up" />
          ) : backend === "down" ? (
            <AlertCircle className="w-4 h-4 text-red-400" data-testid="sidebar-backend-down" />
          ) : (
            <span className="text-zinc-500">Probing backend…</span>
          )}
          <span>
            {backend === "up" && "Backend reachable — depot path live."}
            {backend === "down" &&
              "Backend unreachable — start it first (.\\start.ps1). The sidebar needs the depot module."}
            {backend === "probing" && "Checking backend…"}
          </span>
        </div>
      </motion.section>

      <motion.section
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-light border border-surface-border rounded-xl p-5 space-y-3"
        data-testid="sidebar-install"
      >
        <h2 className="font-semibold flex items-center gap-2">
          <MousePointerClick className="w-4 h-4 text-accent" /> Install
        </h2>
        <ol className="text-sm text-zinc-400 space-y-1.5 list-decimal ml-5">
          <li>Install AutoHotkey v2 (fleet: winget/scoop).</li>
          <li>
            Double-click <code className="text-accent font-mono">sidebar/opencode-sidebar.ahk</code> — tray icon
            appears.
          </li>
          <li>Focus the opencode desktop window, press Ctrl+Alt+O.</li>
          <li>
            Autostart (optional): shortcut in <code className="text-accent font-mono">shell:startup</code> targeting the
            AHK exe plus the script.
          </li>
        </ol>
      </motion.section>

      <motion.section
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-light border border-surface-border rounded-xl p-5 space-y-3"
        data-testid="sidebar-keys"
      >
        <h2 className="font-semibold flex items-center gap-2">
          <Keyboard className="w-4 h-4 text-accent" /> Keys &amp; menu
        </h2>
        <div className="text-sm">
          {KEYBINDS.map(([k, v]) => (
            <div key={k} className="flex gap-3 py-1 border-b border-surface-border last:border-0">
              <code className="text-accent font-mono whitespace-nowrap w-40 flex-shrink-0">{k}</code>
              <span className="text-zinc-400">{v}</span>
            </div>
          ))}
        </div>
        <div className="text-sm pt-2">
          {MENU_ROWS.map(([k, v]) => (
            <div key={k} className="flex gap-3 py-1 border-b border-surface-border last:border-0">
              <span className="text-zinc-200 whitespace-nowrap w-40 flex-shrink-0">{k}</span>
              <span className="text-zinc-400">{v}</span>
            </div>
          ))}
        </div>
      </motion.section>

      <motion.section
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-light border border-surface-border rounded-xl p-5 space-y-3"
        data-testid="sidebar-config"
      >
        <h2 className="font-semibold flex items-center gap-2">
          <Settings2 className="w-4 h-4 text-accent" /> Config
        </h2>
        <ul className="text-sm text-zinc-400 space-y-1.5 list-disc ml-5">
          <li>
            Stars/ratings/comments live in <code className="text-accent font-mono">%TEMP%\opencode\sidecar.ini</code> —
            never committed, migrates with you.
          </li>
          <li>Dock edge (left/right) persists in the same file under [ui].</li>
          <li>
            All reads/writes go through <code className="text-accent font-mono">sidebar_client.py</code> → the depot
            module (narrow update path, FK cascades, backup rotation). No raw SQL.
          </li>
          <li>Filter box, star-only toggle, cost sort + totals, 60s auto-refresh while visible.</li>
        </ul>
      </motion.section>

      <motion.section
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-light border border-surface-border rounded-xl p-5 space-y-3"
        data-testid="sidebar-troubleshoot"
      >
        <h2 className="font-semibold flex items-center gap-2">
          <Wrench className="w-4 h-4 text-accent" /> Troubleshooting
        </h2>
        <ul className="text-sm text-zinc-400 space-y-1.5 list-disc ml-5">
          <li>Empty list: backend down or depot unreachable — check the status line above.</li>
          <li>
            Jump lands on the wrong session: duplicate titles — the palette picks the top match; rename one first.
          </li>
          <li>Middle-click still closes tabs: the guard only covers the strip zone while opencode is focused.</li>
          <li>
            Full reference: <code className="text-accent font-mono">docs/SIDEBAR.md</code>.
          </li>
        </ul>
      </motion.section>
    </div>
  );
}
